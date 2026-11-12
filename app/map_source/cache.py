"""Bounded result cache for frozen local map products.

``resolve_product`` used to run a full ``registry.load_source`` on every map request: every layer
file re-hashed (SHA-256), environment layers compared element-wise against their bound process, and
the manifest identity recomputed.  The arrays themselves are read through ``mmap`` and never copied,
so what got paid again and again was validation.  This module keeps one *successful* load per
(canonical model path, kind, expected identity).  A first load validates exactly as before; a later
request reuses that validation and only re-walks the product directory to decide whether the result
is still current, so on a hit nothing is hashed and no array is compared.

Deliberate limits:

* local, link-free directories only -- a single-file product (``.npz``) and any product tree that
  contains a symbolic link or a junction bypass the cache entirely (the loader still runs, it is
  just not remembered).  ``os.stat`` cannot see through a link, so a product reached partly through
  one has no snapshot that covers what the loader actually read;
* a hit is trusted on path set / ``mtime_ns`` / ``ctime_ns`` / ``size`` / ``inode``.  That catches
  edits, deletions, additions and manifest rewrites done through the filesystem, but it is **not** a
  defence against forged timestamps: whoever can set those can rewrite the manifest identity too;
* a snapshot that changes while a product is loading is never cached, and a failed load caches
  nothing (the error propagates untouched);
* no policy lives here: callers keep their own path, spacing and identity checks.

A held source keeps its layer files ``mmap``-open, so on Windows those files stay locked until the
entry is dropped.  That is harmless for a frozen product (it is only ever republished as a new
directory) but it is why ``clear()`` exists: anything that rewrites a product in place must clear
first.  Hashing and array comparison are what get skipped; ``mmap`` reads are unchanged either way.
"""
from __future__ import annotations

import os
import threading
from collections import OrderedDict
from pathlib import Path

DEFAULT_CAPACITY = 8


class UncacheableProduct(RuntimeError):
    """The product tree cannot be snapshotted faithfully, so its loads are never remembered."""


def _signature(stat):
    """Everything ``os.stat`` reports that moves when a file is rewritten, swapped or replaced."""
    return (stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size, stat.st_ino)


def _is_link(entry):
    """True for a symbolic link, or a Windows junction/reparse point (3.12+ exposes junctions)."""
    if entry.is_symlink():
        return True
    is_junction = getattr(entry, 'is_junction', None)
    return bool(is_junction()) if callable(is_junction) else False


def is_link_path(path):
    """True when ``path`` itself is a link, before anything is walked below it."""
    try:
        if os.path.islink(path):
            return True
        is_junction = getattr(os.path, 'isjunction', None)
        return bool(is_junction(path)) if callable(is_junction) else False
    except OSError:
        return False


def directory_snapshot(root):
    """``(files, directories)`` below ``root``: normalised relative names plus stat signatures.

    Directories carry no signature of their own, only their existence, so an added or removed (even
    empty) folder only counts through the file set it brings or takes away; a new *empty* folder is
    still recorded, so it does invalidate.

    Raises :class:`UncacheableProduct` as soon as a symbolic link or junction is seen anywhere below
    ``root``: ``lstat`` describes the link itself, while the loader reads through it, so no snapshot
    taken this way covers everything the load depended on.
    """
    root = Path(root)
    files, directories = {}, set()
    stack = [str(root)]
    while stack:
        current = stack.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                relative = os.path.normcase(os.path.relpath(entry.path, str(root)))
                if _is_link(entry):
                    raise UncacheableProduct('product contains a link: %s' % relative)
                if entry.is_dir(follow_symlinks=False):
                    directories.add(relative)
                    stack.append(entry.path)
                else:
                    files[relative] = _signature(entry.stat(follow_symlinks=False))
    return frozenset(files.items()), frozenset(directories)


class ProductCache:
    """LRU of successful loads, keyed by ``(canonical path, kind, expected identity)``.

    Thread safety: entries and counters are guarded by one lock; ``loader`` always runs outside it,
    so two threads racing on the same key may both load once and the later result wins.

    What is shared is the loaded source itself, not a copy: ``GridSource`` only promises read-only
    *arrays* -- ``sample``/``crop``/``vectors`` return fresh objects, but ``info`` is the same frozen
    dataclass every caller sees.  Treat a returned source as read-only state, not as your own.
    """

    def __init__(self, capacity=DEFAULT_CAPACITY):
        if type(capacity) is not int or capacity < 1:
            raise ValueError('ProductCache capacity must be a positive integer')
        self._capacity = capacity
        self._entries = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.unstable = 0
        self.uncacheable = 0

    @property
    def capacity(self):
        return self._capacity

    def __len__(self):
        with self._lock:
            return len(self._entries)

    def clear(self):
        """Drop every entry (tests, and anything that rewrites a product in place)."""
        with self._lock:
            self._entries.clear()

    def load(self, path, *, kind, expected_identity, loader):
        """Return the product at ``path``, reusing a cached load while its snapshot is unchanged."""
        root = Path(path)
        if not root.is_dir() or is_link_path(root):
            # Not a directory, or a link we cannot snapshot from here: load, never remember.
            return loader(kind, root, expected_identity=expected_identity)
        key = (os.path.normcase(str(root.resolve())), kind, expected_identity)
        before = self._snapshot(root)
        if before is None:
            # Some part of the tree is unreachable or linked: no faithful snapshot, no cache.
            self.uncacheable += 1
            self._discard(key)
            return loader(kind, root, expected_identity=expected_identity)
        cached = self._lookup(key, before)
        if cached is not None:
            return cached
        source = loader(kind, root, expected_identity=expected_identity)
        after = self._snapshot(root)
        if after is not None and after == before:
            self._store(key, after, source)
            return source
        # The directory moved under us: this result is real, but it is not provably current.
        self.unstable += 1
        self._discard(key)
        return source

    @staticmethod
    def _snapshot(root):
        """``None`` when the tree cannot be walked (OSError) or contains a link."""
        try:
            return directory_snapshot(root)
        except (OSError, UncacheableProduct):
            # Uncacheable is not an error: the loader still decides what the product is.
            return None

    def _lookup(self, key, snapshot):
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self.misses += 1
                return None
            if entry[0] == snapshot:
                self._entries.move_to_end(key)
                self.hits += 1
                return entry[1]
            # The product moved on disk: the entry is stale, not merely unused.
            del self._entries[key]
            self.misses += 1
            return None

    def _store(self, key, snapshot, source):
        with self._lock:
            self._entries[key] = (snapshot, source)
            self._entries.move_to_end(key)
            while len(self._entries) > self._capacity:
                self._entries.popitem(last=False)

    def _discard(self, key):
        with self._lock:
            self._entries.pop(key, None)
