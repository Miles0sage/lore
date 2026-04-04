#!/usr/bin/env bash
# LORE Auto-Evolve Daemon
# Runs the full dwiki evolution cycle and syncs new articles to NotebookLM.
# Designed to be invoked via cron at 2:00 AM daily.

set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
WIKI_DIR="/root/wikis/ai-agents"
LOG_FILE="/var/log/lore-evolve.log"
NOTEBOOK_ID="49dab3c1-06a5-4055-ae2d-7db48d5c576c"
PYTHON="/usr/bin/python3"
DWIKI="/usr/local/bin/dwiki"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUSH_SCRIPT="${SCRIPT_DIR}/notebooklm_push.py"

# Temp files scoped to this run (cleaned up on exit)
TMP_DIR="$(mktemp -d /tmp/lore-evolve.XXXXXX)"
GAPS_OUT="${TMP_DIR}/gaps.txt"
GRAPH_OUT="${TMP_DIR}/graph.txt"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
log() {
    local level="$1"; shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] $*" | tee -a "${LOG_FILE}"
}

log_info()  { log "INFO " "$@"; }
log_warn()  { log "WARN " "$@"; }
log_error() { log "ERROR" "$@"; }

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
cleanup() {
    rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------
preflight() {
    local ok=1

    if [[ ! -d "${WIKI_DIR}" ]]; then
        log_error "Wiki directory not found: ${WIKI_DIR}"
        ok=0
    fi

    if [[ ! -x "${DWIKI}" ]]; then
        log_error "dwiki not executable: ${DWIKI}"
        ok=0
    fi

    if [[ ! -f "${PUSH_SCRIPT}" ]]; then
        log_error "Push script not found: ${PUSH_SCRIPT}"
        ok=0
    fi

    if [[ ! -x "${PYTHON}" ]]; then
        log_error "Python not found: ${PYTHON}"
        ok=0
    fi

    if [[ "${ok}" -eq 0 ]]; then
        log_error "Preflight failed — aborting."
        exit 1
    fi

    # Ensure log file is writable
    touch "${LOG_FILE}" 2>/dev/null || {
        echo "Cannot write to ${LOG_FILE}" >&2
        exit 1
    }
}

# ---------------------------------------------------------------------------
# Step helpers — each step logs its outcome and returns non-zero on failure
# ---------------------------------------------------------------------------
run_step() {
    local step_name="$1"; shift
    local cmd=("$@")

    log_info "Starting: ${step_name}"
    if "${cmd[@]}"; then
        log_info "OK: ${step_name}"
        return 0
    else
        local rc=$?
        log_error "FAILED: ${step_name} (exit ${rc})"
        return "${rc}"
    fi
}

# ---------------------------------------------------------------------------
# Article + gap counters
# ---------------------------------------------------------------------------
count_articles() {
    find "${WIKI_DIR}/wiki" -maxdepth 1 -name "*.md" 2>/dev/null | wc -l
}

count_dangling_gaps() {
    # gaps output contains lines like "- topic" or similar; count non-empty lines
    # that aren't headers/separators
    if [[ -f "${GAPS_OUT}" ]]; then
        grep -c '^[-*]' "${GAPS_OUT}" 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    log_info "========================================"
    log_info "LORE evolve daemon starting"
    log_info "Wiki: ${WIKI_DIR}"
    log_info "Notebook: ${NOTEBOOK_ID}"
    log_info "========================================"

    preflight

    local errors=0

    # Change into wiki directory — all dwiki commands require this cwd
    cd "${WIKI_DIR}" || { log_error "Cannot cd to ${WIKI_DIR}"; exit 1; }

    # Step 1: gaps
    log_info "Step 1/5: dwiki gaps"
    if "${DWIKI}" gaps > "${GAPS_OUT}" 2>&1; then
        log_info "OK: gaps — saved to ${GAPS_OUT}"
        log_info "Gaps output:"
        while IFS= read -r line; do
            log_info "  ${line}"
        done < "${GAPS_OUT}"
    else
        log_warn "dwiki gaps returned non-zero (continuing)"
        (( errors++ )) || true
    fi

    # Step 2: compile
    if ! run_step "dwiki compile" "${DWIKI}" compile; then
        log_warn "compile step failed — continuing"
        (( errors++ )) || true
    fi

    # Step 3: index rebuild
    if ! run_step "dwiki index rebuild" "${DWIKI}" index rebuild; then
        log_warn "index rebuild failed — continuing"
        (( errors++ )) || true
    fi

    # Step 4: graph
    log_info "Step 4/5: dwiki graph"
    if "${DWIKI}" graph > "${GRAPH_OUT}" 2>&1; then
        log_info "OK: graph — saved to ${GRAPH_OUT}"
        log_info "Graph stats:"
        while IFS= read -r line; do
            log_info "  ${line}"
        done < "${GRAPH_OUT}"
    else
        log_warn "dwiki graph returned non-zero (continuing)"
        (( errors++ )) || true
    fi

    # Step 5: push new/modified articles to NotebookLM
    log_info "Step 5/5: notebooklm_push"
    if "${PYTHON}" "${PUSH_SCRIPT}" \
        --notebook-id "${NOTEBOOK_ID}" \
        --wiki-dir "${WIKI_DIR}/wiki"; then
        log_info "OK: notebooklm_push"
    else
        log_warn "notebooklm_push returned non-zero (continuing)"
        (( errors++ )) || true
    fi

    # Summary
    local article_count dangling_gaps
    article_count="$(count_articles)"
    dangling_gaps="$(count_dangling_gaps)"

    local status_label="OK"
    if [[ "${errors}" -gt 0 ]]; then
        status_label="PARTIAL (${errors} step(s) failed)"
    fi

    log_info "========================================"
    log_info "LORE evolve complete: ${article_count} articles, ${dangling_gaps} dangling gaps [${status_label}]"
    log_info "========================================"

    # Write the canonical summary line in a parseable format
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] LORE evolve complete: ${article_count} articles, ${dangling_gaps} dangling gaps" >> "${LOG_FILE}"

    if [[ "${errors}" -gt 0 ]]; then
        exit 1
    fi
}

main "$@"
