"""Static offline demo: world overview (960 m skeleton layer) -> click a point -> 30 m tile status ("not prepared" unless a
prepared tile exists under the world root). Reads only; nothing is generated.

  python tools/build_local30_demo.py [--plan artifacts/worlds/example-existing-skeleton/plan.json]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.world_gen import local30, tiles as T  # noqa: E402

HTML = """<!doctype html><meta charset=utf-8><title>local30 demo</title>
<style>body{font:14px sans-serif;margin:12px}#w{position:relative;display:inline-block}img{display:block;image-rendering:pixelated}
.t{position:absolute;border:1px solid #d22;box-sizing:border-box}#i{margin-top:8px;max-width:900px}</style>
<h3>世界层总览 (底图: __SRC__)</h3>
<div id=w><img id=m src=world.png></div><div id=i>点击地图查看该点所属 30 m 区块的状态。红框 = 配置里登记要安排的区块。</div>
<script>
const D=__DATA__;const w=document.getElementById('w'),i=document.getElementById('i');
D.tiles.forEach(t=>{const e=document.createElement('div');e.className='t';
e.style.left=(t.x0-D.x0)/D.mpp+'px';e.style.top=(t.z0-D.z0)/D.mpp+'px';e.style.width=t.side/D.mpp+'px';e.style.height=t.side/D.mpp+'px';w.appendChild(e)});
document.getElementById('m').onclick=ev=>{const r=ev.target.getBoundingClientRect();
const X=D.x0+(ev.clientX-r.left)*D.mpp,Z=D.z0+(ev.clientY-r.top)*D.mpp;
const ix=Math.floor(X/15360),iz=Math.floor(Z/15360),id=(n)=>(n<0?'-':'+')+String(Math.abs(n)).padStart(3,'0');
const tid='x'+id(ix).replace('+','+0')+'z'+id(iz).replace('+','+0');const t=D.tiles.find(t=>t.ix==ix&&t.iz==iz);
i.textContent='X='+X.toFixed(0)+' m, Z='+Z.toFixed(0)+' m; 区块 ('+ix+','+iz+') '+(t?(t.prepared?'已准备 30 m':'未准备（计划内，需显式运行 tools/prepare_local30.py，GPU）'):'未准备（未登记，不会安排）')+
' ；世界层高程约 '+D.h[Math.floor(ev.offsetY)]?.[Math.floor(ev.offsetX)]+' m'};
</script>"""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', default=str(ROOT / 'artifacts/worlds/example-existing-skeleton/plan.json'))
    ap.add_argument('--out', default=str(ROOT / 'artifacts/local30-demo'))
    ap.add_argument('--step', type=int, default=3)
    a = ap.parse_args(argv)
    from PIL import Image
    plan = json.loads(Path(a.plan).read_text(encoding='utf-8'))
    td = ROOT / 'artifacts/td-world'
    wp = json.loads((td / 'world-plan.json').read_text(encoding='utf-8'))
    arr = np.load(td / 'world-skeleton-960m.npy')[::a.step, ::a.step].astype(np.float64)
    fx, fz = wp['first_sample_xz_m']
    mpp = 960.0 * a.step
    img = np.zeros(arr.shape + (3,), np.uint8)
    sea = arr <= 0
    img[sea] = (40, 90, 160)
    land = np.clip(arr / 3000, 0, 1)
    for c, (lo, hi) in enumerate(((90, 245), (150, 235), (80, 235))):
        img[..., c][~sea] = (lo + (hi - lo) * land[~sea]).astype(np.uint8)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img).save(out / 'world.png')
    tiles = [dict(ix=t['ix'], iz=t['iz'], x0=t['first_sample_xz_m'][0], z0=t['first_sample_xz_m'][1], side=T.NATIVE_M * T.TILE_NATIVE,
                  prepared=t['prepared']) for t in plan['local']['tiles']]
    data = dict(x0=fx, z0=fz, mpp=mpp, tiles=tiles, h=np.round(arr).astype(int).tolist())
    html = HTML.replace('__DATA__', json.dumps(data)).replace('__SRC__', 'artifacts/td-world/world-skeleton-960m.npy（骨架 960 m 层，非成品 TD 镶嵌）')
    (out / 'index.html').write_text(html, encoding='utf-8')
    print(json.dumps(dict(out=str(out / 'index.html'), tiles=len(tiles), image=list(img.shape[:2])), ensure_ascii=False))


if __name__ == '__main__':
    main()
