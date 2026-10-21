#!/usr/bin/env python3
"""진행.md 의 PR 한 절이 PR 을 올려도 되는 상태인지 검사한다.

사용법: check_progress.py <진행.md> <번호>      (--self-test 로 자체 검사)
명세 대조표에 빈칸·자리표시([...])가 없고, 완료 증거가 1줄 이상이면 0, 아니면 1.
"""
import re, sys


def section(text, n):
    m = re.search(rf'^## {n}\.\s.*?(?=^## \d+\.\s|\Z)', text, re.M | re.S)
    return m.group(0) if m else None


def sub(sec, name):
    m = re.search(rf'^### {name}\s*$(.*?)(?=^### |\Z)', sec, re.M | re.S)
    return m.group(1) if m else ''


def check(text, n):
    sec = section(text, n)
    if sec is None:
        return [f'"## {n}." 절 없음']
    fails = []
    rows = [l for l in sub(sec, '명세 대조').splitlines()
            if l.strip().startswith('|') and not re.match(r'^\|[\s|:-]+\|$', l.strip())][1:]  # 머리줄 제외
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
    return fails


def self_test():
    ok = ('## 1. 로그인\n### 명세 대조\n| 항목 | 위치 | 증거 |\n|---|---|---|\n'
          '| 토큰 저장 | `a.py:3` | test_store 통과 |\n### 완료 증거\n- `pytest a` → 3 passed\n')
    assert check(ok, 1) == [], check(ok, 1)
    assert check(ok.replace('test_store 통과', ''), 1)                  # 빈칸
    assert check(ok.replace('test_store 통과', '[테스트 이름]'), 1)      # 자리표시
    assert check(ok.replace('- `pytest a` → 3 passed', ''), 1)        # 증거 없음
    assert check(ok.replace('`a.py:3`', '`[파일:줄]`'), 1)             # 백틱 안 자리표시
    assert check(ok.replace('a.py:3', 'app/[id]/page.tsx:3'), 1) == []  # 경로의 [ ] 는 통과
    assert check(ok, 2) == ['"## 2." 절 없음']
    tpl = open(__file__.replace('check_progress.py', '진행-템플릿.md'), encoding='utf-8').read()
    assert len(check(tpl, 1)) == 2, check(tpl, 1)                     # 빈 템플릿은 실패
    print('self-test 통과')


if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        self_test()
        sys.exit(0)
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    fails = check(open(sys.argv[1], encoding='utf-8').read(), sys.argv[2])
    for f in fails:
        print('실패:', f)
    print('통과' if not fails else f'실패 {len(fails)}건')
    sys.exit(1 if fails else 0)
