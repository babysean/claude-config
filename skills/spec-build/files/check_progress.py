#!/usr/bin/env python3
"""진행.md 의 PR 한 절이 PR 을 올려도 되는 상태인지 검사한다.

사용법: check_progress.py <진행.md> <번호>      (--self-test 로 자체 검사)
테스트 표(로직 줄은 실패·통과 둘 다, 화면·설정 줄은 통과)와 명세 대조표에 빈칸·자리표시([...])가 없고,
완료 증거가 1줄 이상이고, 로직 줄이 있으면 실패 칸에 커밋이 있고 지금 HEAD 로 `tdd.py verify` 가 통과했으면 0, 아니면 1.
"""
import re, subprocess, sys


def section(text, n):
    m = re.search(rf'^## {n}\.\s.*?(?=^## \d+\.\s|\Z)', text, re.M | re.S)
    return m.group(0) if m else None


def sub(sec, name):
    m = re.search(rf'^### {name}\s*$(.*?)(?=^### |\Z)', sec, re.M | re.S)
    return m.group(1) if m else ''


RUN = re.compile(r'^`[^`\[]+`\s*→\s*[^\s\[]')  # `명령` → 결과 (자리표시 아님)


def table(sec, name):
    return [[c.strip() for c in l.strip().strip('|').split('|')] for l in sub(sec, name).splitlines()
            if l.strip().startswith('|') and not re.match(r'^\|[\s|:-]+\|$', l.strip())][1:]  # 머리줄 제외


def check(text, n, head=None):
    sec = section(text, n)
    if sec is None:
        return [f'"## {n}." 절 없음']
    fails = []
    tests = table(sec, '테스트')
    if not tests:
        fails.append('테스트 표에 줄 없음')
    for cells in tests:
        if len(cells) < 4:
            fails.append(f'테스트 줄 칸 부족: {" | ".join(cells)}')
            continue
        case, kind, red, green = cells[:4]
        if not case or re.fullmatch(r'\[[^\]]*\]', case):
            fails.append(f'테스트 줄 이름 없음: {" | ".join(cells)}')
        if not RUN.match(green):
            fails.append(f'통과 기록 없음: {case}')
        if kind == '로직' and not (RUN.match(red) and re.search(r'\([0-9a-f]{7,40}\)\s*$', red)):
            fails.append(f'로직인데 실패 커밋 기록 없음 (tdd.py red 로 실패를 먼저 볼 것): {case}')
        elif kind not in ('로직', '화면', '설정'):
            fails.append(f'종류가 로직·화면·설정이 아님: {case}')
    rows = ['| ' + ' | '.join(r) + ' |' for r in table(sec, '명세 대조')]
    if not rows:
        fails.append('명세 대조표에 항목 없음')
    for r in rows:
        cells = [c.strip() for c in r.strip().strip('|').split('|')]
        # 칸 전체가 [자리표시] 일 때만 — `app/[id]/page.tsx` 같은 경로는 통과
        if any(not c or re.fullmatch(r'\[[^\]]*\]', c.strip('`')) for c in cells):
            fails.append(f'명세 대조 빈칸·자리표시: {r.strip()}')
    evidence = [l for l in sub(sec, '완료 증거').splitlines()
                if re.match(r'^-\s+`[^`\[]+`\s*→\s*\S', l.strip())]
    if not evidence:
        fails.append('완료 증거 없음 (형식: - `명령` → 결과)')
    if any(len(c) >= 2 and c[1] == '로직' for c in tests):
        v = re.search(r'^- `tdd\.py verify` → .*\(head ([0-9a-f]{7})\)', sub(sec, '완료 증거'), re.M)
        if not v:
            fails.append('tdd.py verify 기록 없음 — PR 전에 실행할 것')
        elif head and v.group(1) != head[:7]:
            fails.append(f'tdd.py verify 가 지금 HEAD({head[:7]}) 가 아닌 {v.group(1)} 에서 돌았음 — 다시 실행할 것')
    return fails


def self_test():
    ok = ('## 1. 로그인\n### 테스트\n| 줄 | 종류 | 실패 | 통과 |\n|---|---|---|---|\n'
          '| 만료 토큰 → 401 | 로직 | `pytest a::t` → FAILED 200 != 401 (abc1234) | `pytest a::t` → passed (def5678) |\n'
          '### 명세 대조\n| 항목 | 위치 | 증거 |\n|---|---|---|\n'
          '| 토큰 저장 | `a.py:3` | test_store 통과 |\n### 완료 증거\n- `pytest a` → 3 passed\n'
          '- `tdd.py verify` → 로직 1줄 실패→통과 확인 (head 1234567)\n')
    assert check(ok, 1, '1234567aaaa') == [], check(ok, 1, '1234567aaaa')
    assert check(ok, 1, '7654321bbbb')                                        # HEAD 바뀜 → 재검증
    assert check(ok.replace(' (abc1234)', ''), 1)                             # 실패 커밋 없음
    assert check(ok.replace('- `tdd.py verify` → 로직 1줄 실패→통과 확인 (head 1234567)\n', ''), 1)  # verify 안 함
    assert check(ok.replace('test_store 통과', ''), 1)                  # 빈칸
    assert check(ok.replace('test_store 통과', '[테스트 이름]'), 1)      # 자리표시
    assert check(ok.replace('- `pytest a` → 3 passed', ''), 1, '1234567aaaa') == []  # verify 줄도 완료 증거
    assert check(ok.replace('| 로직 |', '| 화면 |').replace('- `pytest a` → 3 passed\n', '')
                 .replace('- `tdd.py verify` → 로직 1줄 실패→통과 확인 (head 1234567)\n', ''), 1)  # 증거 없음
    assert check(ok.replace('`a.py:3`', '`[파일:줄]`'), 1)             # 백틱 안 자리표시
    assert check(ok.replace('a.py:3', 'app/[id]/page.tsx:3'), 1) == []  # 경로의 [ ] 는 통과
    assert check(ok, 2) == ['"## 2." 절 없음']
    assert check(ok.replace('`pytest a::t` → FAILED 200 != 401 (abc1234)', '-'), 1)   # 로직인데 실패 기록 없음
    assert check(ok.replace('| `pytest a::t` → passed (def5678) |', '| - |'), 1)       # 통과 기록 없음
    scr = ok.replace('| 로직 | `pytest a::t` → FAILED 200 != 401 (abc1234) |', '| 화면 | - |')
    assert check(scr.replace('- `tdd.py verify` → 로직 1줄 실패→통과 확인 (head 1234567)\n', ''), 1) == []  # 화면만이면 verify 불필요
    assert check(ok.replace('| 로직 |', '| 기타 |'), 1)                       # 종류 오타
    tpl = open(__file__.replace('check_progress.py', 'progress-template.md'), encoding='utf-8').read()
    assert len(check(tpl, 1)) >= 3, check(tpl, 1)                     # 빈 템플릿은 실패
    print('self-test 통과')


if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        self_test()
        sys.exit(0)
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    r = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True)
    if r.returncode:
        sys.exit('git 저장소 밖에서 실행됨 — 워크트리 안에서 실행할 것')
    fails = check(open(sys.argv[1], encoding='utf-8').read(), sys.argv[2], r.stdout.strip())
    for f in fails:
        print('실패:', f)
    print('통과' if not fails else f'실패 {len(fails)}건')
    sys.exit(1 if fails else 0)
