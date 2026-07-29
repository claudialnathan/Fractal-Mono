# Contributing

CLN Mono changes must preserve the fixed `579`-unit cell and remain compatible across both variable axes.

1. Create a focused branch.
2. Run `make setup` once.
3. Edit source geometry or build logic, not generated font binaries directly.
4. Run `make build`, `make test`, and `make specimens`.
5. Inspect Thin, Regular, and ExtraBold at optical sizes 9, 14, and 72.
6. Include regenerated fonts, reports, specimens, and release notes with the change.

Outline changes must be checked filled and stroked. Dot contours must remain four-point, on-curve, axis-aligned squares. Programming ligatures stay opt-in.
