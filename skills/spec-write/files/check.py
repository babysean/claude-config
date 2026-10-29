#!/usr/bin/env python3
"""명세서 폴더가 spec-write 완료 기준 1~8 을 지키는지 검사한다.

사용법: check.py <.requirements/주제 폴더>      (--self-test 로 자체 검사)
통과하면 0, 하나라도 실패하면 1 로 끝난다. 항목마다 한 줄씩 통과/실패를 출력한다.
"""
import pathlib, re, sys

MAX_CHARS = 4000  # 5분 읽기. ponytail: 글자 수 근사, 실제 이해 시간은 사람이 판단
CODE_NAME = re.compile(r'(?<![#\w/.-])(?:[A-Z]{1,2}-?\d{1,2}(?:-[a-z])?)(?![\w.-])')
REVISION = re.compile(r'\d+\s*차\s*(반영|개정|수정)|반영 이력|변경 이력|TBD|미정')
FORMS = {'변경형': ('현재 흐름', '고칠 곳', '바뀐 흐름'), '신규형': ('목적', '만들 것', '기존과 붙는 곳')}
PLACEHOLDER = re.compile(r'^\[[^\]]*\]$')  # 칸 전체가 [자리표시]
FLOW_MAX = 7
JUDGES = ('사람', '코드', 'LLM', '외부')


def body(text):
    return re.sub(r'```.*?```', '', text, flags=re.S)


def headings(text):
    return [h.strip() for h in re.findall(r'^#{2,3}\s+(.+)$', body(text), re.M)]


def section(text, name, level='##'):
    m = re.search(rf'^{level} {name}[^\n]*$(.*?)(?=^#{{2,{len(level)}}} |\Z)', body(text), re.M | re.S)
    return m.group(1) if m else None


def table(sec):
    rows = [l.strip() for l in sec.splitlines() if l.strip().startswith('|')]
    head = [c.strip() for c in rows[0].strip('|').split('|')] if rows else []
    return head, [r for r in rows[1:] if not re.match(r'^\|[\s|:-]+\|$', r)]  # 머리줄·구분줄 제외


def flow_fails(name, text):
    sec = section(text, '핵심 흐름')
    if sec is None:
        return [f'{name}: "핵심 흐름" 절 없음 (대표 상황 하나를 처음부터 끝까지, 대화로 확인받은 흐름)']
    head, rows = table(sec)
    if '판단' not in head:
        return [f'{name}: 핵심 흐름 표에 "판단" 칸 없음']
    if not 1 <= len(rows) <= FLOW_MAX:
        return [f'{name}: 핵심 흐름 {len(rows)}단계 (1~{FLOW_MAX}단계로 묶을 것)']
    fails = []
    for r in rows:
        cells = [c.strip() for c in r.strip('|').split('|')]
        if len(cells) < len(head) or any(not c or re.search(r'\[[^\]]*\]', c) for c in cells):
            fails.append(f'{name}: 핵심 흐름 줄에 빈칸·자리표시: {r}')
        elif not cells[head.index('판단')].startswith(JUDGES):
            fails.append(f'{name}: 핵심 흐름 판단 칸이 {"·".join(JUDGES)} 중 하나로 시작하지 않음: {r}')
    return fails


def test_list_fails(name, text):
    sec = section(text, '테스트 목록')
    if sec is None:
        return [f'{name}: "테스트 목록" 절 없음']
    rows = table(sec)[1]
    if not rows:
        return [f'{name}: 테스트 목록에 줄 없음']
    fails = []
    for r in rows:
        cells = [c.strip() for c in r.strip('|').split('|')]
        if len(cells) < 3 or any(not c or PLACEHOLDER.match(c) for c in cells) or '→' not in cells[2] \
                or re.search(r'\[[^\]]*\]\s*→|→\s*\[[^\]]*\]', cells[2]):
            fails.append(f'{name}: 테스트 목록 줄이 "조건 → 기대 결과" 가 아님: {r}')
    return fails


def form_fails(name, hs):
    has = {k: [s for s in v if any(h.startswith(s) for h in hs)] for k, v in FORMS.items()}
    if has['변경형'] and has['신규형']:
        return [f'{name}: 두 틀의 절이 섞임 ({", ".join(has["변경형"] + has["신규형"])}) → 틀 하나로, 다른 쪽은 파일을 쪼갤 것']
    form = '신규형' if has['신규형'] else '변경형'  # 아무 절도 없으면 기존 기본값 변경형으로 안내
    return [f'{name}: {form} "{s}" 절 없음' for s in FORMS[form] if s not in has[form]]


def plan_fails(text):
    fails = []
    for m in re.finditer(r'^## (\d+)\.\s[^\n]*$(.*?)(?=^## |\Z)', body(text), re.M | re.S):
        # 한 줄 형식(`- 테스트: a / b`)과 아래 목록 형식 둘 다 받는다
        t = re.search(r'^- 테스트[^:\n]*:[ \t]*([^\n]*)\n?((?:[ \t]+- [^\n]*\n?)*)', m.group(2), re.M)
        items = [] if not t else [i.strip() for i in [t.group(1)] + re.findall(r'- (.+)', t.group(2))]
        items = [i for i in items if i and not re.match(r'^[\[(]', i)]  # 자리표시·안내 괄호 제외
        if not items:
            fails.append(f'구현계획.md: {m.group(1)}번 PR 에 테스트 줄 없음')
    return fails


