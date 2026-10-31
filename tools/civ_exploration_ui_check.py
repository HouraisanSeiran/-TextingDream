"""Real civ snapshot and browser flow, with all generated journeys in a temporary store."""
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import uvicorn

from app.storage import Store
from app.web import create_app
from app import native_worlds

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = Store(ROOT / 'data/textiledream.sqlite3')
    records = native_worlds.listing(source)
    if not records:
        raise RuntimeError('请先在本地生成一份 civ 世界')
    record = source.get('map_import', records[0]['import_id'])
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root/'map_imports').mkdir()
        shutil.copyfile(ROOT/'data/map_imports'/record['file'], root/'map_imports'/record['file'])
        app = create_app(root/'test.sqlite3')
        app.state.service.store.put('map_import',record['id'],record)
        app.state.service.provider.configure({'offline':True})
        server = uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8979,log_level='warning'))
        thread = threading.Thread(target=server.run,daemon=True)
        thread.start()
        try:
            for _ in range(100):
                if server.started:
                    break
                time.sleep(.1)
            result = subprocess.run(['node',str(ROOT/'tools/civ_exploration_ui_probe.cjs')],cwd=ROOT)
            raise SystemExit(result.returncode)
        finally:
            server.should_exit=True
            thread.join(timeout=10)


if __name__=='__main__':
    main()
