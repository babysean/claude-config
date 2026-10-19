#!/usr/bin/env python3
"""위임 정책의 컨텍스트 효율을 측정한다.

핵심 지표는 **턴당 메인 세션 입력 토큰**이다. 총 토큰이 아니다 — 위임하면
서브에이전트가 파일을 다시 읽으므로 총량은 늘어난다. 줄어드는 것은 메인
세션의 컨텍스트 성장이고, 입력 토큰의 대부분이 cache_read(매 턴 컨텍스트
재독)이므로 메인 컨텍스트가 작으면 이후 모든 턴이 싸진다.

사용법:
    scripts/token-metrics.py                     # 전체 기간
    scripts/token-metrics.py --since 2026-09-02  # 정책 변경 이후만
    scripts/token-metrics.py --band 11-30        # 턴 수를 맞춰 비교
    scripts/token-metrics.py --by-project        # 프로젝트별 (사내 경로명 출력 주의)
    scripts/token-metrics.py --by-mode           # A/B 모드별 (첫 프롬프트에 [mode:role] 처럼 태그)
    scripts/token-metrics.py --json metrics/baseline.json

출력에는 프로젝트 경로명이 기본적으로 포함되지 않는다. --by-project 로 켜면
사내 레포명이 찍히므로, 저장 결과를 공개 레포에 커밋하지 않는다(metrics/ 는
.gitignore 처리).
"""
import argparse, collections, json, os, re, statistics, sys

MODE_RE = re.compile(r'\[mode:([a-z0-9_-]+)\]')
STRIP_RE = re.compile(r'<(system-reminder|pasted_content)[^>]*>.*?(</\1>|$)', re.S)
# sessions.py 의 INJECTED_PREFIXES 복사본
INJECTED_PREFIXES = ('The following is the Codex agent history',)
MAX_MESSAGE_CHARS = 1200  # 이보다 긴 발화는 작업 지시서라 교정으로 세지 않는다
# 교정 키워드: dwe-platform/.claude/skills/morning-routine/scripts/sessions.py 의 CORRECTION_RE 복사본.
# 바꾸면 양쪽을 같이 바꾼다 (레포 간 import 금지).
# ponytail: 키워드 휴리스틱이라 말없는·암묵적 교정은 놓친다. 올릴 때는 LLM 분류로.
CORRECTION_RE = re.compile(
    r"((^|[\s.?!])아니(야|지|요|고)?[\s,.!]|그게 아니|틀렸|틀린|잘못|말고|하지\s?마|하지말|왜\s.*(했|한|하냐)|"
    r"다시\s?(해|하|봐|확인)|정정|되돌|원복|이해가 안|그렇게 하면 안|\bwrong\b|\bdon'?t\b|\bnot what\b|"
    r"\binstead\b|\bstop\b|\bundo\b|\brevert\b)",
    re.I,
)

GLOBAL_AGENTS = {
    'software-architect', 'security-expert', 'backend-engineer', 'frontend-engineer',
    'database-administrator', 'code-reviewer', 'test-engineer', 'devops-engineer',
    'performance-engineer', 'data-engineer', 'ml-ai-engineer', 'codebase-explainer',
    'project-manager', 'technical-writer',
}


def blank():
    return {'turns': 0, 'main_in': 0, 'side_in': 0, 'main_out': 0, 'peak': 0,
            'assists': 0, 'agents': set(), 'proj': '', 'start': '',
            'mode': 'untagged', 'mode_ts': '', 'corrections': 0, 'seen': set()}


