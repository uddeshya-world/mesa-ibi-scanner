# Property coverage (roadmap Section 9, T2)

There are 16 properties. Each one is checked in at least one repository. The mesa-ibi-derive, mesa-d and mesa-pep tests live in those repositories.

| Property | What it checks | Where |
| --- | --- | --- |
| P-01 | Monotonicity | scanner `tests/test_lattice_properties.py` |
| P-02 | Join laws | scanner `tests/test_lattice_properties.py` |
| P-03 | Mask attenuation | scanner `tests/test_lattice_properties.py` |
| P-04 | Gating soundness | scanner `tests/test_lattice_properties.py` |
| P-05 | Boolean compatibility | scanner `tests/test_lattice_properties.py` |
| P-06 | Incremental equals batch | mesa-d `tests/test_properties.py` |
| P-07 | Frontier correctness | scanner `tests/test_lattice_properties.py`; consumption in mesa-pep `tests/pep.rs` |
| P-08 | Temporal | scanner `tests/test_temporal_properties.py` |
| P-09 | Upward-only models | scanner `tests/test_advisory.py`; mesa-pep `tests/pep.rs` |
| P-10 | Determinism | scanner `tests/test_lattice_properties.py`; mesa-ibi-derive `tests/test_properties.py` |
| P-11 | Witness validity | scanner `tests/test_lattice_properties.py` |
| P-12 | Minimal-cut validity | scanner `tests/test_lattice_properties.py` |
| P-13 | Provenance | mesa-ibi-derive `tests/test_properties.py` |
| P-14 | Overlay survival | mesa-ibi-derive `tests/test_properties.py` |
| P-15 | Fail-closed | scanner `tests/test_advisory.py`; mesa-pep `tests/pep.rs` |
| P-16 | Record completeness | mesa-pep `tests/pep.rs` |

All of these tests were written by agents under the harness in `docs/VALIDATION.md`. Passing them shows that the code matches the tests, not that the tests match the spec. The owner reviews the property tests before any gate cites them.
