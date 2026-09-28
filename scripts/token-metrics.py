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
    scripts/token-metrics.py --json metrics/baseline.json

출력에는 프로젝트 경로명이 기본적으로 포함되지 않는다. --by-project 로 켜면
사내 레포명이 찍히므로, 저장 결과를 공개 레포에 커밋하지 않는다(metrics/ 는
.gitignore 처리).
"""
import argparse, collections, json, os, statistics, sys

GLOBAL_AGENTS = {
    'software-architect', 'security-expert', 'backend-engineer', 'frontend-engineer',
    'database-administrator', 'code-reviewer', 'test-engineer', 'devops-engineer',
    'performance-engineer', 'data-engineer', 'ml-ai-engineer', 'codebase-explainer',
    'project-manager', 'technical-writer',
}


def blank():
    return {'turns': 0, 'main_in': 0, 'side_in': 0, 'main_out': 0, 'peak': 0,
            'assists': 0, 'agents': set(), 'proj': '', 'start': ''}


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

    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        with open(a.json, 'w') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f'\n저장: {a.json}')


if __name__ == '__main__':
    main()
