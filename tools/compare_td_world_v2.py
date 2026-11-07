"""Side-by-side of world-relief-pilot-v2 and the TD world-960m product over the same 288 km window (same colour stops/light).

Reads the TD product through app.map_source (identity and file hashes verified); v2 arrays are read for comparison only.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import numpy as np  # noqa: E402
from scipy import ndimage  # noqa: E402
from app.map_source import load_source  # noqa: E402
from build_td_world import comparison  # noqa: E402


def main():
    td_dir = ROOT / "artifacts/td-world/world-960m"
    v2 = ROOT / "artifacts/world-relief-pilot-v2"
    out = td_dir / "atlas/v2-same-window.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    src = load_source("world-map-product", td_dir)
    pm = json.loads((v2 / "manifest.json").read_text(encoding="utf-8"))
    old = np.load(v2 / "elevation_m.npy", mmap_mode="r")
    x0, z0 = pm["zoom"]["first_sample_xz_m"]
    n = 300
    X, Z = np.meshgrid(x0 + np.arange(n) * 960.0, z0 + np.arange(n) * 960.0)
    new = np.asarray(src.sample(X, Z, ("elevation_m",))["elevation_m"], float)
    f = pm["first_sample_xz_m"]
    sp = pm["spacing_m"]
    prev = ndimage.map_coordinates(old, [(Z - f[1]) / sp, (X - f[0]) / sp], order=1, mode="nearest")
    comparison(out, [prev, new], ["v2 noise + erosion (same 288 km window)", "Terragenesis TD latent 960 m (same window)"])
    print(out, "v2", float(prev.min()), float(prev.max()), "td", float(new.min()), float(new.max()))


if __name__ == "__main__":
    main()
