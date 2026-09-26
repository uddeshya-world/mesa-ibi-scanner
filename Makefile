# Week 0 validation harness (TASK-0001).
# Scanner semantics are unchanged. T3 holdout is not part of `make verify`.

PYTHON ?= python3

.DEFAULT_GOAL := verify

.PHONY: verify t0 t1 t2 t3 t3-holdout evidence bench check-claims

# T0, then T1, then T2, then T3. Stop on the first failure.
verify:
	$(MAKE) t0
	$(MAKE) t1
	$(MAKE) t2
	$(MAKE) t3

t0:
	$(PYTHON) .github/harness/t0.py

t1:
	$(PYTHON) -m pytest -q --color=no tests/test_topology.py tests/test_topology_pdp_optional.py tests/test_cli_output.py tests/test_lattice_unit.py tests/test_temporal.py tests/test_claims.py

t2:
	$(PYTHON) -m pytest -q --color=no tests/test_properties.py tests/test_lattice_properties.py tests/test_temporal_properties.py

t3:
	$(PYTHON) -m pytest -q --color=no tests/test_closure.py tests/test_lattice_golden.py tests/test_temporal_golden.py

t3-holdout:
	$(PYTHON) .github/harness/holdout.py

# B-01 batch closure benchmark (target under 30 s).
bench:
	$(PYTHON) benchmarks/b01_batch_closure.py

# G11: every published number maps to a claims-ledger row.
check-claims:
	$(PYTHON) .github/harness/check_claims.py

# Usage: make evidence TASK=TASK-0001
evidence:
	@test -n "$(TASK)" || { echo "usage: make evidence TASK=<id>" >&2; exit 2; }
	$(PYTHON) .github/harness/evidence.py "$(TASK)"
