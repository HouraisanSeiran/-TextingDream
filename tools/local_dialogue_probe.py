"""Run real dialogue requests against a running loopback model using an isolated save."""
import argparse
import asyncio
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import ai_protocols  # noqa: E402
from app.contracts import Preferences, Turn  # noqa: E402
from app.service import Service  # noqa: E402
from app.storage import Store  # noqa: E402
from app.token_budget import output_tokens  # noqa: E402
from tools.playable_scenes import scenes  # noqa: E402


MESSAGES = (
    ('speech', '我想先听听你的看法，你现在关心什么？'),
    ('speech', '请解释刚才提到的条件，哪些是你确定知道的？'),
    ('speech', '我还没有答应交易，也没有交出钱物。我们先继续商量。'),
    ('thought', '这只是我没有说出口的疑问，先观察对方的表情。'),
    ('speech', '如果你没有亲自见过，就告诉我这是听说的。'),
    ('speech', '我们刚才确认了哪些条件？还有哪些事没有决定？'),
)


async def probe(base_url, model=None, turns=6, mode='scene', context_chars=6000,
                declared_context_tokens=8192, timeout=180):
    base_url = ai_protocols.api_base(base_url, 'openai')
    if not ai_protocols.local_endpoint(base_url):
        raise ValueError('本探针只允许本机回环模型地址')
    report = {'created': datetime.now(timezone.utc).isoformat(), 'mode': mode,
              'base_url': base_url, 'declared_context_tokens': declared_context_tokens,
              'context_chars': context_chars, 'output_limit_tokens': output_tokens('surface'),
              'requested_turns': turns, 'rows': [], 'traces': [],
              'quality_review': 'pending', 'status': 'error'}
    with tempfile.TemporaryDirectory(prefix='dream-dialogue-') as directory:
        root = Path(directory)
        service = Service(Store(root / 'probe.sqlite3'), root)
        service.provider.key = ''  # Never reuse an API credential from the environment.
        service.provider.configure({'timeout_seconds': timeout, 'max_concurrency': 1})
        service.store.put('settings', 'preferences',
                          Preferences(context_chars=context_chars, surface_thinking=False).model_dump())
        try:
            config = await service.provider.connect(base_url, 'openai', '', model)
            report['model'] = config['model']
            service.provider.configure({'thinking_mode': 'disabled'})
            data = scenes()[0]  # Reuse an existing fixture; do not create or publish a new story.
            if mode == 'plain':
                data['story']['mechanics'].pop('scene_judgment', None)
            for event in data['story']['events']:
                event['max_turns'] = turns + 1
            service.runtime.commit_package(data['story'], data['characters'], 'isolated local dialogue test')
            session = service.runtime.new_session('本地模型对话测试', 'protagonist')
            for index in range(turns):
                channel, message = MESSAGES[index % len(MESSAGES)]
                before = service.store.session(session['id'])
                started = perf_counter()
                try:
                    await service.turn(session['id'], Turn(message=message, channel=channel))
                except ValueError as error:
                    after = service.store.session(session['id'])
                    report['rows'].append({'turn': index + 1, 'input': message, 'channel': channel,
                                           'elapsed_ms': round((perf_counter() - started) * 1000),
                                           'error': str(error), 'save_unchanged': before == after})
                    raise
                after = service.store.session(session['id'])
                conversations = service.runtime.conversations(after)
                last_turn = conversations[-1]['turns'][-1]
                report['rows'].append({'turn': index + 1, 'input': message, 'channel': channel,
                                       'reply': last_turn['reply'], 'reply_chars': len(last_turn['reply']),
                                       'elapsed_ms': round((perf_counter() - started) * 1000),
                                       'usage': after['usage'][-1],
                                       'state_version': after['state_version']})
            report['status'] = 'transport_and_structure_passed'
        except ValueError as error:
            report['error'] = str(error)
        finally:
            report['traces'] = service.store.all('trace')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:18083/v1')
    parser.add_argument('--model')
    parser.add_argument('--turns', type=int, default=6, choices=range(1, 51), metavar='1..50')
    parser.add_argument('--mode', choices=('scene', 'plain'), default='scene')
    parser.add_argument('--context-chars', type=int, default=6000)
    parser.add_argument('--declared-context-tokens', type=int, default=8192,
                        help='Record the separately configured model-server window; not an automatic query')
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = asyncio.run(probe(args.base_url, args.model, args.turns, args.mode,
                              args.context_chars, args.declared_context_tokens, args.timeout))
    path = args.output or ROOT / 'artifacts' / 'local-dialogue' / (
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(str(path.resolve()))
    print(report['status'])
    if report['status'] != 'transport_and_structure_passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
