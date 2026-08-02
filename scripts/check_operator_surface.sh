#!/usr/bin/env bash
# scripts/check_operator_surface.sh
#
# Operator surface verifier for the laptopfinder-operator skill.
# Checks that every command, script, and Makefile target referenced in
# .agents/skills/laptopfinder-operator/SKILL.md exists on disk.
#
# Exit codes:
#   0  all required surfaces present   (GO)
#   1  one or more surfaces missing    (NO-GO)
#
# Usage:
#   bash scripts/check_operator_surface.sh
#   make check-operator-surface
#
# Read-only and side-effect free. Never writes to the repo, never calls
# network APIs, never reads secret values.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_PATH="${REPO_ROOT}/.agents/skills/laptopfinder-operator/SKILL.md"
MAKEFILE="${REPO_ROOT}/Makefile"
PASS=0
FAIL=0

ok()  { echo "[OK]   $*"; PASS=$((PASS + 1)); }
fail(){ echo "[FAIL] $*"; FAIL=$((FAIL + 1)); }
warn(){ echo "[WARN] $*"; }
hdr() { echo ""; echo "=== $* ==="; }

# ── 1. Canonical skill file ───────────────────────────────────────────────────
hdr "1/6  Canonical skill file"
if [[ -f "${SKILL_PATH}" ]]; then
    ok "SKILL.md present: ${SKILL_PATH}"
else
    fail "SKILL.md missing: ${SKILL_PATH}"
fi

# ── 2. Five-mode run_mode contract ────────────────────────────────────────────
hdr "2/6  Five-mode run_mode contract"
for mode in fixtures_only sniper_preflight sniper_live hunter_dry_run hunter_live; do
    if grep -q "${mode}" "${SKILL_PATH}"; then
        ok "run_mode '${mode}' declared in SKILL.md"
    else
        fail "run_mode '${mode}' NOT found in SKILL.md"
    fi
done

# ── 3. Required Makefile targets ──────────────────────────────────────────────
hdr "3/6  Makefile targets"
for target in pipeline live live-daemon live-stop live-tail hunt status test \
              check-operator-surface "operator/help" pwm-preflight ebay-watchlist-snapshot; do
    if grep -qE "^${target}:" "${MAKEFILE}"; then
        ok "Makefile target '${target}'"
    else
        fail "Makefile target '${target}' NOT found"
    fi
done

# ── 4. Required script files ──────────────────────────────────────────────────
hdr "4/6  Script files"
for script in \
    scripts/check_operator_surface.sh \
    scripts/authenticate_ebay_user.py \
    scripts/refresh_ebay_user.py \
    scripts/status_snapshot.py \
    scripts/render_matrix.py \
    scripts/build_shortlist_value.py \
    scripts/lf_floor_sync.py \
    scripts/lf_price_baseline.py \
    scripts/inject_config.py; do
    if [[ -f "${REPO_ROOT}/${script}" ]]; then
        ok "${script}"
    else
        fail "${script} NOT found on disk"
    fi
done

# ── 5. Required Python runner modules ─────────────────────────────────────────
hdr "5/6  Python runner modules"
for module in \
    src/laptopfinder/__init__.py \
    src/laptopfinder/core.py \
    src/laptopfinder/decide.py \
    src/laptopfinder/ingest_csv.py \
    src/laptopfinder/adapters/__init__.py \
    src/laptopfinder/adapters/ebay.py \
    src/laptopfinder/runners/ebay_sniper.py \
    src/laptopfinder/runners/hunt.py; do
    if [[ -f "${REPO_ROOT}/${module}" ]]; then
        ok "${module}"
    else
        fail "${module} NOT found on disk"
    fi
done

# ── 6. Stale-invocation guard ─────────────────────────────────────────────────
hdr "6/6  Stale invocation guard"
if grep -q "laptopfinder.core pipeline" "${MAKEFILE}"; then
    fail "Makefile still uses deprecated 'python -m laptopfinder.core pipeline'"
else
    ok "Makefile uses current 'python -m laptopfinder pipeline'"
fi

# Warn on any remaining interim four-mode draft names
for old_mode in '"preflight"' '"fixtures"'; do
    if grep -qF "${old_mode}" "${SKILL_PATH}"; then
        warn "Possible stale interim mode name ${old_mode} in SKILL.md — verify"
    fi
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════"
printf "  Operator Surface Check: %d passed, %d failed\n" "${PASS}" "${FAIL}"
echo "══════════════════════════════════════════════════════"

if [[ "${FAIL}" -gt 0 ]]; then
    echo ""
    echo "NO-GO: resolve [FAIL] items before running sniper_live or hunter_live."
    exit 1
else
    echo ""
    echo "GO: operator surface verified."
    echo "Safe to proceed with: make pipeline / make live / make hunt"
    exit 0
fi
