#!/usr/bin/env bash
# Claude Code 개인 에이전트 설정 설치 스크립트
#
#   ./install.sh            symlink 설치 (기본, 권장 — 레포를 고치면 즉시 반영)
#   ./install.sh --symlink  위와 같음 (명시용)
#   ./install.sh --copy     복사 설치 (레포 폴더를 지워도 유지)
#   ./install.sh --dry-run  무엇을 할지만 출력, 실제 변경 없음
#
# 설치 대상은 기본 ~/.claude 다. CLAUDE_HOME 환경변수로 바꿀 수 있다.
# [3/3] 에서 플러그인(ponytail, context7, typescript-lsp, pyright-lsp)과 graphify 도 설치한다 (claude/uv 가 있을 때만).
#
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${CLAUDE_HOME:-$HOME/.claude}"
MODE=symlink
DRY=0

for arg in "$@"; do
  case "$arg" in
    --copy)    MODE=copy ;;
    --symlink) MODE=symlink ;;
    --dry-run) DRY=1 ;;
    -h|--help) awk 'NR>1 && !/^#/ {exit} NR>1' "$0"; exit 0 ;;
    *) echo "알 수 없는 옵션: $arg" >&2; exit 1 ;;
  esac
done

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$DEST/.backup-$STAMP"

run() { if [ "$DRY" = 1 ]; then echo "  [dry-run] $*"; else "$@"; fi; }

echo "레포 : $REPO"
echo "대상 : $DEST"
echo "모드 : $MODE"
echo

# 기존 파일을 덮어쓰기 전에 백업한다.
backup() {
  local target="$1"
  [ -e "$target" ] || [ -L "$target" ] || return 0
  run mkdir -p "$BACKUP"
  run cp -RP "$target" "$BACKUP/"
  echo "  백업: $(basename "$target") -> ${BACKUP#$HOME/~}"
}

link_or_copy() {
  local src="$1" dst="$2"
  backup "$dst"
  run rm -rf "$dst"
  if [ "$MODE" = symlink ]; then run ln -s "$src" "$dst"; else run cp "$src" "$dst"; fi
}

run mkdir -p "$DEST/agents"

echo "[1/3] 에이전트"
for f in "$REPO"/agents/*.md; do
  name="$(basename "$f")"
  link_or_copy "$f" "$DEST/agents/$name"
  echo "  $name"
done

echo
echo "[2/3] CLAUDE.md"
link_or_copy "$REPO/CLAUDE.md" "$DEST/CLAUDE.md"
echo "  CLAUDE.md"

echo
echo "[3/3] 플러그인 / graphify (선택 — 실패해도 계속)"
# 마켓플레이스(GitHub repo 또는 이름), 플러그인 id
MARKETPLACES=(DietrichGebert/ponytail)
PLUGINS=(ponytail@ponytail context7@claude-plugins-official typescript-lsp@claude-plugins-official pyright-lsp@claude-plugins-official)
if command -v claude >/dev/null 2>&1; then
  # 이미 등록/설치돼 있어도 에러 없이 넘어가도록 || 로 경고만 남긴다. 설정은 claude CLI 가 등록한다.
  for m in "${MARKETPLACES[@]}"; do
    run claude plugin marketplace add "$m" --scope user || echo "  경고: 마켓플레이스 등록 실패/이미 있음: $m"
  done
  for p in "${PLUGINS[@]}"; do
    run claude plugin install "$p" --scope user || echo "  경고: 플러그인 설치 실패: $p"
  done
else
  echo "  경고: claude CLI 없음 — 플러그인 설치를 건너뜀 (${PLUGINS[*]})"
fi

if command -v graphify >/dev/null 2>&1; then
  echo "  graphify 이미 설치됨"
elif command -v uv >/dev/null 2>&1; then
  run uv tool install graphifyy || echo "  경고: graphify 설치 실패"
else
  echo "  경고: uv 없음 — graphify 건너뜀. 설치: https://docs.astral.sh/uv/ 후 'uv tool install graphifyy'"
fi

# LSP 플러그인은 서버 바이너리가 PATH 에 있어야 동작한다. (pyright 패키지가 pyright-langserver 를 제공)
if command -v typescript-language-server >/dev/null 2>&1; then
  echo "  typescript-language-server 이미 설치됨"
elif command -v npm >/dev/null 2>&1; then
  run npm install -g typescript-language-server typescript || echo "  경고: typescript-language-server 설치 실패"
else
  echo "  경고: npm 없음 — typescript-language-server 건너뜀. 'npm install -g typescript-language-server typescript'"
fi

if command -v pyright-langserver >/dev/null 2>&1; then
  echo "  pyright-langserver 이미 설치됨"
elif command -v npm >/dev/null 2>&1; then
  run npm install -g pyright || echo "  경고: pyright 설치 실패"
else
  echo "  경고: npm 없음 — pyright 건너뜀. 'npm install -g pyright'"
fi

echo
if [ "$DRY" = 1 ]; then
  echo "dry-run 완료 — 실제로 바뀐 것은 없다."
else
  [ -d "$BACKUP" ] && echo "기존 파일 백업 위치: $BACKUP"
  echo "설치 완료. Claude Code 를 새로 띄운 뒤 /agents 로 확인한다."
fi
