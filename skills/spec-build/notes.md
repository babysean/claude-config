# notes (최신이 위)

- 2026-10-21 · 증명 · 실패 기록을 Claude 가 직접 쓰면 믿는 수밖에 없음 → 실패 테스트를 따로 커밋(tdd.py red)하고 PR 전 verify 가 그 커밋을 다시 돌려 확인. CI 는 push 단위라 비용 불변, 워크트리에선 graphify 훅이 안 돌아 커밋 비용 작음, 호출 수 늘지 않게 한 호출로 묶음. "이름 없음" 실패는 빈 껍데기로 단언 실패를 보게 함(superpowers 와 같은 처리)

- 2026-10-21 · 증명 · 사용자 지적 "테스트가 없다, TDD 로" → 명세에 테스트 목록(조건 → 기대 결과) 필수, 구현계획이 PR 별로 나눠 갖고, spec-build 가 줄 하나씩 실패→통과→정리. 실패·통과 기록을 check_progress 가, 테스트 목록·구현계획 테스트를 check.py 가 검사. 확정된 옛 명세는 그대로(spec-build 가 시작 때 뽑아 씀)

- 2026-10-21 · 첫 실사용(Janus 4번 #2271) · 워크트리 격리로 메인 `.requirements/` 쓰기 거부 → 장부를 scratchpad 에 두고 cleanup 뒤 복사하도록 SKILL.md 입력 절 보강. 자체 리뷰에서 "다음 PR 로" 미룬 지적을 Rumi 가 medium 으로 다시 짚음 — 같은 PR 에서 고치는 편이 회차가 적다

- 2026-10-21 · 이름 · design-doc·implement-plan → spec-write·spec-build (같은 앞말로 한 흐름의 앞뒤임을 드러냄)

- 2026-10-21 · 첫판 · 사용자 인터뷰 10문항으로 작성. 참고: spec-kit `/implement`, superpowers `executing-plans`(판정 장부·멈춤 조건·실패 테스트 먼저). Rumi 는 명세(.requirements)를 못 보고 PR 본문 `배경`·`요약` 의 목록 아닌 줄만 읽음 → 명세 대조를 `### 배경` 에 표로. 첫 실사용 결과를 examples/ 에 저장할 것
