#!/usr/bin/env python3
"""TDD 한 줄을 한 번의 호출로: 실행 → 판정 → 커밋 → 진행.md 기록. 마지막에 실패 커밋을 다시 돌려 검증한다.

사용법 (워크트리 안, 테스트를 돌릴 폴더에서):
  tdd.py red    <진행.md> <N> "<테스트 줄>" --files <경로...> -- <테스트 명령...>
  tdd.py green  <진행.md> <N> "<테스트 줄>" --files <경로...> -m "<커밋 제목>" -- <테스트 명령...>
  tdd.py verify <진행.md> <N>
  tdd.py --self-test

red    명령이 '기대한 이유로' 실패해야 커밋한다(import·이름 없음·문법 오류·테스트 0개는 거부).
       커밋 본문에 명령과 폴더를 남겨 verify 가 다시 돌린다.
green  명령이 통과해야 커밋한다.
verify 로직 줄마다 실패 커밋으로 옮겨 다시 실패하는지, HEAD 에서 통과하는지 확인하고 완료 증거 한 줄을 쓴다.
훅은 우회하지 않는다. 긴 출력은 <git-dir>/tdd-logs/ 에 둔다.
"""
import os, re, subprocess, sys, tempfile, pathlib

TRAILER = 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'
BAD_RED = re.compile(r'ImportError|ModuleNotFoundError|No module named|NameError|SyntaxError|IndentationError|'
                     r"Cannot find module|is not defined|module '[\w.]+' has no attribute|"
                     r'error collecting|no tests ran|collected 0 items|'
                     r'No test files found|ERROR at (?:setup|teardown)|\d+ errors? in \d|^ERROR |'
                     r'ConnectionRefused|OperationalError|could not connect', re.I | re.M)
REASON = re.compile(r'(AssertionError.*|assert .*|FAILED .*|Expected.*|expected.*|✗.*|× .*)')


def git(*a, cwd=None, check=True):
    r = subprocess.run(['git', *a], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f'git {" ".join(a)} 실패: {r.stderr.strip()}')
    return r.stdout.strip()


def run(cmd, cwd, tag):
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    out = r.stdout + r.stderr
    logs = pathlib.Path(git('rev-parse', '--absolute-git-dir', cwd=cwd)) / 'tdd-logs'
    logs.mkdir(exist_ok=True)
    (logs / f'{tag}.log').write_text(out)
    return r.returncode, out


def reason(out):
    m = re.findall(r'^E\s+(.+)$', out, re.M) or REASON.findall(out)  # pytest 의 E 줄(단언 내용)을 먼저
    return re.sub(r'\s+', ' ', m[0]).replace('|', '/')[:80] if m else ''


def red_ok(code, out):
    # pytest 종료 코드 5 = 고른 테스트 없음 (-k 가 아무것도 못 고름). 출력에 'no tests ran' 이 없을 수 있다
    return code not in (0, 5) and not BAD_RED.search(out)


def set_cell(path, n, case, col, value):
    """진행.md 의 N번 절 테스트 표에서 case 줄의 col(2=실패, 3=통과) 칸을 바꾼다."""
    p = pathlib.Path(path)
    lines = p.read_text(encoding='utf-8').split('\n')
    sec = in_tests = False
    for i, l in enumerate(lines):
        if re.match(r'^## \d+\.\s', l):
            sec = l.startswith(f'## {n}.')
        elif sec and l.startswith('### '):
            in_tests = l.strip() == '### 테스트'
        elif sec and in_tests and l.strip().startswith('|'):
            cells = [c.strip() for c in l.strip().strip('|').split('|')]
            if cells and cells[0] == case and len(cells) >= 4:
                cells[col] = value.replace('|', '¦')  # 명령 속 | 가 표 칸을 깨지 않게
                lines[i] = '| ' + ' | '.join(cells) + ' |'
                p.write_text('\n'.join(lines), encoding='utf-8')
                return
    sys.exit(f'진행.md {n}번 테스트 표에 "{case}" 줄이 없음 — 먼저 표에 옮길 것')


def rows(path, n):
    text = pathlib.Path(path).read_text(encoding='utf-8')
    m = re.search(rf'^## {n}\.\s.*?(?=^## \d+\.\s|\Z)', text, re.M | re.S)
    t = re.search(r'^### 테스트\s*$(.*?)(?=^### |\Z)', m.group(0) if m else '', re.M | re.S)
    out = []
    for l in (t.group(1) if t else '').splitlines():
        if l.strip().startswith('|') and not re.match(r'^\|[\s|:-]+\|$', l.strip()):
            out.append([c.strip() for c in l.strip().strip('|').split('|')])
    return out[1:]


def commit(files, msg, body, cwd):
    git('add', '--', *files, cwd=cwd)
    git('commit', '-q', '-m', msg, '-m', body, '-m', TRAILER, cwd=cwd)
    return git('rev-parse', '--short=7', 'HEAD', cwd=cwd)


