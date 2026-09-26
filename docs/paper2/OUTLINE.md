# Paper two: working outline (structure only)

Status: skeleton for G11. It holds structure, no framing and no numbers. The owner writes the framing. Every number enters through the claims ledger as `[[claim:CL-NNNN]]`.

## Sections

1. Problem: P-U-E composition across shared writable surfaces (from the published preprint; no new incident write-ups).
2. Derivation: Tier-0 inputs, mapping rules, confidence classes, facts that cannot be derived (docs/DERIVATION.md, docs/NEVER_DERIVABLE.md).
3. Graded lattice and zones (docs/LATTICE.md). Migration from the boolean model.
4. Temporal closure (docs/TEMPORAL.md). SC-03 as the worked case.
5. Evaluation:
   - derivation accuracy against the G2 pre-registered targets
   - false-positive reduction against the G6 pre-registered target
   - base rate with intervals and negative cases (docs/BASERATE.md)
6. Limitations: capability versus agent use in the corpus; frontier size; observer independence assumptions.
7. Related work.

## Claims to fill (after measurement)

| Section | Measure | Pre-registration |
| --- | --- | --- |
| 5 | T4 metrics per reference environment | gates/g2.yaml |
| 5 | FP reduction per estate | gates/g6.yaml |
| 5 | BR-1 with Wilson interval | gates/g8.yaml, gates/g9.yaml |
