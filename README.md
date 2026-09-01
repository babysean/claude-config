# claude-config

Claude Code 개인 설정. 여러 PC 에서 같은 전역 작업 규칙과 전문 에이전트를
쓰기 위한 저장소.

## 구성

| 경로 | 설치 위치 | 역할 |
|---|---|---|
| `CLAUDE.md` | `~/.claude/CLAUDE.md` | 전역 작업 규칙 — 위임 정책, 라우팅 표, 웹 검색 출처 검증, 버그 대응 순서 |
| `agents/*.md` | `~/.claude/agents/` | 전문 에이전트 14종 |
| `install.sh` | — | 설치 스크립트 (symlink / 복사) |

## 전역 규칙 (`CLAUDE.md`)

메인 세션이 **총괄(orchestrator)** 이다. 직접 처리할지 위임할지 스스로
판단하고, 위임했더라도 최종 판단과 사용자 응답은 메인 세션이 한다.

| 절 | 내용 |
|---|---|
| §1 | 직접 처리 — 위임하지 않는 범위 (파일 1개 국소 수정, 빌드/테스트 실행, 리뷰 지적 반영 등) |
| §2 | 위임 기준 + 라우팅 표. 애매하면 위임한다 |
| §3 | 위임할 때 지킬 것 (컨텍스트 실어 보내기, 결과 검증, 중복 검색 금지) |
| §4 | `<repo>/.claude/agents/` 정의가 `~/.claude/agents/` 보다 우선 |
| §5 | 웹 검색 결과를 쓸 때 — 날짜 확인, 신뢰 순서, 버전 명시 |
| §6 | 버그를 만났을 때 — 재현 → 가설 검증 → 근본 원인 → 회귀 테스트 |

§1 의 "리뷰 지적 반영" 은 파일 수를 따지지 않는다. 판단은 이미 리뷰어가
끝냈고 finding 컨텍스트가 메인에 있어서, 위임하면 그걸 통째로 재작성해야
한다. 단 재설계가 필요하거나 대상이 5개 파일 이상이면 위임한다.

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
