# claude-config

Claude Code 개인 설정. 여러 PC 에서 같은 전역 작업 규칙과 전문 에이전트를
쓰기 위한 저장소.

## 구성

| 경로 | 설치 위치 | 역할 |
|---|---|---|
| `CLAUDE.md` | `~/.claude/CLAUDE.md` | 전역 작업 규칙 — 위임 정책, 라우팅 표, 웹 검색 출처 검증, 버그 대응 순서 |
| `agents/*.md` | `~/.claude/agents/` | 전문 에이전트 14종 |
| `install.sh` | — | 설치 스크립트 (symlink / 복사) |
| `scripts/token-metrics.py` | — | 위임 정책의 컨텍스트 효율 측정 |

## 전역 규칙 (`CLAUDE.md`)

메인 세션이 **총괄(orchestrator)** 이다. 직접 처리할지 위임할지 스스로
판단하고, 위임했더라도 최종 판단과 사용자 응답은 메인 세션이 한다.

| 절 | 내용 |
|---|---|
| §1 | 직접 처리 — 읽기·실행·대화만. **파일을 고치는 작업은 없다** |
| §2 | 위임 — 파일을 고치는 모든 작업 + 라우팅 표. 1줄 수정도 위임한다 |
| §3 | 위임할 때 지킬 것 (컨텍스트 실어 보내기, 결과 검증, 중복 검색 금지) |
| §4 | `<repo>/.claude/agents/` 정의가 `~/.claude/agents/` 보다 우선 |
| §5 | 웹 검색 결과를 쓸 때 — 날짜 확인, 신뢰 순서, 버전 명시 |
| §6 | 버그를 만났을 때 — 재현 → 가설 검증 → 근본 원인 → 회귀 테스트 |

경계는 **파일을 고치는가** 하나다. 오타 1개 수정도, 리뷰 지적 반영도 위임한다.
이전 정책은 "위임 비용이 이득보다 크다" 는 이유로 국소 수정과 리뷰 반영을
직접 처리로 뒀지만, 그 판단을 뒷받침할 측정치가 없었다. 아래 실험이 그
측정치를 만든다.

## 에이전트 목록

`쓰기` 열이 없는 에이전트는 `Edit`/`Write` 도구가 없어 코드를 고치지 못한다
(분석·감사·설명 전용).

| 이름 | 담당 | 모델 | effort | 쓰기 |
|---|---|---|---|---|
| `software-architect` | 시스템 설계, 기술 스택 결정, 대규모 리팩터링 계획 | opus | high | — |
| `security-expert` | 취약점 점검, 인증/인가 검토, OWASP | opus | high | — |
| `backend-engineer` | 서버 로직, REST/GraphQL API, 비즈니스 로직 | sonnet | medium | ✓ |
| `frontend-engineer` | UI 컴포넌트, 스타일링, 클라이언트 상태 관리 | sonnet | medium | ✓ |
| `database-administrator` | 스키마 설계, 쿼리 튜닝, 마이그레이션 | sonnet | medium | ✓ |
| `code-reviewer` | 작성된 코드의 품질·버그 감사 | sonnet | high | — |
| `test-engineer` | 테스트 작성, 커버리지 분석, 테스트 전략 | sonnet | medium | ✓ |
| `devops-engineer` | CI/CD, Docker/K8s, 배포, 인프라 | sonnet | medium | ✓ |
| `performance-engineer` | 병목 분석, 프로파일링, 최적화 | sonnet | high | — |
| `data-engineer` | ETL 파이프라인, 데이터 모델링, 스트림 처리 | sonnet | medium | ✓ |
| `ml-ai-engineer` | ML 모델, LLM 연동, RAG, 프롬프트 설계 | sonnet | medium | ✓ |
| `codebase-explainer` | 낯선 레포 구조·흐름 파악, 온보딩 로드맵 | sonnet | medium | — |
| `project-manager` | 3개 이상 도메인이 얽힌 대형 다단계 작업 조율 | sonnet | medium | ✓ |
| `technical-writer` | README, API 문서, ADR, 체인지로그 | haiku | low | ✓ |

