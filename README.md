# claude-config

Claude Code 개인 설정. 여러 PC 에서 같은 전역 작업 규칙을 쓰기 위한 저장소.

## 구성

| 경로 | 설치 위치 | 역할 |
|---|---|---|
| `CLAUDE.md` | `~/.claude/CLAUDE.md` | 전역 작업 규칙 — 범용 + 매뉴얼 방식, 증명, 매뉴얼 고치기 루프, 웹 검색 출처 검증, 버그 대응 순서 |
| `skills/<job>/` | `~/.claude/skills/<job>/` | 개인 매뉴얼. `spec-write` — 구현 전 명세서 작성·확정 (SDD) · `spec-build` — 구현계획 PR 하나 구현~머지 |
| `install.sh` | — | 설치 스크립트 (symlink / 복사). [1/2] CLAUDE.md·skills, [2/2] 도구 설치 |
| `scripts/token-metrics.py` | — | 작업 방식별 토큰·교정 측정 |
| ponytail@ponytail | Claude Code 플러그인 | 최소 구현 강제 (SessionStart/SubagentStart/UserPromptSubmit hook) |
| context7 | Claude Code 플러그인 | 라이브러리 최신 문서 조회 MCP |
| typescript-lsp, pyright-lsp | Claude Code 플러그인 | TS/Python LSP. 서버 바이너리는 `npm install -g` |
| graphifyy (PyPI) | CLI: PATH | 코드 지식 그래프, `uv tool install graphifyy` |

## 전역 규칙 (`CLAUDE.md`)

메인 세션이 **직접** 일하고, 업무 지식은 에이전트가 아니라 **매뉴얼**(레포의
스킬·커맨드·규칙 파일)에 둔다.

| 절 | 내용 |
|---|---|
| §1 | 일하는 순서 — 매뉴얼 찾기 → 직접 처리 → 증명 → 매뉴얼 고치기. 서브에이전트는 넓은 탐색·병렬·웹 읽기·레포 절차일 때만 |
| §2 | 매뉴얼 — 일 하나에 폴더 하나 (`SKILL.md` · `files/` · `examples/` · `notes.md`) |
| §3 | 증명 — 실패할 수 있는 검사를 증거와 함께 통과해야 완료 |
| §4 | 루프 — 교정은 채팅이 아니라 매뉴얼에 반영. 프로세스·툴박스·증명 중 어느 층인지 진단 |
| §5 | 프로젝트 전용 에이전트 (`<repo>/.claude/agents/`) 위치 |
| §6 | 웹 검색 결과를 쓸 때 — 날짜 확인, 신뢰 순서, 버전 명시 |
| §7 | 버그를 만났을 때 — 재현 → 가설 검증 → 근본 원인 → 회귀 테스트 |
| §8 | Graphify 사용 |

## 정책 이력

| 기간 | 방식 |
|---|---|
| ~ 2026-08-31 | 국소 수정은 직접, 나머지는 위임 |
| 2026-09-01 ~ 10-19 | **역할 위임** — 파일 수정은 전부 역할별 전문 에이전트 15종에 위임 |
| 2026-10-20 ~ | **범용 + 매뉴얼** — 역할 에이전트 폐기, 메인 세션이 매뉴얼을 따라 직접 처리 |

전환 근거: 역할 에이전트는 원칙만 담은 범용 프롬프트였고, 실제 업무 지식(절차·함정·완료 기준)은
레포의 커맨드·규칙에 있었다. 일 단위 매뉴얼에 지식을 모으고 교정을 그 매뉴얼에 되먹이는 쪽이
쓸수록 나아진다는 판단이다. 역할 에이전트 정의는 git 이력(`agents/`, 2026-10-20 삭제 직전 커밋)에 남아 있다.

## 측정

```bash
scripts/token-metrics.py --since 2026-10-20           # 전환 이후
scripts/token-metrics.py --since 2026-09-01 --until 2026-10-19   # 역할 위임 기간
scripts/token-metrics.py --band 11-30                 # 턴 수를 맞춰 비교
scripts/token-metrics.py --by-mode                    # [mode:xxx] 태그별 총 입력·교정 수
```

- **턴당 메인 입력**: 메인 컨텍스트 성장. 위임하면 줄고 직접 처리하면 는다.
- **턴당 총 입력**(메인+서브체인): 실제 처리량. 위임은 서브에이전트가 파일을 다시 읽어 늘어난다.
- **턴당 교정**: 결과 품질 대용. 키워드 휴리스틱이라 말없는 교정은 놓친다.
- `cache_read` 는 일반 입력과 1:1 로 더해진다. 요금은 약 1/10 이므로 토큰 수 ≠ 비용.

