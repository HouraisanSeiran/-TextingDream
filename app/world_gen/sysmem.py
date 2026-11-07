"""Available physical memory and process listing without a hard psutil dependency.

psutil is used when installed. On Windows the fallback is ctypes GlobalMemoryStatusEx (memory) and a PowerShell CIM
query (process command lines). Other platforms without psutil get a clear error; thresholds are not changed here.
"""
from __future__ import annotations

import json
import subprocess
import sys


def available_memory_bytes():
    try:
        import psutil
        return int(psutil.virtual_memory().available)
    except ImportError:
        pass
    if sys.platform == 'win32':
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                        ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                        ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                        ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                        ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]

        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise RuntimeError('GlobalMemoryStatusEx failed; cannot determine available memory')
        return int(status.ullAvailPhys)
    raise RuntimeError('cannot determine available memory: install psutil (no Windows ctypes fallback on this platform)')


def command_lines():
    """[(pid, command line)] of running processes."""
    try:
        import psutil
        return [(p.info['pid'], ' '.join(p.info.get('cmdline') or [])) for p in psutil.process_iter(['pid', 'cmdline'])]
    except ImportError:
        pass
    if sys.platform != 'win32':
        raise RuntimeError('cannot list processes: install psutil')
    out = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command',
                          'Get-CimInstance Win32_Process | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress'],
                         capture_output=True, text=True, timeout=30, check=True, encoding='utf-8').stdout
    rows = json.loads(out or '[]')
    rows = [rows] if isinstance(rows, dict) else rows
    return [(r['ProcessId'], r.get('CommandLine') or '') for r in rows]