def collect(root):
    """세션별로 집계한다. 같은 세션이 여러 .jsonl 에 걸쳐 있어도 합산된다."""
    sessions = collections.defaultdict(blank)
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if not fn.endswith('.jsonl'):
                continue
            proj = os.path.relpath(dirpath, root).split(os.sep)[0]
            with open(os.path.join(dirpath, fn), errors='replace') as f:
                for line in f:
                    try:
                        e = json.loads(line)
                    except ValueError:
                        continue
                    sid, ts = e.get('sessionId'), e.get('timestamp', '')
                    if not sid or not ts:
                        continue
                    s = sessions[sid]
                    s['proj'] = s['proj'] or proj
                    s['start'] = min(s['start'], ts) if s['start'] else ts
                    msg = e.get('message') or {}
                    content = msg.get('content')
                    sidechain = bool(e.get('isSidechain'))

                    # 사용자 턴은 메인 세션의 문자열 발화만 센다.
                    if (e.get('type') == 'user' and not sidechain
                            and isinstance(content, str) and content.strip()):
                        s['turns'] += 1
                        # 모드·교정은 사람이 보낸 발화만 본다 (옛 포맷은 turnOrigin 없음).
                        if e.get('turnOrigin') in (None, 'human'):
                            text = re.sub(r'\s+', ' ', STRIP_RE.sub(' ', content)).strip()
                            m = MODE_RE.search(text)
                            if m and (not s['mode_ts'] or ts < s['mode_ts']):
                                s['mode'], s['mode_ts'] = m.group(1), ts
                            # 이어받기·분기 세션이 앞 발화를 복사하므로 같은 발화는 한 번만 센다.
                            if (text and not text.startswith(('<',) + INJECTED_PREFIXES)
                                    and len(text) <= MAX_MESSAGE_CHARS
                                    and text not in s['seen'] and CORRECTION_RE.search(text)):
                                s['corrections'] += 1
                            s['seen'].add(text)

                    usage = msg.get('usage')
                    if usage:
                        total_in = sum(usage.get(k) or 0 for k in (
                            'input_tokens', 'cache_read_input_tokens',
                            'cache_creation_input_tokens'))
                        if sidechain:
                            s['side_in'] += total_in
                        else:
                            s['main_in'] += total_in
                            s['main_out'] += usage.get('output_tokens') or 0
                            s['assists'] += 1
                            s['peak'] = max(s['peak'], total_in)

                    # 서브에이전트 호출은 메인 세션이 낸 것만 센다.
                    if isinstance(content, list) and not sidechain:
                        for b in content:
                            if (isinstance(b, dict) and b.get('type') == 'tool_use'
                                    and (b.get('input') or {}).get('subagent_type')):
                                s['agents'].add(b['input']['subagent_type'])
    return sessions


def summarize(sel):
    turns = sum(s['turns'] for s in sel)
    if not sel or not turns:
        return None
    return {
        'sessions': len(sel),
        'turns': turns,
        'main_in_per_turn': sum(s['main_in'] for s in sel) // turns,
        'peak_median': int(statistics.median(s['peak'] for s in sel)),
        'side_in_per_session': sum(s['side_in'] for s in sel) // len(sel),
        'side_share_pct': round(
            sum(s['side_in'] for s in sel) * 100
            / max(1, sum(s['main_in'] + s['side_in'] for s in sel)), 1),
    }


def by_mode(sel):
    out = {}
    for m in sorted({s['mode'] for s in sel}):
        g = [s for s in sel if s['mode'] == m]
        turns = sum(s['turns'] for s in g)
        main_in, side_in = sum(s['main_in'] for s in g), sum(s['side_in'] for s in g)
        corr = sum(s['corrections'] for s in g)
        out[m] = {
            'sessions': len(g), 'turns': turns, 'total_in': main_in + side_in,
            'total_in_per_turn': (main_in + side_in) // turns,
            'main_in_per_turn': main_in // turns,
            'side_share_pct': round(side_in * 100 / max(1, main_in + side_in), 1),
            'corrections': corr, 'corrections_per_turn': round(corr / turns, 3),
        }
    return out


def fmt(label, d):
    if not d:
        return f'{label:12} (표본 없음)'
    return (f"{label:12} n={d['sessions']:4d} 턴={d['turns']:5d}  "
            f"턴당 메인입력 {d['main_in_per_turn']:>11,}  "
            f"피크(중앙) {d['peak_median']:>9,}  "
            f"서브체인 비중 {d['side_share_pct']:>5.1f}%")


