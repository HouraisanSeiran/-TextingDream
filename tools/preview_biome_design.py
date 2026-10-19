import json
from pathlib import Path
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
out=root/'artifacts/map-design'
fragment=Path('C:/Users/Huang/.codex/visualizations/2026/09/25/01a0d63f-5aa0-7711-8cf0-b7682afb6c93/biome-dual-grid.html')
text=fragment.read_text(encoding='utf-8')
if '__CATALOG__' in text:
    text=text.replace('__CATALOG__',json.dumps(json.loads((out/'biome-catalog.json').read_text(encoding='utf-8')),ensure_ascii=False))
    fragment.write_text(text,encoding='utf-8')
assert '\\"' not in text
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,channel='msedge')
    page=browser.new_page(viewport={'width':1000,'height':1000},device_scale_factor=1)
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content(text)
    page.screenshot(path=str(out/'preview-forest.png'),full_page=True)
    original=page.locator('#td-scene').evaluate('(c)=>c.toDataURL()')
    page.locator('#td-next').click()
    assert original!=page.locator('#td-scene').evaluate('(c)=>c.toDataURL()')
    assert page.locator('#td-biome-choice option').count()==67
    assert page.locator('#td-gallery canvas').count()==67
    page.locator('#td-grid').check()
    page.screenshot(path=str(out/'preview-dual-grid.png'),full_page=True)
    page.set_viewport_size({'width':360,'height':900})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(out/'preview-mobile.png'),full_page=True)
    page.set_viewport_size({'width':1000,'height':1000})
    page.locator('summary').click()
    page.locator('#td-gallery').screenshot(path=str(out/'all-biomes.png'))
    sheets=out/'biome-sheets'
    sheets.mkdir(exist_ok=True)
    catalog=json.loads((out/'biome-catalog.json').read_text(encoding='utf-8'))['biomes']
    for i,biome in enumerate(catalog):
        page.locator('#td-biome-choice').select_option(str(i))
        page.locator('#td-masks').screenshot(path=str(sheets/(biome['id']+'-16.png')))
    assert not errors,errors
    browser.close()
print('Design browser passed: 67 selectable biomes, 67 thumbnails, canvas changes, dual-grid toggle, 360px layout, no script errors')
