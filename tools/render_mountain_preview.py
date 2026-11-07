"""Render a symbol-free medieval overview of the configured frozen macro terrain."""
import argparse
import copy
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from app.map_render import load_styles, render_map
from app.terrain_source import load_catalog


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config', default=str(ROOT/'docs/examples/terrain-sources.example.json'))
    ap.add_argument('--out', default=str(ROOT/'artifacts/world-overview-preview'))
    args = ap.parse_args(); start = time.perf_counter()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    product = next(p for p in load_catalog(args.config).products if p.kind == 'tectonic-macro-v2')
    x0,z0,x1,z1 = product.extent_m; cell = product.spacing_m
    crop = product.crop(x0,z0,x1+cell,z1+cell)
    # Upsample solely for display: each output pixel covers 1/8 of a source cell.
    # Edges clamp rather than extrapolate or repeat the finite domain.
    factor = 8
    sy,sx = crop['shape_zx']
    yy,xx = np.meshgrid((np.arange(sy*factor)+.5)/factor-.5,
                        (np.arange(sx*factor)+.5)/factor-.5, indexing='ij')
    display = dict(crop)
    display['elevation_m'] = ndimage.map_coordinates(crop['elevation_m'],[yy,xx],order=1,mode='nearest')
    display['status'] = ndimage.map_coordinates(crop['status'],[yy,xx],order=0,mode='nearest')
    display['spacing_m'] = cell/factor
    display['first_sample_xz_m'] = (x0-cell/2+cell/(2*factor),z0-cell/2+cell/(2*factor))
    display['shape_zx'] = display['status'].shape
    styles = copy.deepcopy(load_styles())
    styles['styles']['medieval']['layers'] = {key:False for key in styles['styles']['medieval']['layers']}
    result = render_map(display,'medieval',width=sx*factor,styles=styles)
    assert not (result.symbols or result.decorations or result.spot_heights or result.soundings)
    terrain = Image.fromarray(result.rgb)
    header=100; footer=65
    page=Image.new('RGB',(terrain.width,terrain.height+header+footer),'#e8dcc2')
    page.paste(terrain,(0,header)); draw=ImageDraw.Draw(page)
    fontpath='C:/Windows/Fonts/simsun.ttc'
    title=ImageFont.truetype(fontpath,30); text=ImageFont.truetype(fontpath,18)
    draw.text((35,18),'世界地形总览',font=title,fill='#35291f')
    draw.text((35,61),'冻结板块数据 · 1600 × 1280 km · 原始格距 10 km · X 东 / Z 南',font=text,fill='#534437')
    # A plain 200 km scale bar, not a sprite or decoration.
    bx,by=45,header+terrain.height+20; length=200000/(cell/factor)
    draw.rectangle((bx,by,bx+length,by+8),outline='#35291f',width=1)
    draw.rectangle((bx,by,bx+length/2,by+8),fill='#35291f')
    draw.text((bx,by+11),'0',font=text,fill='#35291f')
    draw.text((bx+length-55,by+11),'200 km',font=text,fill='#35291f')
    page.save(out/'overview.png')
    meta=dict(source=product.provenance(),source_cell_coverage_extent_m=[x0-cell/2,z0-cell/2,x1+cell/2,z1+cell/2],source_shape_zx=[sy,sx],source_spacing_m=cell,display_spacing_m=cell/factor,display_interpolation='bilinear elevation, nearest-neighbour classification, display only; no new terrain detail',style='medieval',symbols='none',decorations='none',spot_heights='none',width_km=1600,height_km=1280,timing_s=round(time.perf_counter()-start,2),limitations=['actual frozen sample is 1600 × 1280 km, not a 10000 km world','interpolation does not create detail','no inferred rivers, lakes, settlements or roads'])
    (out/'preview-source.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'README.md').write_text('# 西式无符号地形总览\n\n```powershell\n.venv\\Scripts\\python.exe tools/render_mountain_preview.py --config docs/examples/terrain-sources.example.json\n```\n\n读取冻结 tectonic-macro-v2；范围 1600 × 1280 km，原始格距 10 km，并非万公里世界。显示插值不会增加真实细节；不修改源地形。使用 medieval 底图预设，本次屏蔽全部符号、装饰和高程点。坐标为本地米制 X 东 Z 南。\n',encoding='utf-8')
    print(json.dumps(meta,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