def main():
    ap = argparse.ArgumentParser(description='위임 정책의 컨텍스트 효율 측정')
    ap.add_argument('--root', default=os.path.expanduser('~/.claude/projects'))
    ap.add_argument('--since', help='YYYY-MM-DD 이후 시작된 세션만')
    ap.add_argument('--until', help='YYYY-MM-DD 이전 시작된 세션만')
    ap.add_argument('--band', help='사용자 턴 수 범위로 표본을 맞춘다 (예: 11-30)')
    ap.add_argument('--by-project', action='store_true',
                    help='프로젝트별로 분해 (사내 레포명이 출력된다)')
    ap.add_argument('--by-mode', action='store_true',
                    help='[mode:xxx] 태그별로 분해 (태그 없으면 untagged)')
    ap.add_argument('--json', metavar='PATH', help='결과를 JSON 으로 저장')
    a = ap.parse_args()

    if not os.path.isdir(a.root):
        sys.exit(f'트랜스크립트 디렉터리가 없다: {a.root}')

    sessions = collect(a.root)
    rows = [s for s in sessions.values() if s['turns'] > 0 and s['assists'] > 0]
    if a.since:
        rows = [s for s in rows if s['start'][:10] >= a.since]
    if a.until:
        rows = [s for s in rows if s['start'][:10] <= a.until]
    if a.band:
        lo, hi = (int(x) for x in a.band.split('-'))
        rows = [s for s in rows if lo <= s['turns'] <= hi]
    if not rows:
        sys.exit('조건에 맞는 세션이 없다.')

    span = (min(s['start'][:10] for s in rows), max(s['start'][:10] for s in rows))
    delegated = [s for s in rows if s['agents'] & GLOBAL_AGENTS]
    zeroshot = [s for s in rows if not (s['agents'] & GLOBAL_AGENTS)]

    out = {
        'span': span, 'filters': {'since': a.since, 'until': a.until, 'band': a.band},
        'all': summarize(rows), 'delegated': summarize(delegated),
        'zeroshot': summarize(zeroshot),
    }

    print(f'기간 {span[0]} ~ {span[1]}   세션 {len(rows)}')
    if a.band:
        print(f'턴 수 밴드: {a.band}')
    print()
    print(fmt('전체', out['all']))
    print(fmt('위임', out['delegated']))
    print(fmt('제로샷', out['zeroshot']))

    d, z = out['delegated'], out['zeroshot']
    if d and z:
        diff = (d['main_in_per_turn'] - z['main_in_per_turn']) / z['main_in_per_turn'] * 100
        print(f'\n턴당 메인 입력: 위임이 제로샷 대비 {diff:+.1f}%')
        if min(d['sessions'], z['sessions']) < 20:
            print('  ⚠ 한쪽 표본이 20세션 미만이다. 방향만 참고하고 단정하지 않는다.')
        print('  ⚠ 무작위 배정이 아니다. 상관이며 인과가 아니다.')
        out['delta_pct'] = round(diff, 1)

    if a.by_project:
        print('\n프로젝트별 (턴당 메인 입력)')
        byp = collections.defaultdict(list)
        for s in rows:
            byp[s['proj']].append(s)
        per = {}
        for p, sel in sorted(byp.items(), key=lambda kv: -len(kv[1])):
            r = summarize(sel)
            per[p] = r
            print(f"  {p[:46]:46} n={r['sessions']:4d}  {r['main_in_per_turn']:>11,}")
        out['by_project'] = per

    if a.by_mode:
        print('\n모드별')
        out['by_mode'] = by_mode(rows)
        for m, r in out['by_mode'].items():
            print(f"  {m:12} n={r['sessions']:4d} 턴={r['turns']:5d}  "
                  f"총입력 {r['total_in']:>14,}  턴당총입력 {r['total_in_per_turn']:>11,}  "
                  f"턴당메인입력 {r['main_in_per_turn']:>11,}  서브체인 비중 {r['side_share_pct']:>5.1f}%  "
                  f"교정 {r['corrections']:4d} (턴당 {r['corrections_per_turn']:.3f})")

    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        with open(a.json, 'w') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f'\n저장: {a.json}')


if __name__ == '__main__':
    main()
