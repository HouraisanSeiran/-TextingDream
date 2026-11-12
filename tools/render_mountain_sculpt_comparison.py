"""Render a prototype elevation pair with identical metre colour stops and lighting. No legacy water vectors."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
import numpy as np
from scipy import ndimage as nd
from PIL import Image,ImageDraw,ImageFont
from app.map_render import hillshade

DISPLAY_Z_FACTOR = 2.5

def font(n):
    return ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)

def relief(h,spacing):
    # Fixed geographic terrain tints, shared exactly by old and new.
    heights=np.array([-5000,0,200,700,1400,2200,3200,4500,6000.])
    colors=np.array([[83,131,151],[152,181,168],[157,177,139],[177,183,145],[190,181,151],
                     [178,158,131],[160,142,125],[201,195,181],[239,237,226]],float)
    rgb=np.stack([np.interp(h,heights,colors[:,k]) for k in range(3)],axis=-1)
    shade,lz=hillshade(h,spacing,315.,35.,DISPLAY_Z_FACTOR)
    factor=np.clip(1+.72*(shade/lz-1),.50,1.12)
    return np.clip(rgb*factor[...,None],0,255).round().astype('uint8')

def panel(im,title,note,width=760):
    h=round(im.height*width/im.width)
    out=Image.new('RGB',(width,h+78),(238,235,222))
    d=ImageDraw.Draw(out); d.text((14,8),title,font=font(22),fill='#353a33')
    d.text((14,44),note,font=font(15),fill='#52564c')
    out.paste(im.resize((width,h),Image.Resampling.NEAREST),(0,78))
    return out

ap=argparse.ArgumentParser()
ap.add_argument('--arrays',required=True)
ap.add_argument('--before',required=True); ap.add_argument('--after',required=True)
ap.add_argument('--spacing',type=float,default=10000.)
ap.add_argument('--out',required=True)
ap.add_argument('--reference-arrays',help='Optional previous candidate arrays.npz; compare its after_m against the new one')
ap.add_argument('--reference-label',default='上一版认可候选')
ap.add_argument('--z-factor',type=float,default=2.5,help='Lighting exaggeration only; use 1 for unexaggerated slope shading')
ap.add_argument('--suffix',default='',help='Output filename suffix, e.g. -z1')
a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
DISPLAY_Z_FACTOR = a.z_factor
with np.load(a.arrays,allow_pickle=False) as z:
    old=np.asarray(z[a.before],float); new=np.asarray(z[a.after],float)
if a.reference_arrays:
    with np.load(a.reference_arrays,allow_pickle=False) as ref:
        assert np.array_equal(old,ref['before_m']), 'candidates do not share the same original surface'
        old=np.asarray(ref['after_m'],float)
assert old.shape==new.shape and np.isfinite(new).all()
ims=[Image.fromarray(relief(h,a.spacing)) for h in [old,new]]
notes=f'同{a.spacing/1000:g} km网格 / 同色标 / 同315°光；显示z×{a.z_factor:g}，不绘旧河流'
titles=[a.reference_label if a.reference_arrays else '原始宽底座','山链层次与山麓：本次候选' if a.reference_arrays else '主链—支脉—谷盆：局部候选']
ps=[panel(im,title,notes) for im,title in zip(ims,titles)]
canvas=Image.new('RGB',(ps[0].width*2+16,ps[0].height+115),(238,235,222))
canvas.paste(ps[0],(0,0)); canvas.paste(ps[1],(ps[0].width+16,0))
d=ImageDraw.Draw(canvas); y=ps[0].height+12
stops=[(0,(152,181,168)),(700,(177,183,145)),(1400,(190,181,151)),(2200,(178,158,131)),(3200,(160,142,125)),(4500,(201,195,181)),(6000,(239,237,226))]
for i,(h,c) in enumerate(stops):
    x=18+i*150; d.rectangle((x,y,x+28,y+18),fill=c); d.text((x+34,y-1),f'{h} m',font=font(15),fill='#353a33')
d.text((18,y+36),'局部生成原型：新高程不等于已接入全域水系；海岸/边界保护以验证记录为准。',font=font(17),fill='#353a33')
d.text((18,y+66),'放大仅便于观察，没有增加高程采样；分层色仅用于公平比较山形，不是新群系。',font=font(16),fill='#53584c')
canvas.save(out/('terrain-comparison'+a.suffix+'.png'))
# Separate signed change map: blue lowered valleys, red raised ridges.
delta=new-old; cap=max(500.,float(np.percentile(np.abs(delta),99)))
t=np.clip(delta/cap,-1,1)
c=np.ones(old.shape+(3,))*245
c[t>0]=np.array([245,245,245])+(np.array([168,84,55])-245)*t[t>0,None]
c[t<0]=np.array([245,245,245])+(np.array([64,116,166])-245)*(-t[t<0,None])
change=panel(Image.fromarray(c.clip(0,255).astype('uint8')),'高程实际变化（不是配色变化）',f'蓝色降低 / 红色抬升 / 白色不变；饱和范围 ±{cap:.0f} m')
change.save(out/('height-change'+a.suffix+'.png'))
print(json.dumps(dict(shape_zx=list(old.shape),spacing_m=a.spacing,before_minmax=[float(old.min()),float(old.max())],
 after_minmax=[float(new.min()),float(new.max())],changed_cells=int((old!=new).sum()),
 change_minmax=[float(delta.min()),float(delta.max())],comparison=str(out/('terrain-comparison'+a.suffix+'.png'))),ensure_ascii=False,indent=2))
