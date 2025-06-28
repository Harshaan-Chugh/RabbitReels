#!/usr/bin/env bash
# RabbitReels Restore from Production Backup
# ------------------------------------------
# Copies the most recent production_backup_* into the current directory,
# after backing up your existing files to current_backup_*.

set -euo pipefail
IFS=$'\n\t'
shopt -s dotglob   # include hidden files

# ─── Colors & Logging ───────────────────────────────────────────────────
RED='\033[0;31m';   GREEN='\033[0;32m';  YELLOW='\033[1;33m';  NC='\033[0m'
log()    { echo -e "${GREEN}[INFO]${NC}    $1"; }
warn()   { echo -e "${YELLOW}[WARNING]${NC} $1"; }
err()    { echo -e "${RED}[ERROR]${NC}   $1"; exit 1; }

# ─── Locate latest backup ────────────────────────────────────────────────
BACKUP_DIR=$(ls -td production_backup_* 2>/dev/null | head -1)
[ -z "$BACKUP_DIR" ] && err "No production_backup_* directory found."

log "Found production backup: $BACKUP_DIR"
read -p "⚠️  This will overwrite your current files. Continue? (y/N) " -n1 REPLY
echo
[[ ! "$REPLY" =~ ^[Yy]$ ]] && log "Restore cancelled." && exit 0

# ─── Backup current files ───────────────────────────────────────────────
CURRENT_BACKUP="current_backup_$(date +%Y%m%d_%H%M%S)"
log "Backing up existing files to $CURRENT_BACKUP"
mkdir -p "$CURRENT_BACKUP"
for item in * .*; do
  # skip self and backup dirs
  [[ "$item" =~ ^(\.|\.\.|production_backup_|current_backup_|restore_from_production\.sh)$ ]] && continue
  mv "$item" "$CURRENT_BACKUP/"
done

# ─── Restore prod files ─────────────────────────────────────────────────
log "Copying files from $BACKUP_DIR → current directory"
cp -a "$BACKUP_DIR/." .

log "✅ Restore complete!"
warn "Don't forget to update local .env files, database URLs, API keys, etc."