def step(kind, path, n, case, files, msg, cmd):
    cwd = os.getcwd()
    rel = os.path.relpath(cwd, git('rev-parse', '--show-toplevel'))
    code, out = run(cmd, cwd, f'{n}-{kind}')
    if kind == 'red':
        if not red_ok(code, out):
            bad = BAD_RED.search(out)
            why = '통과함 — 테스트가 틀렸다' if code == 0 else f'기대한 이유가 아님: {bad.group(0) if bad else ""}'
            sys.exit(f'실패로 치지 않음 ({why}). 빈 껍데기를 만들어 단언에서 실패하게 할 것')
        sha = commit(files, f'test: {case} 실패 테스트', f'- tdd-cmd: {cmd}\n- tdd-cwd: {rel}', cwd)
        set_cell(path, n, case, 2, f'`{cmd}` → FAILED {reason(out) or f"exit {code}"} ({sha})')
        print(f'실패 확인·커밋 {sha}: {reason(out)}')
    else:
        if code:
            sys.exit(f'통과 안 함 (exit {code}): {reason(out)} — 로그 tdd-logs/{n}-green.log')
        sha = commit(files, msg, f'- {case} 통과', cwd)
        set_cell(path, n, case, 3, f'`{cmd}` → passed ({sha})')
        print(f'통과 확인·커밋 {sha}')


def verify(path, n):
    top = git('rev-parse', '--show-toplevel')
    if git('status', '--porcelain', '--untracked-files=no', cwd=top):
        sys.exit('추적 중인 파일에 커밋 안 된 변경이 있음 — 커밋 뒤 다시')
    branch, head = git('branch', '--show-current', cwd=top), git('rev-parse', 'HEAD', cwd=top)
    if not branch:
        sys.exit('브랜치 위에서 실행할 것 (detached 상태)')
    fails, checked, mutated = [], [], []
    for cells in rows(path, n):
        if len(cells) < 4 or cells[1] != '로직':
            continue
        if cells[2].startswith('변이:'):  # 앞 줄 구현으로 이미 충족 — 실패 커밋 대신 변이 확인, HEAD 통과만 다시 본다
            cmd = re.search(r'`([^`]+)`', cells[3])
            if not cmd:
                fails.append(f'{cells[0]}: 변이 줄인데 통과 칸에 명령 없음')
            else:
                mutated.append((cells[0], cmd.group(1)))
            continue
        m = re.search(r'\(([0-9a-f]{7,40})\)\s*$', cells[2])
        if not m:
            fails.append(f'{cells[0]}: 실패 칸에 커밋 없음 (tdd.py red 로 기록할 것)')
            continue
        sha = m.group(1)
        if subprocess.run(['git', 'merge-base', '--is-ancestor', sha, 'HEAD'], cwd=top).returncode:
            fails.append(f'{cells[0]}: 실패 커밋 {sha} 가 이 브랜치에 없음')
            continue
        body = git('log', '-1', '--format=%B', sha, cwd=top)
        cmd = re.search(r'^- tdd-cmd: (.+)$', body, re.M)
        rel = re.search(r'^- tdd-cwd: (.+)$', body, re.M)
        if not (cmd and rel):
            fails.append(f'{cells[0]}: {sha} 본문에 tdd-cmd·tdd-cwd 없음')
            continue
        checked.append((cells[0], sha, cmd.group(1), os.path.join(top, rel.group(1))))
    try:
        for case, sha, cmd, cwd in checked:
            git('switch', '-q', '--detach', sha, cwd=top)
            code, out = run(cmd, cwd, f'{n}-verify-red-{sha}')
            if not red_ok(code, out):
                fails.append(f'{case}: {sha} 에서 기대한 이유로 실패하지 않음 (exit {code})')
    finally:
        git('switch', '-q', branch, cwd=top)
    for case, sha, cmd, cwd in checked:
        code, out = run(cmd, cwd, f'{n}-verify-green')
        if code:
            fails.append(f'{case}: HEAD 에서 통과하지 않음 (exit {code})')
    for case, cmd in mutated:
        code, out = run(cmd, os.getcwd(), f'{n}-verify-mutated')
        if code:
            fails.append(f'{case}: HEAD 에서 통과하지 않음 (exit {code})')
    for f in fails:
        print('실패:', f)
    if fails or not checked:
        sys.exit('검증 실패' if fails else '검증할 로직 줄 없음')
    text = pathlib.Path(path).read_text(encoding='utf-8')
    extra = f', 변이 확인 {len(mutated)}줄 HEAD 통과' if mutated else ''
    line = f'- `tdd.py verify` → 로직 {len(checked)}줄 실패→통과 확인{extra} (head {head[:7]})'
    text = re.sub(r'^- `tdd\.py verify` → .*$\n?', '', text, flags=re.M)  # 이전 검증 줄 교체
    m = re.search(rf'(^## {n}\.\s.*?^### 완료 증거\s*\n)', text, re.M | re.S)
    if not m:
        sys.exit(f'진행.md {n}번 절에 "### 완료 증거" 없음')
    pathlib.Path(path).write_text(text[:m.end()] + line + '\n' + text[m.end():], encoding='utf-8')
    print(f'검증 통과: 로직 {len(checked)}줄 (head {head[:7]})')


