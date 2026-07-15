.PHONY: test lint pipeline live hunt status \
        pwm-preflight \
        pwm-floor-sync-prep pwm-floor-sync-check \
        pwm-watch-grad-prep pwm-watch-grad-check \
        pwm-query-expand-prep pwm-query-expand-check \
        pwm-exclusion-tune-prep pwm-exclusion-tune-check \
        pwm-seller-intel-prep pwm-seller-intel-check \
        ebay-watchlist-snapshot

OP_RUN ?= op run --env-file=.env --

test:
	.venv/bin/python -m pytest tests/ -v

# Zero-LLM snapshot of runner/evidence state + NEXT_TASK queue (reads existing files only).
status:
	.venv/bin/python scripts/status_snapshot.py

lint:
	.venv/bin/python -m ruff check src/ tests/

# Run Stage 1 then Stage 2+decide sequentially against paired fixtures.
# Usage: make pipeline STAGE1=tests/fixtures/stage1/ebay_rtx4090_laptop.json STAGE2=tests/fixtures/stage2/ebay_facts_grounded.json
pipeline:
	@test -n "$(STAGE1)" || (echo "ERROR: Set STAGE1=<path>" && exit 1)
	@test -n "$(STAGE2)" || (echo "ERROR: Set STAGE2=<path>" && exit 1)
	.venv/bin/python -m laptopfinder.core pipeline $(STAGE1) $(STAGE2)

# Run the AU sniper live (requires credentials via 1Password).
live:
	$(OP_RUN) .venv/bin/python -m laptopfinder.runners.ebay_sniper

# Run a target JSON-driven ad hoc discovery sweep.
# Usage: make hunt CONFIG=config/runs/desktop_replacement.json
# Add DRY_RUN=1 to suppress email and state writes regardless of config.
hunt:
	@test -n "$(CONFIG)" || (echo "ERROR: Set CONFIG=<path to operator run config JSON>" && exit 1)
	$(OP_RUN) .venv/bin/python -m laptopfinder.runners.hunt \
	  --config $(CONFIG) \
	  $(if $(DRY_RUN),--dry-run)

# ─── PWM: Sniper Pre-flight Gate ───────────────────────────────────────────────
pwm-preflight:
	@echo "=== [1/5] Running test suite ==="
	@$(MAKE) test
	@echo ""
	@echo "=== [2/5] Validating SRL JSON ==="
	@.venv/bin/python -m json.tool config/static_reference_layer.json > /dev/null \
	  && echo "[OK] config/static_reference_layer.json valid" \
	  || (echo "[FAIL] SRL JSON invalid — fix before running sniper"; exit 1)
	@echo ""
	@echo "=== [3/5] Checking search query count ==="
	@lines=$$(grep -cvE '^[[:space:]]*(#|$$)' prompts/search_queries.txt); \
	  [ "$$lines" -ge 25 ] \
	  && echo "[OK] prompts/search_queries.txt: $$lines active queries" \
	  || echo "[WARN] Only $$lines queries — run: make pwm-query-expand-prep"
	@echo ""
	@echo "=== [4/5] Checking eBay access token age (stale = >7200s / 2h) ==="
	@.venv/bin/python -c "import os,time; f='.ebay_access_token'; rf='.ebay_refresh_token'; age=int(time.time()-os.path.getmtime(f)) if os.path.exists(f) else -1; print(f'[OK] Token fresh ({age}s old)') if 0<=age<7200 else (os.system('$(OP_RUN) .venv/bin/python scripts/refresh_ebay_user.py') if os.path.exists(rf) else (print(f'[WARN] Token stale ({age}s old) — run: $(OP_RUN) .venv/bin/python scripts/authenticate_ebay_user.py') if age>=7200 else print('[FAIL] .ebay_access_token missing — run: $(OP_RUN) .venv/bin/python scripts/authenticate_ebay_user.py')))"
	@echo ""
	@echo "=== [5/5] PWM workflow due checklist ==="
	@printf "[ ] lf-floor-sync     monthly; update observed_au_price_min_aud floors\n"
	@printf "[ ] lf-watch-grad     monthly or on Blackwell / RTX 5000 news\n"
	@printf "[ ] lf-query-expand   monthly or on major GPU launch\n"
	@printf "[ ] lf-seller-intel   monthly; populate watched_sellers before make live\n"
	@printf "[ ] lf-exclusion-tune per false-positive cluster in sniper output\n"
	@echo ""
	@echo "=== Pre-flight complete. Resolve [FAIL]/[WARN] before: make live ==="

