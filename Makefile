PY ?= python3
EDITION ?= q3-2026
export RBNT_EDITION = $(EDITION)

.PHONY: all data analyse build verify test check snapshots scan internal labels balances contracts charts

all: data analyse build verify

data: snapshots scan internal labels balances contracts

snapshots:
	$(PY) scripts/01_snapshots.py
scan:
	$(PY) scripts/02_scan_chain.py
internal:
	$(PY) scripts/03_internal_transfers.py
labels:
	$(PY) scripts/04_explorer_labels.py
balances:
	$(PY) scripts/05_balances.py
contracts:
	$(PY) scripts/06_contracts.py
analyse:
	$(PY) scripts/07_analyse.py
charts:
	$(PY) scripts/08_charts.py
build: charts
	$(PY) scripts/09_build.py
verify:
	$(PY) scripts/10_verify.py

# Offline checks, no network needed: unit tests plus the publishing rules
# (no unlabelled address, no dashes, no emoji, no price talk, no credit lines).
test:
	$(PY) -m pytest -q tests
check: test
	$(PY) scripts/10_verify.py --offline
