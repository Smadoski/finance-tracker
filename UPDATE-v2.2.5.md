# Finance Tracker v2.2.5

Fixes the macOS package failure caused by non-executable package scripts.
- preinstall and postinstall forced to 0755 before pkgbuild
- executable permissions preserved in the release ZIP
- installer builder and shell scripts preserved as executable
- retains v2.2.4 authentication-preference persistence and all earlier v2.2.x changes
