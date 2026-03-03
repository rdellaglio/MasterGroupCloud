#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="$REPO_ROOT/backups"
STAMP="$(date +%Y%m%d_%H%M%S)"
MAX_VERSIONS=4

mkdir -p "$BACKUP_DIR"

FILES=(
  "GestionaleMG.py"
  "requirements.txt"
)

SNAPSHOT_DIR="$BACKUP_DIR/$STAMP"
mkdir -p "$SNAPSHOT_DIR"

for file in "${FILES[@]}"; do
  if [[ -f "$REPO_ROOT/$file" ]]; then
    cp "$REPO_ROOT/$file" "$SNAPSHOT_DIR/$(basename "$file")"
  fi
done

# Keep only the latest MAX_VERSIONS snapshots
mapfile -t snapshots < <(find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
count=${#snapshots[@]}
if (( count > MAX_VERSIONS )); then
  remove_count=$((count - MAX_VERSIONS))
  for old in "${snapshots[@]:0:remove_count}"; do
    rm -rf "$BACKUP_DIR/$old"
  done
fi

echo "Backup creato in: $SNAPSHOT_DIR"
