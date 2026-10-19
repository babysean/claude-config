#!/usr/bin/env python3
"""token-metrics.py --by-mode 점검: python3 scripts/test_token_metrics.py"""
import importlib.util, json, os, subprocess, sys, tempfile

spec = importlib.util.spec_from_file_location(
    'tm', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'token-metrics.py'))
tm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tm)


def user(sid, ts, text, **kw):
    return {'type': 'user', 'sessionId': sid, 'timestamp': ts, 'message': {'content': text}, **kw}


def asst(sid, ts, n, **kw):
    return {'type': 'assistant', 'sessionId': sid, 'timestamp': ts,
            'message': {'usage': {'input_tokens': n}}, **kw}


def write(root, name, events):
    with open(os.path.join(root, 'proj', name), 'w') as f:
        f.write('\n'.join(json.dumps(e) for e in events))


with tempfile.TemporaryDirectory() as root:
    os.makedirs(os.path.join(root, 'proj'))
    # (a) 같은 세션이 두 파일에 나뉘고, 나중 timestamp 줄(mode:late)이 앞 파일에 있다
    write(root, 'a.jsonl', [
        user('A', '2026-10-01T00:00:09Z', '[mode:late] 늦은 태그'),
        user('A', '2026-10-01T00:00:01Z', '[mode:role] PR 고쳐줘'),
        asst('A', '2026-10-01T00:00:02Z', 100),
        asst('A', '2026-10-01T00:00:03Z', 40, isSidechain=True),
        user('A', '2026-10-01T00:00:04Z', '아니 그게 아니라 다시 해'),
        user('A', '2026-10-01T00:00:05Z', '<command-name>/x</command-name> 아니 틀렸'),  # 제외
        # (b) 사이드체인 user 는 무시
        user('A', '2026-10-01T00:00:00Z', '[mode:side] 아니 틀렸', isSidechain=True),
        # (d) peer 발화는 교정 무시
        user('A', '2026-10-01T00:00:06Z', '아니 틀렸어', turnOrigin='peer'),
        user('B', '2026-10-01T01:00:01Z', '그냥 해줘'),
        # (e) system-reminder 안의 태그는 모드가 아니다
        user('B', '2026-10-01T01:00:00Z', '<system-reminder>[mode:z]</system-reminder> 안녕'),
        asst('B', '2026-10-01T01:00:02Z', 50),
    ])
    # (c) 같은 발화가 다른 파일에 복사됨 -> 교정 1회
    write(root, 'b.jsonl', [user('A', '2026-10-01T00:00:04Z', '아니 그게 아니라 다시 해')])
    rows = [s for s in tm.collect(root).values() if s['turns'] and s['assists']]
    r = tm.by_mode(rows)
    res = subprocess.run([sys.executable, os.path.join(os.path.dirname(spec.origin), 'token-metrics.py'),
                          '--root', root, '--by-mode', '--json', os.path.join(root, 'o.json')],
                         capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert set(json.load(open(os.path.join(root, 'o.json')))['by_mode']) == set(r)

assert set(r) == {'role', 'untagged'}, r  # late 는 더 늦어 밀리고, side·z 는 안 잡힌다
assert r['role']['total_in'] == 140 and r['role']['corrections'] == 1, r
assert r['untagged']['total_in'] == 50 and r['untagged']['corrections'] == 0, r
print('ok')
