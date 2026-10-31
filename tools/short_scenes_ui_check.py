"""Exercise the short-scene UI in an isolated temporary database."""
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import uvicorn

from app.web import create_app
from tools.playable_scenes import ROOT, scenes


def main():
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(Path(tmp) / 'ui.sqlite3')
        svc = app.state.service
        svc.provider.configure({'offline': False, 'base_url': 'http://127.0.0.1:8082/v1',
                                'model': 'qwen3', 'dialogue_model': 'qwen3', 'api_key': 'local',
                                'max_tokens': 900})
        data = scenes()[0]
        svc.runtime.commit_package(data['story'], data['characters'], 'isolated UI check')
        session = svc.runtime.new_session('UI check', 'protagonist', profile_id='traveller')
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=8978, log_level='warning'))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        try:
            for _ in range(100):
                if server.started:
                    break
                time.sleep(.1)
            result = subprocess.run(['node', str(ROOT / 'tools/short_scenes_ui_probe.cjs'), session['id']], cwd=ROOT)
            raise SystemExit(result.returncode)
        finally:
            server.should_exit = True
            thread.join(timeout=10)


if __name__ == '__main__':
    main()
