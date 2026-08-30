# Finance Tracker v2.2.4 — Release Test Report

Corrective build based on v2.2.1.

## Validated
- VERSION source set to 2.2.4.
- Python source byte-compiles.
- Jinja templates parse.
- macOS package scripts pass shell syntax checks where supported.
- Installer payload excludes `data/` and `.venv/`.
- Upgrade preinstall preserves `data/` and removes stale release code.
- postinstall verifies installed VERSION before completing.
- v2.2.1 hierarchy and multi-account report changes remain present.

## Environment limitation
Apple `pkgbuild` and `productbuild` are not available in this Linux build environment. The included macOS builder must be run on macOS to create the final `.pkg`.
