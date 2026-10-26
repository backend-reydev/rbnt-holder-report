PY ?= python3
EDITION ?= q3-2026
RUN = RBNT_EDITION=$(EDITION) PYTHONPATH=src $(PY) -m rbnt

.PHONY: all data report check test
all:
	$(RUN) all
data:
	$(RUN) data
report:
	$(RUN) report
test:
	PYTHONPATH=src $(PY) -m pytest -q tests
check: test
	$(RUN) audit --offline
