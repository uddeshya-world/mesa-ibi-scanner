# Security Policy

## Scope

`mesa-ibi-scanner` is a **research prototype**. It evaluates a formal graph property (MESA-INV-01) against **user-supplied or toy fixtures**. It does **not**:

- Discover live Schelling points or scan production estates by default
- Include exploit payloads, weaponized scanners, or attack playbooks
- Replace a PDP, mesh, or admission controller

## Reporting

If you find a vulnerability in this repository (e.g. unsafe deserialization of untrusted graph JSON in a future release, dependency issues), email the maintainer via the GitHub security advisory flow Prefer **private vulnerability reporting** on GitHub over public issues.

## Safe use

- Treat CLI output as advisory analysis, not an enforcement decision.
- Do not point future live connectors at systems you do not own or are not authorized to assess.
- Keep ACM examples and fixtures out of production secret stores.
