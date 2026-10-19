"""Exercise map rendering without touching real sessions or story documents."""
import hashlib
import json
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
import uvicorn
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.web import create_app

def hashes():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('StoryPackage','character_packages') for p in (ROOT/folder).rglob('*') if p.is_file()}

def main():
    before=hashes()
    with tempfile.TemporaryDirectory() as tmp:
        app=create_app(Path(tmp)/'test.sqlite3');app.state.service.provider.configure({'offline':True})
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(128)
        server=uvicorn.Server(uvicorn.Config(app,log_level='error'));worker=threading.Thread(target=lambda:server.run(sockets=[listener]),daemon=True);worker.start()
        try:
            for _ in range(100):
                if server.started:break
                time.sleep(.1)
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1100});errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto('http://127.0.0.1:'+str(listener.getsockname()[1]))
                page.locator('#session-title').fill('分层设色检查');page.locator('#new-form .primary').click();page.locator('#actions button').wait_for()
                page.locator('[data-page=world-workshop]').click();page.locator('#open-author-atlas').click()
                host=page.locator('#author-map')
                expect(host.locator('.atlas-basemap')).to_have_attribute('href','/maps/world-hypsometric.png')
                expect(host.locator('.terrain-legend')).to_contain_text('陆地海拔（米）')
                expect(host.locator('.terrain-legend')).to_contain_text('2000–3000')
                for name in ('矿产','沃土','人口承载'):
                    host.get_by_label(name,exact=True).check()
                expect(host.get_by_role('button',name='天朝都城 · 资源',exact=True)).to_be_visible()
                # Co-located resource and city markers overlap; use supported keyboard activation.
                host.get_by_role('button',name='天朝都城 · 资源',exact=True).press('Enter')
                expect(host.locator('.atlas-info')).to_contain_text('铁')
                host.get_by_label('地图样式').select_option('all');host.get_by_label('地图样式').select_option('terrain')
                for name in ('矿产','沃土','人口承载'):expect(host.get_by_label(name,exact=True)).to_be_checked()
                assert page.request.get(page.url.rstrip('/')+'/maps/world-hypsometric.png').status==200
                (ROOT/'artifacts/hypsometric').mkdir(parents=True,exist_ok=True)
                host.screenshot(path=str(ROOT/'artifacts/hypsometric/分层设色地图.png'))
                # Independent viewer: same height -> same fill regardless of terrain class.
                page.evaluate('''()=>{const host=document.createElement('div');host.id='band-check';document.body.append(host);const v=atlasViewer(host);v.update({features:[{id:'forest',name:'forest',layer:'terrain',terrain_kind:'forest',geometry:'polygon',coordinates:[[0,0],[1,0],[0,1]],environment:{elevation_m:500}},{id:'desert',name:'desert',layer:'terrain',terrain_kind:'desert',geometry:'polygon',coordinates:[[2,0],[3,0],[2,1]],environment:{elevation_m:500}},{id:'unknown',name:'unknown',layer:'terrain',terrain_kind:'mountain',geometry:'polygon',coordinates:[[4,0],[5,0],[4,1]]}]})}''')
                vals=page.locator('#band-check .atlas-feature').evaluate_all('(xs)=>xs.map(x=>({height:x.dataset.elevation,fill:x.querySelector("path").getAttribute("fill")}))')
                assert vals[0]['fill']==vals[1]['fill']=='#e1db91',vals
                assert vals[2]['fill']=='none',vals
                assert not errors,errors
                browser.close()
            assert before==hashes(),'Production story or characters changed'
            print('PASS: elevation bands, resource layers, toggles, image load, same-height colour, unknown outline, production data unchanged')
        finally:server.should_exit=True;worker.join(timeout=10);listener.close()

if __name__=='__main__':main()
