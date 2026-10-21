#!/usr/bin/env python3
"""명세서 폴더가 design-doc 완료 기준 1~6 을 지키는지 검사한다.

사용법: check.py <.requirements/주제 폴더>
통과하면 0, 하나라도 실패하면 1 로 끝난다. 항목마다 한 줄씩 통과/실패를 출력한다.
"""
import pathlib, re, sys

MAX_CHARS = 4000  # 5분 읽기. ponytail: 글자 수 근사, 실제 이해 시간은 사람이 판단
CODE_NAME = re.compile(r'(?<![#\w/.-])(?:[A-Z]{1,2}-?\d{1,2}(?:-[a-z])?)(?![\w.-])')
REVISION = re.compile(r'\d+\s*차\s*(반영|개정|수정)|반영 이력|변경 이력|TBD|미정')
FLOW = ('현재 흐름', '고칠 곳', '바뀐 흐름')


def body(text):
    return re.sub(r'```.*?```', '', text, flags=re.S)


def headings(text):
    return [h.strip() for h in re.findall(r'^#{2,3}\s+(.+)$', body(text), re.M)]


def check(folder):
    fails = []
    mds = sorted(m for m in folder.glob('*.md') if m.name != '진행.md')  # implement-plan 장부, 명세 아님
    if not mds:
        return [f'{folder}: md 파일 없음']
    for md in mds:
        t = md.read_text()
        b = body(t)
        n = len(re.sub(r'\s', '', b))
        if n > MAX_CHARS:
            fails.append(f'{md.name}: 본문 {n}자 > {MAX_CHARS}자 (쪼갤 것)')
        hs = headings(t)
        if not hs or not hs[0].startswith('용어'):
            fails.append(f'{md.name}: 첫 절이 "용어" 가 아님')
        if md.name != '구현계획.md':
            for f in FLOW:
                if not any(h.startswith(f) for h in hs):
                    fails.append(f'{md.name}: "{f}" 절 없음')
        codes = sorted(set(CODE_NAME.findall(b)))
        if codes:
            fails.append(f'{md.name}: 내부 코드명 {", ".join(codes)} → 우리말 이름으로')
        rev = sorted(set(m.group(0) for m in REVISION.finditer(b)))
        if rev:
            fails.append(f'{md.name}: 개정 이력·미결 표시 {", ".join(rev)}')
        if not md.with_suffix('.html').exists():
            fails.append(f'{md.name}: 짝 html 없음')
    return fails


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    folder = pathlib.Path(sys.argv[1])
    fails = check(folder)
    for f in fails:
        print('실패', f)
    print('통과' if not fails else f'실패 {len(fails)}건')
    sys.exit(1 if fails else 0)