def self_test():
    # 실제 pytest 출력 모양 (2026-10-21 Janus poetry 환경에서 확인)
    assert red_ok(1, 'E       assert 0 == 2\n1 failed in 0.01s') and reason('E       assert 0 == 2') == 'assert 0 == 2'
    assert not red_ok(1, 'ERROR t.py::test_db - ConnectionRefusedError: devdb down\n1 error in 0.01s')  # fixture 오류
    assert not red_ok(2, "E   ModuleNotFoundError: No module named 'nope'")                          # 이름 없음
    assert not red_ok(5, '7 deselected, 24 warnings in 1.22s')                                      # -k 가 0개 고름
    assert not red_ok(1, "E   AttributeError: module 'app.orchestrator' has no attribute 'status'")  # 이름 없음
    assert red_ok(1, "E   AttributeError: 'NoneType' object has no attribute 'user_email'\n1 failed")  # 동작 실패
    assert not red_ok(1, '.venv/bin/python: No module named pytest')                              # venv 없음
    with tempfile.TemporaryDirectory() as d:
        sh = lambda *a: subprocess.run(a, cwd=d, check=True, capture_output=True)
        sh('git', 'init', '-q', '-b', 'feature/t')
        sh('git', 'config', 'user.email', 't@t'); sh('git', 'config', 'user.name', 't')
        pathlib.Path(d, 'README').write_text('x'); sh('git', 'add', '.'); sh('git', 'commit', '-qm', 'init')
        prog = pathlib.Path(d, '진행.md')
        prog.write_text('## 1. 덧셈\n### 테스트\n| 줄 | 종류 | 실패 | 통과 |\n|---|---|---|---|\n'
                        '| 1+1 → 2 | 로직 | - | - |\n### 완료 증거\n')
        os.chdir(d)
        exe = [sys.executable, __file__]
        cmd = f'{sys.executable} t.py'
        bad = lambda *a: subprocess.run(exe + list(a), capture_output=True, text=True).returncode != 0
        pathlib.Path(d, 't.py').write_text('from add import add\nassert add(1, 1) == 2, "1+1 != 2"\n')
        assert bad('red', str(prog), '1', '1+1 → 2', '--files', 't.py', '--', cmd)        # 이름 없음은 거부
        pathlib.Path(d, 'add.py').write_text('def add(a, b):\n    return 0\n')                # 빈 껍데기
        assert not bad('red', str(prog), '1', '1+1 → 2', '--files', 't.py', 'add.py', '--', cmd)
        assert 'FAILED' in prog.read_text()
        pathlib.Path(d, 'add.py').write_text('def add(a, b):\n    return a + b\n')
        assert not bad('green', str(prog), '1', '1+1 → 2', '--files', 'add.py', '-m', 'feat: 덧셈', '--', cmd)
        assert not bad('verify', str(prog), '1')
        assert 'tdd.py verify` → 로직 1줄' in prog.read_text()
        assert bad('red', str(prog), '1', '없는 줄', '--files', 't.py', '--', cmd)            # 표에 없는 줄
        pathlib.Path(d, 'add.py').write_text('def add(a, b):\n    return 0\n')
        assert bad('green', str(prog), '1', '1+1 → 2', '--files', 'add.py', '-m', 'x', '--', cmd)  # 통과 안 함
        assert bad('verify', str(prog), '1')                                                  # 커밋 안 된 변경
        sh('git', 'checkout', '--', 'add.py')
        assert subprocess.run(['git', 'branch', '--show-current'], cwd=d, capture_output=True,
                              text=True).stdout.strip() == 'feature/t'                       # 브랜치 복귀
    print('self-test 통과')


def main(a):
    if a == ['--self-test']:
        return self_test()
    if len(a) >= 3 and a[0] == 'verify':
        return verify(a[1], a[2])
    if len(a) < 4 or a[0] not in ('red', 'green') or '--' not in a or '--files' not in a:
        sys.exit(__doc__)
    kind, path, n, case = a[:4]
    opts, cmd = a[4:a.index('--')], ' '.join(a[a.index('--') + 1:])
    files = opts[opts.index('--files') + 1:]
    msg = None
    if '-m' in files:
        msg = files[files.index('-m') + 1]
        files = files[:files.index('-m')]
    elif '-m' in opts:
        msg = opts[opts.index('-m') + 1]
        files = [f for f in files if f not in ('-m', msg)]
    if kind == 'green' and not msg:
        sys.exit('green 은 -m "<type>: <제목>" 이 필요함')
    if not files or not cmd:
        sys.exit(__doc__)
    step(kind, path, n, case, files, msg, cmd)


if __name__ == '__main__':
    main(sys.argv[1:])
