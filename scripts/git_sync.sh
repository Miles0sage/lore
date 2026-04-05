#!/usr/bin/env bash
# LORE Git Sync — pushes new/updated wiki articles to the public GitHub repo
# Runs nightly at 3:00 AM (after evolve_daemon.sh at 2:00 AM)
# Env vars:
#   LORE_PUBLIC_REPO  — path to public git repo (default: /root/lore)
#   LORE_WIKI_DIR     — path to wiki source (default: /root/wikis/ai-agents)

set -euo pipefail

REPO_DIR="${LORE_PUBLIC_REPO:-/root/lore}"
WIKI_SRC="${LORE_WIKI_DIR:-/root/wikis/ai-agents}/wiki"
LOG_FILE="/var/log/lore-git-sync.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"; }

log "=== LORE git sync starting ==="

# Sync wiki articles into public repo
if [[ ! -d "${WIKI_SRC}" ]]; then
    log "ERROR: wiki source not found: ${WIKI_SRC}"
    exit 1
fi

if [[ ! -d "${REPO_DIR}/.git" ]]; then
    log "ERROR: public repo not found: ${REPO_DIR}"
    exit 1
fi

# Copy updated wiki articles
CHANGED=0
while IFS= read -r -d '' f; do
    fname="$(basename "${f}")"
    dest="${REPO_DIR}/wiki/${fname}"
    if [[ ! -f "${dest}" ]] || ! cmp -s "${f}" "${dest}"; then
        cp "${f}" "${dest}"
        log "Updated: ${fname}"
        CHANGED=$((CHANGED + 1))
    fi
done < <(find "${WIKI_SRC}" -maxdepth 1 -name "*.md" -print0)

if [[ "${CHANGED}" -eq 0 ]]; then
    log "No changes — wiki is up to date"
    exit 0
fi

# Commit and push
cd "${REPO_DIR}"
git add wiki/
COUNT="$(git diff --cached --name-only | wc -l | tr -d ' ')"
DATE="$(date '+%Y-%m-%d')"
git commit -m "chore: nightly wiki sync ${DATE} (+${COUNT} articles)"
git push origin main
log "Pushed ${COUNT} article(s) to GitHub"
log "=== LORE git sync complete ==="
