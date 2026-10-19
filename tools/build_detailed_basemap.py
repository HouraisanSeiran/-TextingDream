"""Build a local SVG from Natural Earth 1:50m public-domain vector datasets."""
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import httpx

ROOT=Path(__file__).resolve().parents[1]
BASE='https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/'
NAMES=['ne_50m_land','ne_50m_lakes','ne_50m_rivers_lake_centerlines']

def fetch(name):
    cache=ROOT/'assets/maps'/ (name+'.geojson')
    if cache.exists():return name,json.loads(cache.read_text(encoding='utf-8'))
    urls=[BASE+name+'.geojson', 'https://cdn.jsdelivr.net/gh/nvkelso/natural-earth-vector@master/geojson/'+name+'.geojson']
    for url in urls:
        try:
            r=httpx.get(url,follow_redirects=True,timeout=50)
            r.raise_for_status()
            data=r.json()
            cache.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
            return name,data
        except (httpx.HTTPError,ValueError):
            if url==urls[-1]:raise

def line(coords,close=False):
    return ' '.join(('M' if i==0 else 'L')+f'{(x+180)*4:.2f},{(90-y)*4:.2f}' for i,(x,y,*_) in enumerate(coords))+(' Z' if close else '')

def main():
    data=dict(ThreadPoolExecutor(3).map(fetch,NAMES))
    parts=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 720"><rect width="1440" height="720" fill="#172f3c"/>']
    for name in NAMES:
        color='#3c514a' if name.endswith('land') else '#234858'
        for f in data[name]['features']:
            g=f['geometry']
            if not g:continue
            typ,coords=g['type'],g['coordinates']
            if typ in ('Polygon','MultiPolygon'):
                polygons=[coords] if typ=='Polygon' else coords
                path=' '.join(line(ring,True) for poly in polygons for ring in poly)
                parts.append(f'<path d="{path}" fill="{color}" fill-rule="evenodd" stroke="#60766a" stroke-width="0.15"/>')
            elif typ in ('LineString','MultiLineString'):
                lines=[coords] if typ=='LineString' else coords
                parts.append('<path d="'+' '.join(line(x) for x in lines)+'" fill="none" stroke="#568797" stroke-width="0.23"/>')
    parts.append('</svg>')
    target=ROOT/'assets/maps/world-detailed.svg'
    target.write_text(''.join(parts),encoding='utf-8')
    (target.parent/'world-detailed-source.json').write_text(json.dumps({'source':'Natural Earth','scale':'1:50m','license':'Public domain','urls':[BASE+n+'.geojson' for n in NAMES], 'note':'现代自然地理仅用于测试底图，不表示架空世界的精确地形或历史疆域。'},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Built',target.name,target.stat().st_size,'bytes')

if __name__=='__main__':main()