`backend-engineer` · `frontend-engineer` · `database-administrator` ·
`performance-engineer` 에는 **Bug Investigation** 절이 있다. `CLAUDE.md` §2 가
원인 미상 버그를 도메인 전문가에게 넘기라고 지시하므로, 받는 쪽에 조사 절차가
있어야 한다.

`project-manager` 는 위임 정책이 대체한다. 사용자가 이름을 직접 부르거나 여러
전문 분야가 얽힌 다단계 작업일 때만 쓴다.

## 위임 정책 실험 (2026-09-01 ~)

신규 구축이든 유지보수든 파일 수정은 전부 위임하도록 §1·§2 를 고쳤다. 목적은
**제로샷 대비 컨텍스트 효율을 측정할 표본을 만드는 것** 이다.

지표는 **턴당 메인 세션 입력 토큰** 이다. 총 토큰이 아니다 — 위임하면
서브에이전트가 파일을 다시 읽으므로 총량은 늘어난다. 줄어드는 것은 메인
컨텍스트의 성장이고, 입력 토큰의 85% 가 `cache_read`(매 턴 컨텍스트 재독)
이므로 메인 컨텍스트가 작으면 이후 모든 턴이 싸진다.

```bash
scripts/token-metrics.py                      # 전체 기간
scripts/token-metrics.py --since 2026-09-02   # 정책 변경 이후만
scripts/token-metrics.py --band 11-30         # 턴 수를 맞춰 비교
scripts/token-metrics.py --json metrics/2026-10.json
```

`--band` 가 중요하다. 밴드 없이 비교하면 결론이 뒤집힌다 — 위임 세션이 애초에
큰 작업이라서 그렇다. 정책 변경 직전 베이스라인이 이 함정을 보여준다.

| 비교 방식 | 위임 (턴당) | 제로샷 (턴당) | 차이 |
|---|---|---|---|
| 전체 세션 (n=15 vs 181) | 8,239,724 | 7,391,288 | **+11.5%** |
| 11-30턴만 (n=9 vs 55) | 5,610,888 | 7,691,466 | **−27.1%** |

표본이 작고(위임 n=9) 무작위 배정이 아니므로 이 수치는 상관이며 인과가 아니다.
방향만 참고한다. 표본을 쌓는 것이 실험의 목적이다.

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

기존 `~/.claude/CLAUDE.md` 나 동명의 에이전트가 있으면
`~/.claude/.backup-<타임스탬프>/` 로 백업한 뒤 교체한다. 이 백업 폴더는
`.gitignore` 에 걸려 있어 커밋되지 않는다.

## 설정 수정 흐름

symlink 설치 기준으로 `~/.claude/agents/backend-engineer.md` 를 고치면
이 레포의 파일이 바로 수정된다. 그대로 커밋·푸시하면 된다.

```bash
cd ~/Personal/claude-config
git add -A && git commit -m "backend-engineer: ..." && git push
```

다른 PC 에서는 `git pull` 만 하면 끝. Claude Code 는 세션 시작 시
설정을 읽으므로, 반영하려면 세션을 새로 띄운다.

## 에이전트 정의 형식

```markdown
---
name: backend-engineer          # 파일명과 반드시 일치
description: 언제 이 에이전트를 쓸지. 메인 세션이 이걸 보고 라우팅한다.
tools: Read, Edit, Write, Bash, Grep, Glob, WebSearch, WebFetch
model: sonnet                   # opus | sonnet | haiku
effort: medium                  # low | medium | high
---

여기부터 에이전트의 시스템 프롬프트.
```

`name` 이 파일명과 다르면 호출되지 않는다. 이름을 바꿀 때는 `CLAUDE.md`
라우팅 표와 `agents/project-manager.md` 의 표까지 같이 고쳐야 한다.

읽기 전용으로 만들려면 `tools` 에서 `Edit` · `Write` 를 뺀다.

## 포함하지 않는 것

`~/.claude/settings.json` 은 PC 마다 다른 권한 허용 목록·플러그인·
statusLine 경로가 들어가므로 의도적으로 제외했다. 필요한 항목만 새 PC 에서
직접 설정한다.

프로젝트 전용 에이전트(`<repo>/.claude/agents/`)도 해당 레포가 관리한다.
`CLAUDE.md` §4 에 어느 레포에 무엇이 있는지만 적어 둔다.
