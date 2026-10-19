"""Render discrete elevation bands from GMT Earth Relief; never edit story data."""
import hashlib
import json
import os
from pathlib import Path
import httpx
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
MAPS=ROOT/'assets/maps'
URL='https://oceania.generic-mapping-tools.org/server/earth/earth_relief/earth_relief_10m_g.grd'
LAND=[(-500,'#77ad78'),(0,'#79b76c'),(200,'#b3ce7c'),(500,'#e1db91'),(1000,'#dfbb78'),(2000,'#c99260'),(3000,'#ab7558'),(4000,'#8f695b'),(5000,'#d1c3b6'),(6000,'#f3eee5')]
SEA=[(-12000,'#315d98'),(-6000,'#427aae'),(-4000,'#5997c2'),(-2000,'#7eb8d6'),(-200,'#aad9e5')]

def main():
    source=MAPS/'earth_relief_10m_g.grd'
    if not source.exists():
        response=httpx.get(URL,timeout=90,follow_redirects=True);response.raise_for_status()
        temp=source.with_suffix('.download');temp.write_bytes(response.content);temp.replace(source)
    w,h=2160,1080
    # netCDF-C on Windows cannot open this Unicode absolute path; relative
    # ASCII filename uses the same file and retains latitude/scale metadata.
    os.chdir(MAPS)
    with rasterio.open(source.name,driver='netCDF') as ds:
        heights=np.full((h,w),np.nan,dtype='float32')
        # Explicit netCDF driver exposes north-to-south rows; pass array to avoid
        # GDAL reopening .grd through HDF5 and losing its coordinate metadata.
        raw=ds.read(1).astype('float32')*ds.scales[0]+ds.offsets[0]
        assert ds.tags().get('lat#actual_range')=='{-90,90}' and ds.tags().get('lon#actual_range')=='{-180,180}'
        dx=360/(ds.width-1);dy=180/(ds.height-1)
        transform=from_bounds(-180-dx/2,-90-dy/2,180+dx/2,90+dy/2,ds.width,ds.height)
        reproject(raw,heights,src_transform=transform,src_crs='EPSG:4326',
            dst_transform=from_bounds(-180,-90,180,90,w,h),dst_crs='EPSG:4326',resampling=Resampling.nearest)
    assert np.isfinite(heights).all() and heights.max()>5000 and heights.min()<-6000
    def sample(lon,lat):return heights[min(h-1,int((90-lat)/180*h)),min(w-1,int((lon+180)/360*w))]
    assert sample(85,32)>3500 and sample(-30,0)<-1000, 'Grid orientation/scale incorrect'
    mask=Image.new('1',(w,h));draw=ImageDraw.Draw(mask)
    data=json.loads((MAPS/'ne_50m_land.geojson').read_text(encoding='utf-8'))
    for f in data['features']:
        g=f['geometry'];polys=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
        for poly in polys:
            for i,ring in enumerate(poly):draw.polygon([((x+180)/360*w,(90-y)/180*h) for x,y,*_ in ring],fill=1 if i==0 else 0)
    land=np.asarray(mask,dtype=bool)
    rgb=np.zeros((h,w,3),dtype=np.uint8)
    rgb[land]=tuple(bytes.fromhex(LAND[0][1][1:]))
    rgb[~land]=tuple(bytes.fromhex(SEA[0][1][1:]))
    for selector,bands in [(~land,SEA),(land,LAND)]:
        for lower,color in bands:
            rgb[selector & (heights>=lower)]=tuple(bytes.fromhex(color[1:]))
    Image.fromarray(rgb).save(MAPS/'world-hypsometric.png',optimize=True)
    metadata={'source':URL,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'dataset':'GMT IGPP Earth Relief 10 arc-minute, derived from SRTM15+V2.7 (Tozer et al., 2019)',
        'documentation':'https://www.generic-mapping-tools.org/remote-datasets/earth-relief.html',
        'license_documentation':'https://www.generic-mapping-tools.org/remote-datasets/',
        'land_mask':'Natural Earth 1:50m land (public domain)',
        'projection':'equirectangular EPSG:4326, bounds [-180,-90,180,90]',
        'size':[w,h],'sampling':'nearest; elevation/depth in metres, discrete colour bands, no hillshade',
        'land_bands':LAND,'sea_bands':SEA,
        'note':'现实高程仅作世界测试底图，不改变架空故事海拔/资源；约10角分分辨率，不是精细测绘。'}
    (MAPS/'world-hypsometric-source.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Built',MAPS/'world-hypsometric.png','range',float(heights.min()),float(heights.max()))

if __name__=='__main__':main()
