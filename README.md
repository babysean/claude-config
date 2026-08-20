# claude-config

Claude Code 개인 서브에이전트 설정. 여러 PC 에서 같은 위임 정책과
전문 에이전트를 쓰기 위한 저장소.

## 구성

| 경로 | 설치 위치 | 역할 |
|---|---|---|
| `CLAUDE.md` | `~/.claude/CLAUDE.md` | 위임 정책 + 라우팅 표 (모든 프로젝트에 전역 적용) |
| `agents/*.md` | `~/.claude/agents/` | 전문 에이전트 14종 |
| `install.sh` | — | 설치 스크립트 |

## 에이전트 목록

| 이름 | 담당 | 모델 |
|---|---|---|
| `software-architect` | 시스템 설계, 기술 스택 결정, 대규모 리팩터링 계획 | opus |
| `security-expert` | 취약점 점검, 인증/인가 검토, OWASP | opus |
| `backend-engineer` | 서버 로직, REST/GraphQL API, 비즈니스 로직 | sonnet |
| `frontend-engineer` | UI 컴포넌트, 스타일링, 클라이언트 상태 관리 | sonnet |
| `database-administrator` | 스키마 설계, 쿼리 튜닝, 마이그레이션 | sonnet |
| `code-reviewer` | 작성된 코드의 품질·버그 감사 | sonnet |
| `test-engineer` | 테스트 작성, 커버리지 분석, 테스트 전략 | sonnet |
| `devops-engineer` | CI/CD, Docker/K8s, 배포, 인프라 | sonnet |
| `performance-engineer` | 병목 분석, 프로파일링, 최적화 | sonnet |
| `data-engineer` | ETL 파이프라인, 데이터 모델링, 스트림 처리 | sonnet |
| `ml-ai-engineer` | ML 모델, LLM 연동, RAG, 프롬프트 설계 | sonnet |
| `codebase-explainer` | 낯선 레포 구조·흐름 파악 (읽기 전용) | sonnet |
| `project-manager` | 3개 이상 도메인이 얽힌 대형 다단계 작업 조율 | sonnet |
| `technical-writer` | README, API 문서, ADR, 체인지로그 | haiku |

## 새 PC 에 설치

```bash
git clone https://github.com/babysean/claude-config.git ~/Personal/claude-config
cd ~/Personal/claude-config
./install.sh
```

`install.sh` 는 기본적으로 **symlink** 로 건다. 레포 파일을 고치면 즉시
반영되고, `git pull` 한 번으로 모든 PC 가 같은 설정이 된다.

레포 폴더 위치에 묶이기 싫으면 복사 설치:

```bash
./install.sh --copy
```

무엇이 바뀌는지 먼저 보고 싶으면:

```bash
./install.sh --dry-run
```

기존 `~/.claude/CLAUDE.md` 나 동명의 에이전트가 있으면
`~/.claude/.backup-<타임스탬프>/` 로 백업한 뒤 교체한다.

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

## 포함하지 않는 것

`~/.claude/settings.json` 은 PC 마다 다른 권한 허용 목록·플러그인·
statusLine 경로가 들어가므로 의도적으로 제외했다. 필요한 항목만 새 PC 에서
직접 설정한다.
