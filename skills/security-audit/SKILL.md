---
name: security-audit
description: Cloudflare 보안 감사 스킬(cloudflare/security-audit-skill)을 부를 때마다 최신으로 받아 와 그 지침대로 코드베이스 전체 보안 감사를 돌린다. 형님이 /security-audit <범위> <단계(quick·standard·deep)> 로 직접 부를 때만 쓴다.
disable-model-invocation: true
---

# security-audit — 최신 원본으로 보안 감사

원본은 고치지 않는다. 이 스킬은 원본을 받아 오고 원본 지침을 넘겨줄 뿐이다.
수동 전용인 이유: 원본이 저절로 불려 오면 원본 실행 규칙("OS 샌드박스 없이는 대상 테스트를 실행하지 않는다")이
구현 세션에 걸려 spec-build 테스트가 멈출 수 있다.

- 원본: `https://github.com/cloudflare/security-audit-skill`
- 원본 사본: `~/.cache/claude-skills/security-audit-skill`
- 감사 요청: `$ARGUMENTS` (예: `apps/janus quick`)

## 순서

명령은 `&&`·`||`·`;` 로 잇지 않고 하나씩 실행한다. clone·fetch·pull 앞에는 `GIT_TERMINAL_PROMPT=0` 을 붙인다
(원격을 못 찾으면 비밀번호 입력을 기다리며 멈추지 않고 바로 실패하게).

1. **받아 오기.**
   - 사본이 없으면 `git clone https://github.com/cloudflare/security-audit-skill ~/.cache/claude-skills/security-audit-skill`.
   - 있으면 `git -C <사본> fetch` → `git -C <사본> log --oneline HEAD..origin/main` 으로 바뀐 커밋을 한 줄로 보여 준다
     (없으면 "변경 없음") → `git -C <사본> pull --ff-only`.
2. **실패하면.**
   - 사본이 있으면 `git -C <사본> rev-parse --short HEAD` 로 커밋을 확인하고 "최신을 못 받아 기존 사본(커밋 `<sha>`)으로 진행" 을 알린 뒤 계속한다.
   - 사본이 없으면 멈추고 실패 출력과 함께 보고한다.
3. **원본 따르기.** `<사본>/skills/security-audit/SKILL.md` 를 끝까지 읽는다. 그 폴더를 원본의 "Skill directory" 로 삼아
   원본 지침을 그대로 따른다. `$ARGUMENTS` 를 감사 요청으로 넘긴다 — 형님이 직접 부른 것이므로 원본의 전체 감사 요청이다.
   인자가 비었으면 원본 규칙대로 범위를 한 번 묻는다.
4. 원본 지침을 요약·생략하지 않는다. 출력 폴더 기본값도 원본을 따른다(`~/security-audit-skill/<레포>/run-N`).

## 완료 기준

- 받아 오기 결과(바뀐 커밋·"변경 없음"·기존 사본으로 진행)를 형님께 한 줄로 알렸다.
- 원본의 두 끝 상태 중 하나다: 보고서 3종이 쓰이고 두 검증 스크립트가 통과했거나, `run_status: "incomplete"` 와 이유가 기록됐다.

## 주의

- 원본을 검토 없이 최신으로 받는다. 바뀐 커밋 목록이 유일한 확인 수단이니 반드시 보여 준다.
- 이 PC 에는 OS 샌드박스가 없어 원본 규칙상 대상 코드를 실행하지 않는다. 확정보다 `needs_validation` 이 많이 나온다.
- 전체 감사는 하위 에이전트를 여러 개 띄운다. 처음에는 `quick` 이나 좁은 범위로 돈다.

## 파일

- 고친 기록은 `notes.md`
- 명세 `.requirements/보안감사-스킬-설치/`
