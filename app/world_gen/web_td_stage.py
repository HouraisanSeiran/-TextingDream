"""Web job TD stage: run tools/td_coarse_ridges.py unchanged, then record the torch CUDA memory peak of this process.

  <Terragenesis venv python> app/world_gen/web_td_stage.py <td_coarse_ridges.py arguments>

Writes <out>/../td-gpu-peak.json (runtime only, never part of the product identity): device name, torch max allocated /
reserved MiB. Refuses to run when --device is cuda but CUDA is not usable (no silent CPU fallback).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    out = Path(argv[argv.index('--out') + 1]) if '--out' in argv else None
    want_cuda = '--device' in argv and argv[argv.index('--device') + 1].startswith('cuda')
    import torch
    if want_cuda and not torch.cuda.is_available():
        raise SystemExit('无可用显卡(no usable CUDA device): web TD stage does not fall back to CPU')
    import td_coarse_ridges
    td_coarse_ridges.main(argv)
    rec = dict(note='torch.cuda peak of the TD stage process (runtime only, not identity)', cuda=bool(want_cuda))
    if want_cuda:
        rec.update(device_name=torch.cuda.get_device_name(0),
                   max_memory_allocated_mib=round(torch.cuda.max_memory_allocated() / 2 ** 20, 1),
                   max_memory_reserved_mib=round(torch.cuda.max_memory_reserved() / 2 ** 20, 1))
    if out is not None:
        (out.parent / 'td-gpu-peak.json').write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding='utf-8')
    print('TD-GPU-PEAK ' + json.dumps(rec, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