def check(folder):
    fails = []
    mds = sorted(m for m in folder.glob('*.md') if m.name != '진행.md')  # spec-build 장부, 명세 아님
    if not mds:
        return [f'{folder}: md 파일 없음']
    specs = [m for m in mds if m.name != '구현계획.md']
    if specs:  # 쪼갠 경우 00-개요 에만 둔다
        fails += flow_fails(specs[0].name, specs[0].read_text())
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
            fails += form_fails(md.name, hs)
            fails += test_list_fails(md.name, t)
        else:
            fails += plan_fails(t)
        codes = sorted(set(CODE_NAME.findall(b)))
        if codes:
            fails.append(f'{md.name}: 내부 코드명 {", ".join(codes)} → 우리말 이름으로')
        rev = sorted(set(m.group(0) for m in REVISION.finditer(b)))
        if rev:
            fails.append(f'{md.name}: 개정 이력·미결 표시 {", ".join(rev)}')
    return fails


def self_test():
    spec = ('## 용어\n## 현재 흐름\n## 고칠 곳\n## 바뀐 흐름\n## 테스트 목록\n\n'
            '| 항목 | 종류 | 조건 → 기대 결과 |\n|---|---|---|\n| 로그인 | 로직 | 만료 토큰 → 401 |\n')
    assert test_list_fails('a', spec) == []
    assert test_list_fails('a', spec.replace('## 테스트 목록', '## 확인 방법'))            # 절 없음
    assert test_list_fails('a', spec.replace('| 로그인 | 로직 | 만료 토큰 → 401 |\n', ''))  # 줄 없음
    assert test_list_fails('a', spec.replace('만료 토큰 → 401', '잘 된다'))                # 화살표 없음
    assert test_list_fails('a', spec.replace('만료 토큰 → 401', '[조건] → [기대 결과]'))   # 자리표시
    assert test_list_fails('a', spec.replace('로직', ''))                                # 빈칸
    flow = ('## 핵심 흐름\n\n| 단계 | 누가 | 들어가는 것 → 나오는 것 | 판단 | 실패하면 |\n|---|---|---|---|---|\n'
            '| 1 | 사용자 | 질문 → 요청 | 사람 — 질문 고름 | 없음 |\n'
            '| 2 | LLM | 질문 → 도구 이름 | LLM — 부를 도구 고름 | 답 없음 표시 |\n')
    assert flow_fails('a', flow) == []
    assert flow_fails('a', '## 용어\n')                                                  # 절 없음
    assert flow_fails('a', flow.replace('LLM — 부를', '아무개 — 부를'))                   # 판단 값 틀림
    assert flow_fails('a', flow.replace('답 없음 표시', ''))                              # 빈칸
    assert flow_fails('a', flow.replace('| 판단 |', '| 결정 |'))                          # 판단 칸 없음
    assert flow_fails('a', flow + '| 3 | 서버 | a → b | 코드 — c | d |\n' * 6)           # 8단계
    for f in ('변경', '신규'):
        tpl = pathlib.Path(__file__).with_name(f'명세-템플릿-{f}.md').read_text()
        assert form_fails(f, headings(tpl)) == [], f'{f}형 템플릿 절이 검사와 어긋남'
        assert headings(tpl)[:2] == ['용어', '핵심 흐름'], f'{f}형 템플릿 절 순서'
        assert test_list_fails(f, tpl), f'빈 {f}형 템플릿은 실패해야 함'
        assert flow_fails(f, tpl), f'빈 {f}형 템플릿 핵심 흐름은 실패해야 함'
    change, new = ['용어', '현재 흐름', '고칠 곳', '바뀐 흐름'], ['용어', '목적과 쓰는 사람', '만들 것', '기존과 붙는 곳']
    assert form_fails('a', change) == [] and form_fails('a', new) == []
    assert form_fails('a', [h for h in new if h != '만들 것']) == ['a: 신규형 "만들 것" 절 없음']
    assert form_fails('a', [h for h in change if h != '고칠 곳']) == ['a: 변경형 "고칠 곳" 절 없음']
    assert form_fails('a', change + ['만들 것'])                                          # 섞임
    assert len(form_fails('a', ['용어'])) == 3                                            # 아무 틀도 없음
    plan = '## 용어\n## 1. 뼈대\n- 범위: a\n- 테스트:\n  - 01.md 만료 토큰 → 401 — test_expired\n- 커밋 마일스톤:\n'
    assert plan_fails(plan) == []
    assert plan_fails(plan.replace('  - 01.md 만료 토큰 → 401 — test_expired\n', ''))
    assert plan_fails('## 1. 뼈대\n- 테스트: 만료 토큰 401 / 쿠키 HttpOnly\n- 커밋: ①\n') == []   # 한 줄 형식
    assert plan_fails('## 1. 뼈대\n- 테스트(가짜 응답): 403 확인\n') == []                       # 괄호 붙은 이름
    assert plan_fails(pathlib.Path(__file__).with_name('구현계획-템플릿.md').read_text()), '빈 계획 템플릿은 실패해야 함'
    print('self-test 통과')


if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        self_test()
        sys.exit(0)
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    folder = pathlib.Path(sys.argv[1])
    fails = check(folder)
    for f in fails:
        print('실패', f)
    print('통과' if not fails else f'실패 {len(fails)}건')
    sys.exit(1 if fails else 0)
