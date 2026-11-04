"""Explicit, isolated worlds for tests that exercise a running journey.

The small journey contract lives in _legacy_world; no production default is
installed, and callers must explicitly opt in after constructing their Service.
"""
import copy
from pathlib import Path

from app.service import Service
from tests._legacy_world import CHARACTERS, STORY


def adopt_world(runtime, story=None, characters=None):
    """Commit a fresh test package to the temporary store and activate it."""
    repository = Path(__file__).resolve().parents[1]
    if runtime.library.resolve() == (repository / 'StoryPackage').resolve():
        raise ValueError('Test worlds require a temporary package library')
    story = copy.deepcopy(STORY if story is None else story)
    story.setdefault('atlas', {'version': 1, 'features': []})
    characters = copy.deepcopy(CHARACTERS if characters is None else characters)
    return runtime.commit_package(story, characters, 'Explicit test world')


def world_service(store, root):
    """Construct a test Service and explicitly adopt its initial world if empty."""
    repository = Path(__file__).resolve().parents[1]
    isolated_root = Path(store.path).resolve().parent if Path(root).resolve() == repository else Path(root)
    service = Service(store, isolated_root)
    if not service.runtime.has_world():
        adopt_world(service.runtime)
    return service


def world_app(path, package=None):
    """Create an API test app and explicitly adopt the selected test package."""
    from app.web import create_app
    app = create_app(path)
    runtime = app.state.service.runtime
    if not runtime.has_world():
        adopt_world(runtime, package['story'] if package else None,
                    package['characters'] if package else None)
    return app