# ─── PWM: lf-floor-sync ────────────────────────────────────────────────────────
pwm-floor-sync-prep:
	@mkdir -p data/pwm/lf-floor-sync
	@.venv/bin/python -c "import json; srl=json.load(open('config/static_reference_layer.json')); [print(k,'|',srl['target_gpus'][k].get('observed_au_price_min_aud','—'),'--',srl['target_gpus'][k].get('observed_au_price_max_aud','—')) for k in srl['target_gpus']]"

pwm-floor-sync-check:
	@test -f data/pwm/lf-floor-sync/price_patches.json \
	  && .venv/bin/python -c "import json,os,time; p=json.load(open('data/pwm/lf-floor-sync/price_patches.json')); filled=[x for x in p if x.get('new_min_aud')]; age_d=(time.time()-os.path.getmtime('data/pwm/lf-floor-sync/price_patches.json'))/86400; print(len(filled),'patches ready,','%.0f'%age_d,'days old'); print('[WARN] Patches stale (>30d) — re-run lf-floor-sync') if age_d>30 else None" \
	  || echo "[FAIL] price_patches.json missing or empty"

# ─── PWM: lf-watch-grad ────────────────────────────────────────────────────────
pwm-watch-grad-prep:
	@mkdir -p data/pwm/lf-watch-grad
	@.venv/bin/python -c "import json; srl=json.load(open('config/static_reference_layer.json')); [print(w['name'],'|',w['graduation_condition']) for w in srl['watch_list']]"

pwm-watch-grad-check:
	@test -f data/pwm/lf-watch-grad/graduation_report.md \
	  && grep -cE 'GRADUATE|HOLD|DEFER' data/pwm/lf-watch-grad/graduation_report.md \
	  || echo "[FAIL] graduation_report.md missing or has no GRADUATE/HOLD/DEFER verdicts"

# ─── PWM: lf-query-expand ──────────────────────────────────────────────────────
pwm-query-expand-prep:
	@mkdir -p data/pwm/lf-query-expand
	@echo "--- Current queries (non-comment lines) ---"
	@grep -vE '^[[:space:]]*(#|$$)' prompts/search_queries.txt
	@echo "--- SRL target GPU names ---"
	@.venv/bin/python -c "import json; srl=json.load(open('config/static_reference_layer.json')); [print(k) for k in srl['target_gpus']]"

pwm-query-expand-check:
	@lines=$$(grep -cvE '^[[:space:]]*(#|$$)' data/pwm/lf-query-expand/proposed_queries.txt 2>/dev/null || echo 0); \
	  [ "$$lines" -ge 3 ] && echo "[OK] $$lines new queries proposed" \
	  || echo "[FAIL] only $$lines proposed queries in data/pwm/lf-query-expand/proposed_queries.txt (need >=3)"

# ─── PWM: lf-exclusion-tune ────────────────────────────────────────────────────
# Companion script used (scripts/pwm_exclusion_tune_prep.py) so srl + corpus share one Python scope.
pwm-exclusion-tune-prep:
	@mkdir -p data/pwm/lf-exclusion-tune
	@.venv/bin/python scripts/pwm_exclusion_tune_prep.py

pwm-exclusion-tune-check:
	@test -f data/pwm/lf-exclusion-tune/exclusion_patch.json \
	  && .venv/bin/python -c "import json; p=json.load(open('data/pwm/lf-exclusion-tune/exclusion_patch.json')); adds=p.get('proposed_additions',[]); safe=[x for x in adds if x.get('false_negative_risk') in ('low','medium')]; print('[OK]',len(safe),'safe pattern(s) proposed out of',len(adds)) if safe else print('[WARN] no low/medium risk patterns in exclusion_patch.json')" \
	  || echo "[FAIL] exclusion_patch.json missing"

# ─── PWM: lf-seller-intel ──────────────────────────────────────────────────────
# Companion script used (scripts/pwm_seller_intel_prep.py) so srl + corpus share one Python scope.
pwm-seller-intel-prep:
	@mkdir -p data/pwm/lf-seller-intel
	@.venv/bin/python scripts/pwm_seller_intel_prep.py

pwm-seller-intel-check:
	@test -f data/pwm/lf-seller-intel/seller_patches.json \
	  && .venv/bin/python scripts/pwm_seller_intel_check.py \
	  || echo "[FAIL] seller_patches.json missing"

# ─── eBay Watchlist Snapshot (non-PWM, one-off) ────────────────────────────────
ebay-watchlist-snapshot:
	@mkdir -p data/pwm/lf-watchlist
	@.venv/bin/python -c "import os,time; f='.ebay_access_token'; rf='.ebay_refresh_token'; age=int(time.time()-os.path.getmtime(f)) if os.path.exists(f) else -1; os.system('$(OP_RUN) .venv/bin/python scripts/refresh_ebay_user.py') if (age>=7200 or age<0) and os.path.exists(rf) else None"
	$(OP_RUN) .venv/bin/python tools/ebay_watchlist_snapshot.py
