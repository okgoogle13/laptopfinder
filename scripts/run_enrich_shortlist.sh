#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="/Users/okgoogle13/Projects/laptopfinder"
PYTHON="${PROJECT_ROOT}/.venv/bin/python"
RUNNER="${PROJECT_ROOT}/runners/enrich_shortlist.py"
LOG_DIR="${PROJECT_ROOT}/output/logs"
REPORT_DIR="${PROJECT_ROOT}/output/shortlist"
LOCK_DIR="/tmp/laptopfinder-enrich.lock"

mkdir -p "${LOG_DIR}" "${REPORT_DIR}"

timestamp="$(date '+%Y%m%d_%H%M%S')"
log_file="${LOG_DIR}/enrich_${timestamp}.log"
report_file="${REPORT_DIR}/latest_enriched.md"

exec >>"${log_file}" 2>&1

echo "[$(date -Iseconds)] Starting shortlist enrichment"

if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
    echo "[$(date -Iseconds)] Another enrichment run is already active; exiting"
    exit 0
fi

cleanup() {
    rmdir "${LOCK_DIR}" 2>/dev/null || true
}
trap cleanup EXIT

cd "${PROJECT_ROOT}"

if [[ -f ".env" ]]; then
    set -a
    source .env
    set +a
fi

export PYTHONUNBUFFERED=1
export PYTHONPATH="${PROJECT_ROOT}"

"${PYTHON}" "${RUNNER}" \
    --output "${report_file}"

echo "[$(date -Iseconds)] Enrichment completed"
echo "[$(date -Iseconds)] Report: ${report_file}"

if [[ -n "${LAPTOPFINDER_NOTIFY_TO:-}" ]]; then
    subject="Laptopfinder shortlist updated: ${timestamp}"

    {
        echo "Laptopfinder shortlist enrichment completed."
        echo
        echo "Report: ${report_file}"
        echo "Log: ${log_file}"
        echo
        tail -n 80 "${report_file}"
    } | /usr/bin/mail \
        -s "${subject}" \
        "${LAPTOPFINDER_NOTIFY_TO}"
fi

echo "[$(date -Iseconds)] Notification step completed"
