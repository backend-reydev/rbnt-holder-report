PY ?= python3
EDITION ?= q3-2026
export RBNT_EDITION = $(EDITION)

.PHONY: all blocks named candidates balances analyse charts report check

all: blocks named candidates balances analyse charts report

blocks:
	$(PY) scripts/01_snapshot_blocks.py
named:
	$(PY) scripts/02_named_wallets.py
candidates:
	$(PY) scripts/03_holder_candidates.py
balances:
	$(PY) scripts/04_balances.py
analyse:
	$(PY) scripts/05_analyse.py
charts:
	$(PY) scripts/06_charts.py
report:
	$(PY) scripts/07_build_report.py

# Brand voice rule: no em or en dashes, anywhere in the repo.
check:
	@! grep -rnP '\xE2\x80[\x93\x94]' --exclude-dir=.git --exclude-dir=data --exclude=*.png . || (echo "Remove em or en dashes above"; exit 1)
	@echo "check passed"
