"""Local launcher: explicit interpreter, UTF-8 log and readiness check."""
import os
from pathlib import Path
import socket
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent


class Tee:
    def __init__(self, console, log):
        self.console, self.log = console, log

    def write(self, text):
        self.console.write(text)
        self.log.write(text)
        self.log.flush()

    def flush(self):
        self.console.flush()
        self.log.flush()

    def isatty(self):
        return False


def main():
    os.chdir(ROOT)
    (ROOT / 'logs').mkdir(exist_ok=True)
    log = (ROOT / 'logs' / 'startup.log').open('w', encoding='utf-8')
    sys.stdout = Tee(sys.stdout, log)
    sys.stderr = Tee(sys.stderr, log)
    try:
        print('TextileDream | Python:', sys.executable, flush=True)
        import uvicorn
        from app.main import app
        # Never terminate another application's process to obtain a port.
        listener = socket.socket()
        try:
            listener.bind(('127.0.0.1', 8000))
        except OSError:
            listener.bind(('127.0.0.1', 0))
        listener.listen(128)
        port = listener.getsockname()[1]
        url = f'http://127.0.0.1:{port}'
        print('Open:', url, flush=True)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        def ready():
            for _ in range(100):
                try:
                    with opener.open(url + '/openapi.json', timeout=0.5) as response:
                        if response.status == 200:
                            print('READY:', url, flush=True)
                            if os.getenv('TEXTILEDREAM_NO_BROWSER') != '1':
                                webbrowser.open(url)
                            return
                except OSError:
                    time.sleep(0.2)
            print('Readiness check failed. See logs/startup.log.', flush=True)

        threading.Thread(target=ready, daemon=True).start()
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port, log_config=None))
        try:
            server.run(sockets=[listener])
        finally:
            listener.close()
        return 0 if server.started else 1
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