`--band` 가 중요하다. 밴드 없이 비교하면 결론이 뒤집힌다 — 위임 세션이 애초에 큰 작업이었다.
모든 수치는 무작위 배정이 아니므로 상관이며 인과가 아니다.

측정 결과는 `metrics/` 에 저장되고 `.gitignore` 로 제외된다. 프로젝트 경로명이
들어가기 때문이며, 이 레포는 공개다. `--by-project` 출력도 커밋하지 않는다.

## 새 PC 에 설치

```bash
git clone https://github.com/babysean/claude-config.git ~/Personal/claude-config
cd ~/Personal/claude-config
./install.sh
```

`install.sh` 는 기본적으로 **symlink** 로 건다. 레포 파일을 고치면 즉시
반영되고, `git pull` 한 번으로 모든 PC 가 같은 설정이 된다.

설치 과정은 2단계다. [1/2] 전역 규칙 `CLAUDE.md` (예전 설치가 남긴 `~/.claude/agents/` 링크도 정리),
[2/2] 도구 설치. 도구는 다음 4가지다:

- **ponytail** — Claude Code 플러그인. 최소 구현 강제 (SessionStart/SubagentStart/UserPromptSubmit hook).
  플러그인 `ponytail@ponytail` (마켓플레이스 GitHub `DietrichGebert/ponytail`).
- **context7** — Claude Code 플러그인. 라이브러리 최신 문서를 자동 조회하는 MCP.
  플러그인 `context7@claude-plugins-official` (공식 마켓플레이스).
- **typescript-lsp / pyright-lsp** — Claude Code 플러그인. TS/Python 코드 인텔리전스(LSP).
  플러그인 `typescript-lsp@claude-plugins-official`, `pyright-lsp@claude-plugins-official`.
  서버는 `npm install -g typescript-language-server typescript pyright` 로 설치.
- **graphify** — CLI 도구. 코드베이스의 지식 그래프를 생성해 구조 질의를 빠르게 한다 (CLAUDE.md §8).
  `uv tool install graphifyy`.

**선택 의존성:**
- `claude` CLI: 없으면 경고 후 플러그인 설치를 건너뜀.
- `uv`: 없으면 경고와 uv 설치 안내만 출력하고 graphify 는 건너뜀.
- `npm`: 없으면 경고만 출력하고 LSP 서버(`typescript-language-server`, `pyright-langserver`) 설치는 건너뜀.

| 옵션 | 동작 |
|---|---|
| (없음) 또는 `--symlink` | symlink 설치 (기본, 권장) |
| `--copy` | 복사 설치 — 레포 폴더를 지워도 유지 |
| `--dry-run` | 무엇이 바뀌는지만 출력, 실제 변경 없음 |
| `-h`, `--help` | 사용법 출력 |

설치 대상은 기본 `~/.claude` 다. `CLAUDE_HOME` 환경변수로 바꿀 수 있다.

```bash
CLAUDE_HOME=~/test-claude ./install.sh --dry-run
```

기존 `~/.claude/CLAUDE.md` 는 백업 없이 교체한다. `--copy` 로 설치했던 PC 의
옛 에이전트 파일(`~/.claude/agents/*.md`)은 자동으로 지우지 않으니 직접 지운다.

## 설정 수정 흐름

symlink 설치 기준으로 `~/.claude/CLAUDE.md` 를 고치면 이 레포의 파일이 바로
수정된다. 그대로 커밋·푸시하면 된다.

```bash
cd ~/Personal/claude-config
git add -A && git commit -m "CLAUDE.md: ..." && git push
```

다른 PC 에서는 `git pull` 만 하면 끝. Claude Code 는 세션 시작 시
설정을 읽으므로, 반영하려면 세션을 새로 띄운다.

## 포함하지 않는 것

`~/.claude/settings.json` 은 PC 마다 다른 권한 허용 목록·statusLine 경로가 들어가므로 의도적으로 제외했다. 필요한 항목만 새 PC 에서 직접 설정한다. 다만 플러그인(`ponytail`, `context7`, `typescript-lsp`, `pyright-lsp`)은 설치 시 Claude Code 가 자동으로 `settings.json` 에 등록하므로 수동 설정이 필요 없다.

매뉴얼(스킬)과 프로젝트 전용 에이전트(`<repo>/.claude/`)는 해당 레포가 관리한다.
`CLAUDE.md` §5 에 어느 레포에 무엇이 있는지만 적어 둔다.
