#!/usr/bin/env bash
# RabbitReels Production → Local Sync
# ----------------------------------
# Pulls files from prod `/home/rabbitreels/rabbitreels` into a timestamped
# local directory, excl. node_modules, .git, .env* etc.

set -euo pipefail
IFS=$'\n\t'

# ─── Colors & Logging ───────────────────────────────────────────────────
RED='\033[0;31m';   GREEN='\033[0;32m';  YELLOW='\033[1;33m';  NC='\033[0m'
log()    { echo -e "${GREEN}[INFO]${NC}    $1"; }
warn()   { echo -e "${YELLOW}[WARNING]${NC} $1"; }
err()    { echo -e "${RED}[ERROR]${NC}   $1"; exit 1; }

# ─── Configuration ──────────────────────────────────────────────────────
PROD_USER="rabbitreels"
PROD_HOST="64.23.135.94"
PROD_PATH="/home/${PROD_USER}/RabbitReels"
LOCAL_BACKUP_DIR="production_backup_$(date +%Y%m%d_%H%M%S)"

# ─── Start ──────────────────────────────────────────────────────────────
log "Syncing RabbitReels from ${PROD_USER}@${PROD_HOST}:${PROD_PATH}"
log "Local backup dir will be: ${LOCAL_BACKUP_DIR}"
mkdir -p "$LOCAL_BACKUP_DIR"

# ─── Sync step (rsync → scp fallback) ───────────────────────────────────
log "Attempting to sync with rsync…"
if command -v rsync >/dev/null 2>&1; then
  rsync -azv --progress \
    --exclude='node_modules/' \
    --exclude='.git/' \
    --exclude='*.env*' \
    --exclude='production_backup_*' \
    --exclude='current_backup_*' \
    --exclude='data/' \
    -e ssh \
    "${PROD_USER}@${PROD_HOST}:${PROD_PATH}/" \
    "$LOCAL_BACKUP_DIR/"
else
  warn "rsync not found – falling back to scp (no excludes)"
  scp -r "${PROD_USER}@${PROD_HOST}:${PROD_PATH}/" "$LOCAL_BACKUP_DIR/"
fi

# ─── Summary ────────────────────────────────────────────────────────────
log "✅ Files synced to $LOCAL_BACKUP_DIR"
log "Contents:"
ls -1 "$LOCAL_BACKUP_DIR" | sed 's/^/   • /'

cat << 'EOF'

🎉 Sync complete!
Next, if you want to overwrite your current working tree with this backup:

  ./restore_from_production.sh

EOF
