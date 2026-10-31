"""一键安装 / 启动 / 停止的共享实现（不依赖第三方包，仅标准库）。

三个职责分开，互不耦合：

* ``install``  —— 检查 Python（>=3.11，排除 Windows 商店占位）、建项目独立 ``.venv``、
  按 ``requirements.txt`` 装依赖、可选把 civ-atlas 本体装到 ``external/civ-atlas``。
* ``start``    —— 找空闲端口起 ``launch.py``，等就绪，写状态文件，成功才打开浏览器。
* ``stop``     —— 只停**自己启动过**的那个进程：PID + 命令行身份 + 启动时间三者一致才动手，
  绝不按端口杀，也不拿复用的 PID 误杀。

所有网络/安装动作默认先问，``--yes`` 才直接做；``--dry-run`` 只打印计划。
状态与日志落在 ``logs/``（已在 .gitignore 里），UTF-8 写入，不含任何密钥。
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / 'logs'
STATE_FILE = STATE_DIR / 'launcher-state.json'
LOG_DIR = STATE_DIR
VENV_DIR = ROOT / '.venv'
REQUIREMENTS = ROOT / 'requirements.txt'
LAUNCH_SCRIPT = ROOT / 'launch.py'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 8000

#: civ-atlas 固定来源（与 docs/civ-atlas-install.md 一致，不另猜版本）。
CIV_ATLAS_COMMIT = '0939c5f1622a5e45cfc16f645ea3845993ab3985'
CIV_ATLAS_URL = ('https://codeload.github.com/guaner-334/civ-atlas/tar.gz/'
                 + CIV_ATLAS_COMMIT)
CIV_ATLAS_BYTES = 30256136
CIV_ATLAS_SHA256 = '8FE4F3CB16CD81AEAC393789FFA5EF30093AA1245A561A456684E6CA7CDFEEBC'
CIV_ATLAS_DIR = ROOT / 'external' / 'civ-atlas'
CIV_ATLAS_PATCH = ROOT / 'docs' / 'civ-atlas-patch' / 'files'

MIN_PYTHON = (3, 11)
MIN_NODE_MAJOR = 22


class LauncherError(RuntimeError):
    """A refused or failed launcher step, with a readable reason."""


# --------------------------------------------------------------------- helpers
def say(text=''):
    print(text, flush=True)


def ask(question, assume_yes=False):
    """一回明确的确认。``--yes`` 视为已确认，其余情况必须有可交互的输入。"""
    if assume_yes:
        return True
    if not sys.stdin or not sys.stdin.isatty():
        raise LauncherError('需要确认但当前不是交互终端；请加 --yes 明确同意后再运行')
    answer = input(question + ' [y/N] ').strip().lower()
    return answer in ('y', 'yes')


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest().upper()


def ensure_state_dir():
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def read_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def write_state(state):
    ensure_state_dir()
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                          encoding='utf-8')


def clear_state():
    try:
        STATE_FILE.unlink()
    except OSError:
        pass


# ------------------------------------------------------------------ python/venv
def python_version_ok(exe):
    """Run ``exe -c`` for the version tuple. Windows Store stubs pass --version but
    fail on real work, so this asks the interpreter to actually compute something."""
    try:
        done = subprocess.run(
            [str(exe), '-c', 'import sys;print("%d.%d.%d" % sys.version_info[:3])'],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', (done.stdout or '').strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def find_base_python():
    """一列候选解释器，返回第一个真能执行且 >=3.11 的（先看已有 .venv）。"""
    venv_python = VENV_DIR / ('Scripts' if os.name == 'nt' else 'bin') / (
        'python.exe' if os.name == 'nt' else 'python')
    candidates = []
    if venv_python.exists():
        candidates.append(venv_python)
    if os.environ.get('TEXTILEDREAM_PYTHON'):
        candidates.append(Path(os.environ['TEXTILEDREAM_PYTHON']))
    candidates.append(Path(sys.executable))
    if os.name == 'nt':
        candidates.append(Path(shutil.which('python') or ''))
        candidates.append(Path(shutil.which('py') or ''))
    else:
        candidates.extend([Path(shutil.which('python3') or ''),
                           Path(shutil.which('python') or '')])
    for candidate in candidates:
        if not candidate or not str(candidate).strip():
            continue
        if not Path(candidate).exists():
            continue
        version = python_version_ok(candidate)
        if version and version[:2] >= MIN_PYTHON:
            return Path(candidate), version
    return None, None


def venv_python():
    return VENV_DIR / ('Scripts' if os.name == 'nt' else 'bin') / (
        'python.exe' if os.name == 'nt' else 'python')


def ensure_venv(base_python, dry_run=False):
    if venv_python().exists():
        say('  已有项目 .venv：' + str(VENV_DIR))
        return venv_python()
    say('  将创建项目独立虚拟环境：' + str(VENV_DIR))
    if dry_run:
        return None
    subprocess.run([str(base_python), '-m', 'venv', str(VENV_DIR)], check=True)
    return venv_python()


def install_requirements(py, dry_run=False, upgrade=False):
    args = [str(py), '-m', 'pip', 'install', '--disable-pip-version-check']
    if upgrade:
        args.append('--upgrade')
    args += ['-r', str(REQUIREMENTS)]
    say('  ' + ' '.join(args))
    if dry_run:
        return
    done = subprocess.run(args, capture_output=True, text=True)
    if done.returncode != 0:
        tail = (done.stderr or done.stdout or '')[-800:]
        raise LauncherError('安装依赖失败：\n' + tail)


def deps_ready(py):
    """不联网的依赖就绪检查：只 import 名字，不装东西。"""
    code = ('import fastapi, uvicorn, pydantic, httpx, jinja2, PIL;'
            'print("ok")')
    done = subprocess.run([str(py), '-c', code], capture_output=True, text=True)
    return done.returncode == 0


# ---------------------------------------------------------------- civ-atlas body
def node_version():
    exe = shutil.which('node')
    if not exe:
        return None
    try:
        done = subprocess.run([exe, '--version'], capture_output=True, text=True,
                              timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.match(r'^v(\d+)\.', (done.stdout or '').strip())
    return int(match.group(1)) if match else None


def civ_atlas_present():
    return (CIV_ATLAS_DIR / 'package.json').exists()


def install_civ_atlas(dry_run=False, assume_yes=False):
    """下载官方固定源码包 → 校验大小与 SHA-256 → 安全解包 → 打补丁。

    已存在的目录**不覆盖**（可能是作者改过的），只在缺失时安装。
    """
    if civ_atlas_present():
        say('  已有 external/civ-atlas，不覆盖（如需重装请自行移走该目录）。')
        return
    major = node_version()
    if major is None or major < MIN_NODE_MAJOR:
        raise LauncherError(
            'civ-atlas 需要 Node >= %d（当前 %s）。请从 https://nodejs.org 安装 LTS，'
            '不要用本项目自动装系统运行时。' % (MIN_NODE_MAJOR, major))
    if not ask('将下载 civ-atlas 源码包（约 %d MB，固定 commit %s）并装到 '
               'external/civ-atlas，继续吗？' % (CIV_ATLAS_BYTES // (1024 * 1024),
                                                CIV_ATLAS_COMMIT[:8]), assume_yes):
        say('  已跳过地图生成器安装（织梦本体不依赖它）。')
        return
    archive = STATE_DIR / 'civ-atlas.tar.gz'
    say('  下载：' + CIV_ATLAS_URL)
    if dry_run:
        say('  [dry-run] 跳过下载与解包')
        return
    ensure_state_dir()
    try:
        with urllib.request.urlopen(CIV_ATLAS_URL, timeout=60) as response, \
                open(archive, 'wb') as handle:
            shutil.copyfileobj(response, handle)
    except (urllib.error.URLError, OSError) as error:
        raise LauncherError('下载失败：%s\n（网络不通时可稍后手动按 docs/civ-atlas-install.md '
                            '安装，织梦本体不受影响）' % error)
    size = archive.stat().st_size
    if size != CIV_ATLAS_BYTES:
        raise LauncherError('源码包大小不符（%d ≠ %d），拒绝解包' % (size, CIV_ATLAS_BYTES))
    digest = sha256_of(archive)
    if digest != CIV_ATLAS_SHA256:
        raise LauncherError('源码包 SHA-256 不符，拒绝解包')
    unpack_safely(archive)
    apply_patch()


def unpack_safely(archive):
    """只用 tarfile 的 data 过滤：拒绝绝对路径、``..`` 穿越与链接条目。"""
    import tarfile
    target = ROOT / 'external'
    target.mkdir(parents=True, exist_ok=True)
    staging = target / ('_unpack_' + str(int(time.time())))
    staging.mkdir()
    try:
        with tarfile.open(archive) as bundle:
            for member in bundle.getmembers():
                name = member.name.replace('\\', '/')
                if name.startswith('/') or '..' in name.split('/'):
                    raise LauncherError('源码包含不安全的路径：' + member.name)
                if member.issym() or member.islnk():
                    raise LauncherError('源码包含链接条目，拒绝解包：' + member.name)
            previous = os.getcwd()
            os.chdir(staging)
            try:
                bundle.extractall('.')
            finally:
                os.chdir(previous)
        roots = [item for item in staging.iterdir() if item.is_dir()]
        source = roots[0] if len(roots) == 1 else staging
        if CIV_ATLAS_DIR.exists():
            raise LauncherError('目标目录已存在，拒绝覆盖')
        shutil.move(str(source), str(CIV_ATLAS_DIR))
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        try:
            archive.unlink()
        except OSError:
            pass


def apply_patch():
    """按相对路径应用仓内补丁，包括原生地图宿主及共享前端组件。"""
    if not CIV_ATLAS_PATCH.exists():
        say('  未找到 patch 目录，跳过打补丁（地图导出入口可能不存在）。')
        return
    sources = sorted(path for path in CIV_ATLAS_PATCH.rglob('*') if path.is_file())
    for src in sources:
        dst = CIV_ATLAS_DIR / src.relative_to(CIV_ATLAS_PATCH)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    say(f'  已应用织梦前端补丁（{len(sources)} 个文件）。')


def civ_atlas_hint():
    return ('\n  安装地图生成器（可选，需要 Node >= %d）：\n'
            '    python tools/bootstrap.py install --with-map --yes\n'
            '  或按 docs/civ-atlas-install.md 手动安装。' % MIN_NODE_MAJOR)


# ----------------------------------------------------------------------- ports
def port_free(port, host=DEFAULT_HOST):
    with socket.socket() as probe:
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


def pick_port(preferred=DEFAULT_PORT, host=DEFAULT_HOST):
    """先用约定端口，被占就让系统给一个空闲的——不杀别的进程腾端口。"""
    if preferred and port_free(preferred, host):
        return int(preferred)
    with socket.socket() as probe:
        probe.bind((host, 0))
        return probe.getsockname()[1]


def port_reachable(host, port, timeout=1.0):
    """一次 TCP 连通性试探：端口上有没有人在监听。"""
    probe = socket.socket()
    probe.settimeout(timeout)
    try:
        probe.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        probe.close()


def wait_ready(url, timeout=90.0):
    """就绪 = 端口真的能连上，且 ``/openapi.json`` 返回 200。"""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname or DEFAULT_HOST
    target = parsed.port or 80
    deadline = time.time() + timeout
    while time.time() < deadline:
        # 先确认端口上真有监听：没有就直接当作「还没好」，
        # 不去猜测各类 HTTP 客户端异常的含义（那样会把死端口误判成就绪）。
        if not port_reachable(host, target):
            time.sleep(0.3)
            continue
        try:
            with opener.open(url + '/openapi.json', timeout=1.0) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.3)
    return False


# ------------------------------------------------------------- civ-atlas service
#: 项目内受控的 pnpm 版本（与上游 packageManager 一致；仅装进 .tools，不碰全局）。
PNPM_VERSION = '11.24.0'
TOOLS_DIR = ROOT / '.tools'
VITE_ENTRY = CIV_ATLAS_DIR / 'node_modules' / 'vite' / 'bin' / 'vite.js'
ESBUILD_DIR = CIV_ATLAS_DIR / 'node_modules' / '@esbuild'


def node_executable():
    return shutil.which('node')


def local_pnpm():
    """项目内已装的 pnpm 可执行文件（Windows 是 .cmd 包装，仍由 node 调用其 js）。"""
    base = TOOLS_DIR / 'pnpm'
    candidates = [
        base / 'node_modules' / 'pnpm' / 'bin' / 'pnpm.cjs',
        base / 'node_modules' / 'pnpm' / 'bin' / 'pnpm.js',
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def civ_atlas_deps_ready():
    """vite 与 esbuild 的本地文件在不在（不靠「装过就算好」）。"""
    if not VITE_ENTRY.exists():
        return False, '缺少 node_modules/vite/bin/vite.js'
    if not ESBUILD_DIR.exists():
        return False, '缺少 node_modules/@esbuild（vite 运行时需要它的本地二进制）'
    return True, ''


def install_pnpm(assume_yes=False, dry_run=False):
    """把固定版本 pnpm 装进项目 .tools（不全局、不改 registry）。"""
    node = node_executable()
    if not node:
        raise LauncherError('缺少 Node：请从 https://nodejs.org 安装 LTS（>= %d）'
                            % MIN_NODE_MAJOR)
    existing = local_pnpm()
    if existing:
        say('  项目内 pnpm 已就绪：' + str(existing))
        return existing
    if not ask('需要在项目目录 .tools 里安装 pnpm@%s（会联网，不装全局），继续吗？'
               % PNPM_VERSION, assume_yes):
        raise LauncherError('未获授权安装 pnpm；可稍后带 --yes 重跑')
    if dry_run:
        say('  [dry-run] 跳过 pnpm 安装')
        return None
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    package = TOOLS_DIR / 'pnpm' / 'package.json'
    package.parent.mkdir(parents=True, exist_ok=True)
    package.write_text(json.dumps({'name': 'zhimeng-tools', 'private': True,
                                   'dependencies': {'pnpm': PNPM_VERSION}}, indent=2),
                       encoding='utf-8')
    # 用 node 直接跑 npm 的 cli，避免依赖 PATH 里的 npm 包装脚本。
    npm_cli = Path(node).parent / 'node_modules' / 'npm' / 'bin' / 'npm-cli.js'
    if not npm_cli.exists():
        npm_cli = Path(shutil.which('npm') or '')
    if not npm_cli or not str(npm_cli):
        raise LauncherError('找不到 npm（Node 自带）；请重装 Node LTS')
    done = subprocess.run(
        [node, str(npm_cli), 'install', '--no-audit', '--no-fund',
         '--ignore-scripts', '--prefix', str(package.parent)],
        cwd=str(package.parent), capture_output=True, text=True)
    if done.returncode != 0:
        raise LauncherError('安装 pnpm 失败：' + (done.stderr or '')[-500:])
    found = local_pnpm()
    if not found:
        raise LauncherError('pnpm 安装后仍找不到可执行文件，请检查 .tools 目录')
    return found


def install_civ_atlas_deps(assume_yes=False, dry_run=False):
    """在 external/civ-atlas 里用项目内 pnpm 装依赖（ignore-scripts + frozen-lockfile）。"""
    if not civ_atlas_present():
        raise LauncherError('还没装 civ-atlas 本体：先跑 install --with-map')
    ready, reason = civ_atlas_deps_ready()
    if ready:
        say('  civ-atlas 前端依赖已就绪（vite/esbuild 本地文件都在）')
        return True
    node = node_executable()
    if not node:
        raise LauncherError('缺少 Node：请从 https://nodejs.org 安装（>= %d）'
                            % MIN_NODE_MAJOR)
    pnpm = install_pnpm(assume_yes=assume_yes, dry_run=dry_run)
    if dry_run:
        say('  [dry-run] 跳过 civ-atlas 依赖安装')
        return False
    if not ask('将用项目内 pnpm 在 external/civ-atlas 安装前端依赖'
               '（--ignore-scripts --frozen-lockfile，联网），继续吗？', assume_yes):
        raise LauncherError('未获授权安装 civ-atlas 依赖')
    # 由 node 直接跑 pnpm 的 js：不走 packageManager 字段的全局分派。
    done = subprocess.run(
        [node, str(pnpm), 'install', '--ignore-scripts', '--frozen-lockfile',
         '--config.manage-package-manager-versions=false'],
        cwd=str(CIV_ATLAS_DIR), capture_output=True, text=True,
        env={**os.environ, 'CI': 'true'})
    if done.returncode != 0:
        raise LauncherError('civ-atlas 依赖安装失败：' + (done.stderr or '')[-800:])
    ready, reason = civ_atlas_deps_ready()
    if not ready:
        # 装了但 vite/esbuild 跑不了：如实报缺，不谎称可用。
        raise LauncherError('依赖装完但前端仍不可用：%s' % reason)
    say('  civ-atlas 前端依赖就绪')
    return True


def start_map_service(state, dry_run=False, assume_yes=False, host=DEFAULT_HOST):
    """起 civ-atlas 的 vite（node 直接调用），记录 URL/PID/身份到状态文件。"""
    if not civ_atlas_present():
        raise LauncherError('还没装 civ-atlas 本体：先跑 install --with-map')
    existing = (state.get('map') or {})
    if existing.get('pid') and is_our_process(int(existing['pid']), existing):
        if wait_ready(existing.get('url'), timeout=3.0):
            say('  地图服务已在运行：' + existing['url'])
            return existing['url']
    if not civ_atlas_deps_ready()[0]:
        install_civ_atlas_deps(assume_yes=assume_yes, dry_run=dry_run)
    node = node_executable()
    if not node:
        raise LauncherError('缺少 Node')
    port = pick_port(5188, host)
    url = 'http://%s:%d' % (host, port)
    say('  启动地图生成器：%s' % url)
    if dry_run:
        say('  [dry-run] 未真正启动 vite')
        return None
    log_path = LOG_DIR / 'civ-atlas.log'
    handle = open(log_path, 'w', encoding='utf-8')
    try:
        proc = subprocess.Popen(
            [node, str(VITE_ENTRY), '--host', host, '--port', str(port), '--strictPort'],
            cwd=str(CIV_ATLAS_DIR), stdout=handle, stderr=subprocess.STDOUT)
    finally:
        handle.close()
    info = process_info(proc.pid) or {}
    fresh = read_state()
    fresh['map'] = {'pid': proc.pid, 'url': url, 'port': port,
                    'created': info.get('created'),
                    'command': info.get('command') or str(VITE_ENTRY),
                    'started': time.strftime('%Y-%m-%dT%H:%M:%S')}
    write_state(fresh)
    if not wait_ready(url, timeout=60.0):
        say('  地图服务未在超时内就绪，日志：%s' % log_path)
        raise LauncherError('地图生成器启动失败，详见 %s' % log_path)
    return url


def stop_map_service(dry_run=False):
    state = read_state()
    entry = state.get('map') or {}
    pid = entry.get('pid')
    if not pid:
        return 0
    pid = int(pid)
    if not process_alive(pid):
        if not dry_run:
            state['map'] = None
            write_state(state)
        return 0
    if not is_our_process(pid, entry):
        raise LauncherError('地图服务的 PID %d 身份不符，拒绝停止' % pid)
    say('停止地图服务 PID %d（%s）' % (pid, entry.get('url')))
    if dry_run:
        return 0
    if not terminate(pid):
        raise LauncherError('地图服务未能结束，状态保留')
    state = read_state()
    state['map'] = None
    write_state(state)
    return 0


# ----------------------------------------------------------------- start/stop
def process_info(pid):
    """一次拿到进程的「命令 + 创建时间」，用作身份指纹（Windows 走 Get-CimInstance）。"""
    if os.name == 'nt':
        query = ('(Get-CimInstance Win32_Process -Filter \'ProcessId=%d\' | '
                 'Select-Object CommandLine,CreationDate | '
                 'ForEach-Object { "$($_.CommandLine)`t$($_.CreationDate)" })' % pid)
        done = subprocess.run(['powershell', '-NoProfile', '-Command', query],
                              capture_output=True, text=True, cwd=str(ROOT))
        text = (done.stdout or '').strip()
        if done.returncode != 0 or not text:
            return None
        command, _, created = text.partition('\t')
        return {'command': command.strip() or None, 'created': created.strip() or None}
    proc = Path('/proc/%d' % pid)
    cmdline = proc / 'cmdline'
    if not cmdline.exists():
        return None
    command = cmdline.read_bytes().replace(b'\x00', b' ').decode('utf-8', 'replace').strip()
    created = None
    try:
        stat = (proc / 'stat').read_text(encoding='utf-8', errors='replace').split()
        created = stat[21] if len(stat) > 21 else None
    except OSError:
        pass
    return {'command': command or None, 'created': created}


def process_alive(pid):
    """PID 是否还存在（不判断是谁）。"""
    if os.name == 'nt':
        done = subprocess.run(['tasklist', '/FI', 'PID eq %d' % pid, '/FO', 'CSV',
                               '/NH'], capture_output=True, text=True)
        return str(pid) in (done.stdout or '')
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def process_identity(pid):
    """兼容旧名：只回「进程在不在」。"""
    return process_alive(pid)


def is_our_process(pid, recorded):
    """PID 还活着、命令行指向本项目、且创建时间与记录一致，才算「我们启动的那个」。

    任一项取不到就当作不匹配：误杀别人的进程比多启动一个要糟糕得多。
    """
    if not recorded:
        return False
    info = process_info(pid)
    if not info:
        return False
    command = (info.get('command') or '').lower()
    marker = str(LAUNCH_SCRIPT).lower()
    if marker not in command and not command.startswith(str(ROOT).lower()):
        if str(ROOT).lower() not in command:
            return False
    recorded_started = str(recorded.get('created') or '')
    actual_created = str(info.get('created') or '')
    if recorded_started and actual_created:
        return recorded_started[:19] == actual_created[:19]
    return marker in command


def start(port=None, dry_run=False, assume_yes=False, open_browser=True,
          host=DEFAULT_HOST, with_map=False):
    state = read_state()
    if state.get('pid') and is_our_process(int(state['pid']), state):
        url = state.get('url')
        if url and wait_ready(url, timeout=5.0):
            say('服务已在运行：%s（复用，不重复启动）' % url)
            map_url = (state.get('map') or {}).get('url')
            if map_url and not wait_ready(map_url, timeout=3.0):
                map_url = None
            if with_map and not map_url:
                say('地图服务还没起，补起一个。')
                map_url = start_map_service(state, dry_run=dry_run, assume_yes=assume_yes)
            if open_browser:
                webbrowser.open(url)          # 只开一次，且只开织梦本体
            if map_url:
                say('地图工具：' + map_url)
            return 0
        say('状态文件里的进程还活着但未就绪，先停止它。')
        stop(dry_run=dry_run)

    py = venv_python()
    if not py.exists():
        base, version = find_base_python()
        if not base:
            raise LauncherError(
                '没有找到可用的 Python >= %d.%d。请从 https://www.python.org/downloads/'
                ' 安装（勾选 Add to PATH），或用 TEXTILEDREAM_PYTHON 指定解释器。'
                % MIN_PYTHON)
        say('使用 Python %s：%s' % ('.'.join(map(str, version)), base))
        py = ensure_venv(base, dry_run=dry_run)
        if dry_run:
            say('  [dry-run] 未创建 .venv')
            return 0
    if not deps_ready(py):
        if not ask('项目依赖尚未安装，现在用 pip 安装吗？', assume_yes):
            raise LauncherError('依赖未安装，已取消启动')
        install_requirements(py)

    chosen = port or pick_port()
    url = 'http://%s:%d' % (host, chosen)
    say('启动：%s' % url)
    if dry_run:
        say('  [dry-run] 未真正启动进程')
        return 0
    ensure_state_dir()
    # 两个写者不能写同一个文件：启动器的转发日志与应用自己的 startup.log 分开。
    child_log = LOG_DIR / 'launcher-child.log'
    env = dict(os.environ)
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    env['TEXTILEDREAM_PORT'] = str(chosen)
    # 浏览器由启动器在「确认就绪」之后统一开一次，子进程不要再开一个。
    env['TEXTILEDREAM_NO_BROWSER'] = '1'
    creation = 0
    if os.name == 'nt':
        creation = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
    handle = open(child_log, 'w', encoding='utf-8')
    try:
        proc = subprocess.Popen([str(py), '-X', 'utf8', str(LAUNCH_SCRIPT)],
                                cwd=str(ROOT), stdout=handle, stderr=subprocess.STDOUT,
                                env=env, creationflags=creation)
    finally:
        handle.close()
    info = process_info(proc.pid) or {}
    state = {'pid': proc.pid, 'url': url, 'port': chosen,
             'created': info.get('created'),
             'command': info.get('command') or '%s -X utf8 %s' % (py, LAUNCH_SCRIPT),
             'started': time.strftime('%Y-%m-%dT%H:%M:%S'),
             'map': None}
    write_state(state)
    say('等待就绪…（子进程日志：%s，应用日志：%s）'
        % (child_log, LOG_DIR / 'startup.log'))
    if not wait_ready(url):
        # 就绪失败：把子进程收掉，但保留状态与日志供诊断，不谎称启动成功。
        say('启动未在超时内就绪。日志：%s 与 %s' % (child_log, LOG_DIR / 'startup.log'))
        return 1
    say('READY: ' + url)
    if with_map:
        map_url = start_map_service(state, dry_run=dry_run, assume_yes=assume_yes)
        state = read_state()
        if map_url:
            say('地图工具：' + map_url)
    if open_browser:
        webbrowser.open(url)
    return 0



def stop(dry_run=False):
    state = read_state()
    pid = state.get('pid')
    if not pid:
        say('没有本项目启动记录，无需停止。')
        return 0
    pid = int(pid)
    if not process_alive(pid):
        say('记录的进程 %d 已不在，清理状态文件。' % pid)
        if not dry_run:
            clear_state()
        return 0
    # 身份核对：命令行 + 创建时间，由 is_our_process 一次做完。
    if not is_our_process(pid, state):
        raise LauncherError(
            'PID %d 不是本项目启动的那个进程（命令或启动时间不符），拒绝停止；'
            '如确认残留，请手动处理 %s' % (pid, STATE_FILE))
    say('停止 PID %d（%s）' % (pid, state.get('url')))
    if dry_run:
        say('  [dry-run] 未真正终止')
        return 0
    if not terminate(pid):
        # 没停成就不清状态文件、也不报成功：下次还能看到它。
        raise LauncherError('PID %d 未能在本次尝试中结束，状态保留，请重试或手动结束'
                            % pid)
    # 先停地图（它记录在同一份状态文件里），再清本体状态。
    stop_map_service(dry_run=dry_run)
    clear_state()
    say('已停止。')
    return 0


def process_command_line(pid):
    if os.name == 'nt':
        code = ('powershell -NoProfile -Command "(Get-CimInstance Win32_Process '
                '-Filter \'ProcessId=%d\').CommandLine"' % pid)
        done = subprocess.run(code, capture_output=True, text=True, shell=False,
                              cwd=str(ROOT))
        text = (done.stdout or '').strip()
        return text or None
    proc = Path('/proc/%d/cmdline' % pid)
    if proc.exists():
        return proc.read_bytes().replace(b'\x00', b' ').decode('utf-8', 'replace')
    return None


def terminate(pid):
    """终止进程树；返回是否真的停了（不靠一句「已停止」冒充成功）。"""
    if os.name == 'nt':
        done = subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'],
                              capture_output=True, text=True)
        return done.returncode == 0 or not process_alive(pid)
    os.kill(pid, 15)
    return not process_alive(pid)


# -------------------------------------------------------------------- commands
def cmd_check(args):
    say('项目根：' + str(ROOT))
    base, version = find_base_python()
    if base:
        say('Python：%s（%s）' % (base, '.'.join(map(str, version))))
    else:
        say('Python：未找到 >= %d.%d 的解释器' % MIN_PYTHON)
    py = venv_python()
    say('.venv：%s' % ('已存在' if py.exists() else '未创建'))
    if py.exists():
        say('依赖：%s' % ('就绪' if deps_ready(py) else '缺失'))
    major = node_version()
    say('Node：%s' % (('v%d' % major) if major else '未安装'))
    say('civ-atlas：%s' % ('已安装' if civ_atlas_present() else '未安装'))
    say('端口 %d：%s' % (DEFAULT_PORT, '空闲' if port_free(DEFAULT_PORT) else '被占用（会自动换一个）'))
    state = read_state()
    if state.get('pid') and process_identity(int(state['pid'])):
        say('运行中：%s（PID %s）' % (state.get('url'), state.get('pid')))
    else:
        say('运行中：否')
    return 0


def cmd_install(args):
    say('== 安装 ==')
    base, version = find_base_python()
    if not base:
        raise LauncherError(
            '没有找到 Python >= %d.%d。请安装 https://www.python.org/downloads/ 的版本'
            '（不要用 Microsoft Store 的占位版），或用 TEXTILEDREAM_PYTHON 指定。'
            % MIN_PYTHON)
    say('Python %s：%s' % ('.'.join(map(str, version)), base))
    py = ensure_venv(base, dry_run=args.dry_run)
    if not args.dry_run:
        install_requirements(py, dry_run=args.dry_run, upgrade=args.upgrade)
        if not deps_ready(py):
            raise LauncherError('依赖安装后仍无法 import，请查看上面的 pip 输出')
        say('  依赖就绪')
    if args.with_map:
        install_civ_atlas(dry_run=args.dry_run, assume_yes=args.yes)
    else:
        say('  未安装地图生成器（可选）。' + civ_atlas_hint())
    if args.build_encyclopedia:
        say('  构建百科库（幂等，--with-traits）…')
        if not args.dry_run:
            done = subprocess.run([str(py), '-X', 'utf8',
                                   str(ROOT / 'tools' / 'encyclopedia_build.py'),
                                   '--with-traits'], cwd=str(ROOT),
                                  capture_output=True, text=True)
            if done.returncode != 0:
                raise LauncherError('百科库构建失败：' + (done.stderr or '')[-600:])
    say('安装完成。下一步：python tools/bootstrap.py start')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='bootstrap',
        description='织梦一键安装 / 启动 / 停止（Windows 与类 Unix 通用）')
    parser.add_argument('--dry-run', action='store_true', help='只打印计划，不做改动')
    parser.add_argument('--yes', action='store_true', help='对所有确认回答 yes')
    sub = parser.add_subparsers(dest='command')

    sub.add_parser('check', help='只读检查环境与运行状态')

    p_install = sub.add_parser('install', help='建 .venv 并安装依赖')
    p_install.add_argument('--with-map', action='store_true',
                           help='同时安装 civ-atlas 地图生成器（需 Node >= %d）'
                                % MIN_NODE_MAJOR)
    p_install.add_argument('--build-encyclopedia', action='store_true',
                           help='安装后构建百科库（--with-traits，幂等）')
    p_install.add_argument('--upgrade', action='store_true',
                           help='pip 使用 --upgrade（默认不升级已有包）')
    # 子命令后面也能写 --dry-run / --yes（双写在 argparse 里不会冲突，因为两处都是
    # 同一份 namespace 的默认值，后解析的子命令参数会覆盖父命令）。
    p_install.add_argument('--dry-run', action='store_true', default=argparse.SUPPRESS,
                           help=argparse.SUPPRESS)
    p_install.add_argument('--yes', action='store_true', default=argparse.SUPPRESS,
                           help=argparse.SUPPRESS)

    p_start = sub.add_parser('start', help='启动服务并在就绪后打开浏览器')
    p_start.add_argument('--port', type=int, default=None,
                         help='指定端口（默认 %d，占用时自动换）' % DEFAULT_PORT)
    p_start.add_argument('--no-browser', action='store_true', help='不自动开浏览器')
    p_start.add_argument('--with-map', action='store_true',
                         help='同时启动 civ-atlas 地图生成器（需已装本体与前端依赖）')
    p_start.add_argument('--dry-run', action='store_true', default=argparse.SUPPRESS,
                           help=argparse.SUPPRESS)
    p_start.add_argument('--yes', action='store_true', default=argparse.SUPPRESS,
                           help=argparse.SUPPRESS)

    p_stop = sub.add_parser('stop', help='停止本项目启动的服务')
    p_stop.add_argument('--dry-run', action='store_true', default=argparse.SUPPRESS,
                        help=argparse.SUPPRESS)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 2
    try:
        if args.command == 'check':
            return cmd_check(args)
        if args.command == 'install':
            return cmd_install(args)
        if args.command == 'start':
            return start(port=args.port, dry_run=args.dry_run, assume_yes=args.yes,
                         open_browser=not args.no_browser, with_map=args.with_map)
        if args.command == 'stop':
            return stop(dry_run=args.dry_run)
    except LauncherError as error:
        say('错误：' + str(error))
        return 1
    return 2
