#!/usr/bin/env bash
# Claude Code 개인 에이전트 설정 설치 스크립트
#
#   ./install.sh            symlink 설치 (기본, 권장 — 레포를 고치면 즉시 반영)
#   ./install.sh --symlink  위와 같음 (명시용)
#   ./install.sh --copy     복사 설치 (레포 폴더를 지워도 유지)
#   ./install.sh --dry-run  무엇을 할지만 출력, 실제 변경 없음
#
# 설치 대상은 기본 ~/.claude 다. CLAUDE_HOME 환경변수로 바꿀 수 있다.
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

echo "[1/2] 에이전트"
for f in "$REPO"/agents/*.md; do
  name="$(basename "$f")"
  link_or_copy "$f" "$DEST/agents/$name"
  echo "  $name"
done

echo
echo "[2/2] CLAUDE.md"
link_or_copy "$REPO/CLAUDE.md" "$DEST/CLAUDE.md"
echo "  CLAUDE.md"

echo
if [ "$DRY" = 1 ]; then
  echo "dry-run 완료 — 실제로 바뀐 것은 없다."
else
  [ -d "$BACKUP" ] && echo "기존 파일 백업 위치: $BACKUP"
  echo "설치 완료. Claude Code 를 새로 띄운 뒤 /agents 로 확인한다."
fi
