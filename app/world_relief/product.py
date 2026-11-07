"""Frozen product, rendering and provenance for the pilot."""
import copy
import ctypes
import hashlib
import json
import time
from pathlib import Path
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw, ImageFont
from app.map_render import load_styles, render_map
from .source import load_source, sample, subseed, spatial_noise, identity
from .tectonic_uplift import uplift_field
from .drainage import ocean_mask, river_lines
from .erosion import evolve

VERSION = 'world-relief-pilot-1.0'

def peak_memory():
    class Counters(ctypes.Structure):
        _fields_ = [('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    if hasattr(ctypes,'windll'):
        counters = Counters(); counters.cb = ctypes.sizeof(counters)
        get_info = ctypes.windll.psapi.GetProcessMemoryInfo
        get_info.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
        get_info.restype = ctypes.c_int
        if not get_info(ctypes.c_void_p(-1),ctypes.byref(counters),counters.cb):
            raise OSError('GetProcessMemoryInfo failed')
        return counters.PeakWorkingSetSize
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024

def crop(h,ocean,first,spacing):
    return dict(elevation_m=h.astype(np.float32),status=np.where(ocean,3,np.where(h<0,4,5)).astype(np.uint8),spacing_m=spacing,first_sample_xz_m=first,shape_zx=h.shape,complete=True,provenance=dict(kind=VERSION))

def render(h,ocean,first,spacing,width):
    styles = copy.deepcopy(load_styles())
    styles['styles']['medieval']['layers'] = {k:False for k in styles['styles']['medieval']['layers']}
    result = render_map(crop(h,ocean,first,spacing),'medieval',width=width,styles=styles)
    assert not (result.symbols or result.decorations or result.spot_heights or result.soundings)
    margin = result.margin
    map_width, map_height = result.map_size
    image = Image.fromarray(result.rgb).crop((margin,margin,margin+map_width,margin+map_height))
    if image.width != width:
        image = image.resize((width,round(image.height*width/image.width)),Image.Resampling.BICUBIC)
    return image

def page(image,title,subtitle,scale_km,meters_per_pixel):
    result = Image.new('RGB',(image.width,image.height+130),'#e8dcc2'); result.paste(image,(0,82))
    draw = ImageDraw.Draw(result)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
    small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
    draw.text((24,12),title,font=font,fill='#35291f'); draw.text((24,47),subtitle,font=small,fill='#534437')
    y = image.height+99; length=scale_km*1000/meters_per_pixel
    draw.line((25,y,25+length,y),fill='#35291f',width=3)
    draw.text((32+length,y-8),f'{scale_km} km',font=small,fill='#35291f')
    return result

def figures(out,before,h,ocean,first,spacing,flow):
    image = render(h,ocean,first,spacing,1600)
    # Thin river lines are actual extracted data, not sprite symbols.
    draw = ImageDraw.Draw(image)
    lines = river_lines(flow,ocean,first,spacing)
    ratio = image.width/(h.shape[1]*spacing)
    edge = (first[0]-spacing/2,first[1]-spacing/2)
    for line in lines:
        points = [((x-edge[0])*ratio,(z-edge[1])*ratio) for x,z in line['coordinates_xz_m']]
        draw.line(points,fill='#4b747a',width=1)
    page(image,'World relief pilot | 1 km generated surface' if spacing==1000 else 'World relief pilot | coarse rehearsal', 'Frozen tectonic skeleton + declared landscape evolution | 1600 x 1280 km | X east, Z south',200,1/ratio).save(out/'overview.png')
    left = render(before, ocean_mask(before),first,spacing,800); right=render(h,ocean,first,spacing,800)
    paired = Image.new('RGB',(1600,left.height));paired.paste(left,(0,0));paired.paste(right,(800,0))
    page(paired,'Before: interpolated buoyancy skeleton                 After: uplift + incision + diffusion','Same extent, same medieval palette and shading | no terrain sprites',200,h.shape[1]*spacing/800).save(out/'before-after.png')
    # Select a rugged land window, rather than an isolated high-elevation plateau.
    gy,gx=np.gradient(h); relief=ndimage.uniform_filter(np.hypot(gx,gy)*(~ocean),size=max(3,int(100000/spacing)))
    half=int(150000/spacing); relief[:half]=0;relief[-half:]=0;relief[:,:half]=0;relief[:,-half:]=0
    z,x=np.unravel_index(np.argmax(relief),h.shape)
    sl=(slice(z-half,z+half),slice(x-half,x+half)); zoomfirst=(first[0]+(x-half)*spacing,first[1]+(z-half)*spacing)
    zoom=render(h[sl],ocean[sl],zoomfirst,spacing,1000)
    page(zoom,'Mountain detail | 300 x 300 km',f'Generated 1 km bed; window centre X={first[0]+x*spacing:.0f} m, Z={first[1]+z*spacing:.0f} m',50,300000/zoom.width).save(out/'zoom.png')
    return lines,dict(first_sample_xz_m=zoomfirst,shape_zx=list(h[sl].shape))

def build(source,out,spacing=1000,steps=12,variant='v1'):
    start=time.perf_counter(); out=Path(out);out.mkdir(parents=True,exist_ok=True)
    fields,source_manifest=load_source(source)
    config=source_manifest['config']; native=config['cell_size_m']
    if spacing not in (1000,4000):
        raise ValueError('Pilot spacing must be 1000 or 4000 m')
    shape=tuple(int(n*native/spacing) for n in config['shape'])
    first=(config['origin_x_m']+spacing/2,config['origin_z_m']+spacing/2)
    before=sample(fields['elevation_m'],shape,native,spacing)
    cf=sample(fields['continental_fraction'],shape,native,spacing)
    thick=sample(fields['crust_thickness_m'],shape,native,spacing)
    belt,_=uplift_field(fields['plate_id'],fields['velocities_m_per_step'],fields['crust_thickness_m'],fields['continental_fraction'],native)
    uplift=sample(belt,shape,native,spacing)
    # Bilinear zero contour is continuous. Only four-neighbor connected negative
    # elevations attached to the domain rim are ocean; fractional crust modulates
    # generated detail, never overrides the sea-level/elevation contract.
    ocean=ocean_mask(before)
    base=before.copy()
    land=~ocean
    seeds={purpose:subseed(20260903,purpose) for purpose in ('relief-24km','relief-8km','relief-3km')}
    detail=np.zeros(shape)
    for purpose,wavelength,amplitude in (('relief-24km',24000,85),('relief-8km',8000,38),('relief-3km',3000,12)):
        detail += amplitude*spatial_noise(shape,first,spacing,seeds[purpose],wavelength)
    # Ruggedness seeds drainage divides; crust and convergence set its amplitude.
    rugged=np.clip((thick-20000)/35000,.1,1.5)
    initial=base+land*(uplift*2200+detail*rugged*np.clip((cf-.5)*5,0,1))
    rate=uplift*.0005
    morphology_parameters=None
    if variant == 'v2':
        from .morphology import initial_surface
        initial,rate,seeds,morphology_parameters=initial_surface(base,uplift,thick,ocean,first,spacing)
    elif variant != 'v1':
        raise ValueError('Unknown morphology variant')
    print(f'Initial surface {shape}; seed 20260903; {variant}',flush=True)
    def progress(i,h):
        print(f'Erosion {i}/{steps}: {time.perf_counter()-start:.1f}s; max {h.max():.1f}m',flush=True)
    h,flow=evolve(initial,ocean,rate,spacing,steps=steps,k=1.2e-6 if variant=='v2' else 2e-6,diffusivity=1.2 if variant=='v2' else .03,progress=progress,area_mode='mfd' if variant=='v2' else 'd8')
    h=h.astype(np.float32)
    ocean=ocean_mask(h)
    # Final routing is calculated from the exact exported float32 bed.
    from .drainage import route
    flow=route(h.astype(float),ocean,spacing,'mfd' if variant=='v2' else 'd8')
    closed=flow['closed_mask'] | ((h<0)&~ocean)
    zz,xx=np.meshgrid((np.arange(shape[0])+.5)*spacing/native-.5,(np.arange(shape[1])+.5)*spacing/native-.5,indexing='ij')
    source_ocean=ndimage.map_coordinates(fields['ocean_connected'].astype(np.uint8),[zz,xx],order=0,mode='nearest').astype(bool)
    edge_structure=ndimage.generate_binary_structure(2,1)
    source_coast=source_ocean ^ ndimage.binary_erosion(source_ocean,structure=edge_structure,border_value=1)
    final_coast=ocean ^ ndimage.binary_erosion(ocean,structure=edge_structure,border_value=1)
    distances=ndimage.distance_transform_edt(~source_coast,sampling=spacing)[final_coast]/1000
    offshore=ndimage.distance_transform_edt(~ocean,sampling=spacing)/1000
    shore_land=ndimage.binary_dilation(ocean,structure=edge_structure)&~ocean
    assert not np.any(h[shore_land]<0)
    assert np.all(closed[(h<0)&~ocean])
    coast_stats=dict(source_land_area_km2=float((~source_ocean).sum()*spacing**2/1e6),final_land_area_km2=float((~ocean).sum()*spacing**2/1e6),land_area_change_percent=float(((~ocean).sum()/(~source_ocean).sum()-1)*100),coast_distance_to_source_km_quantiles=dict(zip(('p50','p90','p99'),np.percentile(distances,[50,90,99]).tolist())),negative_adjacent_land_fraction=0.,land_elevation_medians_by_coast_distance_km={str(d):float(np.median(h[(~ocean)&(offshore>=d)&(offshore<d+2)])) for d in (1,3,10,30,60) if np.any((~ocean)&(offshore>=d)&(offshore<d+2))})
    arrays=dict(elevation_m=h,ocean_mask=ocean,inland_depression_mask=closed,lake_surface_m=flow['filled_m'].astype(np.float32),receiver=flow['receiver'].reshape(shape),drainage_area_m2=flow['area_m2'].astype(np.float32),initial_elevation_m=initial.astype(np.float32),uplift_m_per_year=rate.astype(np.float32))
    for name,a in arrays.items():
        np.save(out/(name+'.npy'),a,allow_pickle=False)
    lines,zoom=figures(out,before,h,ocean,first,spacing,flow)
    (out/'rivers.json').write_text(json.dumps(dict(schema='coordinate-river-segments-v1',threshold_km2=300,lines=lines),separators=(',',':')),encoding='utf-8')
    manifest=dict(schema=VERSION,source_identity=source_manifest['identity'],source_world_seed=config['world_seed'],world_seed=20260903,source_arrays={k:source_manifest['arrays']['final/'+k] for k in fields},shape_zx=shape,first_sample_xz_m=first,spacing_m=spacing,axes='arrays [z,x]; X east; Z south; metres; cell centres; sea=0',boundary='finite, open domain rim and fixed ocean outlets; no wrap',subseed_method='first 8 bytes, big endian unsigned, SHA-256(UTF-8 f"{world_seed}:{purpose}")',subseeds=seeds,parameters=dict(steps=steps,dt_years=100000,K=2e-6,m=.5,n=1,diffusivity_m2_per_year=.03,convergence_width_m=24000,initial_belt_amplitude_m=2200,uplift_scale_m_per_year=.0005,river_threshold_km2=300,coast_fraction=.5),declared_generated=['continuous fractional-crust coastline','convergent mountain belts','coordinate lattice detail at 24, 8 and 3 km','implicit stream power bed and hillslope diffusion','priority-flood water surface and D8 rivers'],limitations=['Not a Terragenesis certified product; not physically calibrated','No sediment transport/deposition; piedmont surfaces are inherited and smoothed, not mass-balanced alluvial fans','D8 grid anisotropy; fixed coastline; depressions marked and overflow routed, no lake water balance','Geological years and rates are scenario parameters, not derived from source steps'],zoom=zoom,river_segments=len(lines),elapsed_seconds=time.perf_counter()-start,peak_working_set_bytes=peak_memory())
    if variant=='v2':
        manifest['schema']='world-relief-pilot-2.0'
        manifest['accumulation']='MFD slope^1.1 with flood-parent flat fallback; single D8 receiver for implicit incision and river lines'
        manifest['morphology_parameters']=morphology_parameters
        manifest['parameters'].update(K=1.2e-6,diffusivity_m2_per_year=1.2,initial_belt_amplitude_m=1900,uplift_scale_m_per_year=.0004)
        manifest['declared_generated'].extend(['14km Gaussian-smoothed and domain-warped skeleton','16km Gaussian-smoothed and domain-warped convergence uplift','64/32/16/8/4/2km fractal relief with separate mountain and plain amplitudes'])
    manifest['coast_validation']=coast_stats
    manifest['coast_rule']='bilinear elevation zero contour; four-neighbor negative cells connected to domain rim are ocean; disconnected negatives are closed below sea'
    manifest['parameters'].pop('coast_fraction',None)
    manifest['declared_generated'][0]='continuous bilinear zero-elevation coastline'
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file() and p.suffix in ('.npy','.png','.json') and p.name!='manifest.json'}
    manifest['files']=files;manifest['identity']=identity(manifest)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    (out/'README.md').write_text(f'''# 世界地貌试点\n\n不是 Terragenesis 认证产品，不是物理标定。源板块种子 20261020，生成种子 20260903。\n\n源身份 `{source_manifest['identity']}`。仅用 numpy 读取冻结 npz，逐数组校验。范围 1600 × 1280 km，数组 [z,x]，X 东 Z 南，格距 {spacing} m，首格心 {first}。有限域开放边界，不周期。\n\n## 方法与参数\n\n相邻板块速度沿边界法向的相向分量定义汇聚，张裂、平移不产生山带；汇聚线以 24 km 高斯半宽扩展，厚地壳调幅。原始浮力代理保留高原，加 2200 m 标度山带。连续插值高程的零等值线确定海岸，四邻连通至有限域边界的负高程格点归海；不连海的负高程保留为内陆洼地。continental_fraction 仅控制细节幅度，不能覆盖高程海陆规则。海岸面积与距离偏差见 manifest.coast_validation。\n\n空间噪声按绝对米坐标的 24/8/3 km 格点哈希采样，幅度 85/38/12 m，仅用于分水岭微扰。种子用途与实际子种子见 manifest。新细节均为声明生成。\n\n{steps} 步 × 100000 情景年；stream power m=0.5,n=1,K=2e-6，按下游优先拓扑用稀疏三角矩阵隐式求解。坡面扩散 D=0.03 m²/年。priority flood 保留原始床面，填洼水面另存，所有低于溢流面的洼地标记。D8 汇水面积 300 km² 出河线，ID 来自绝对坐标 SHA-256，提供上下游连接。\n\n## 产物与复现\n\n`.venv/Scripts/python.exe tools/build_world_relief_pilot.py`\n\n高程与初始地表 float32；ocean_mask、inland_depression_mask 为 bool；receiver 为扁平格点索引；lake_surface_m 为排水填洼面。rivers.json 存米制折线与连接。overview.png 用 medieval render_map，全部 layers=False，零符号和装饰，仅标题、来源、比例尺与数据河线。before-after 对比原始插值与加工地表；zoom 展示约 300 km 山区。manifest 记录数组、PNG、JSON 的文件哈希，自身身份为排除 identity 后规范 JSON 的 SHA-256。\n\n## 局限\n\n尚无沉积物搬运、质量守恒冲积扇或平原增长；山前低缓面来自原有地表和扩散，不能称为已验证冲积沉积。D8 有网格方向偏好；海岸固定；湖泊无水量平衡；速度单位与情景年未物理对应。10 km 骨架采样仍限制山带位置可信度，1 km 细节属于试验生成。\n''',encoding='utf-8')
    if variant=='v2':
        readme=out/'README.md'
        text=readme.read_text(encoding='utf-8')
        text=text.replace('空间噪声按绝对米坐标的 24/8/3 km 格点哈希采样，','空间噪声按绝对米坐标格点哈希采样，')
        text=text.replace('幅度 85/38/12 m，仅用于分水岭微扰','v2采用64/32/16/8/4/2 km六尺度分形起伏，山地幅度700/550/450/320/200/100 m、平原120/85/55/32/18/9 m；不是源数据')
        text=text.replace('K=2e-6','K=1.2e-6').replace('D=0.03','D=1.2').replace('加 2200 m 标度山带','加 1900 m 标度平滑弯曲山带')
        text=text.replace('tools/build_world_relief_pilot.py`','tools/build_world_relief_pilot.py --variant v2 --steps 16`')
        text+='\n## V2形态修正\n\n骨架地表Gaussian sigma=14 km，抬升sigma=16 km，抑制10 km格痕。96/32 km坐标噪声驱动22/6.5 km domain warp，让山带和分水岭弯曲，边界有限clamp、不wrap。所有新增细节均为声明生成；海岸16 km带平滑渐隐，不以噪声改变来源岸线。宽阔高原降低山地噪声，低幅丘陵在平原保留轻微起伏。D8已有对角sqrt(2)长度；未采用D-infinity；汇水面积改为MFD（坡度^1.1归一分配，平坦格走flood-parent），下切和河线保留单一receiver与无环保证。MFD面积沿单一receiver不保证单调，超过门槛的河线向下游延伸闭合；不能把面积直接当实测流量。\n'
        readme.write_text(text,encoding='utf-8')
    print(json.dumps(dict(elapsed_seconds=manifest['elapsed_seconds'],peak_working_set_bytes=manifest['peak_working_set_bytes'],identity=manifest['identity'],river_segments=len(lines))),flush=True)
