# Finance Tracker v2.4.5 — Final Deep Test Report

## Result

The v2.4.5 source release passes all tests that can be executed in this build environment.

## Passed

- ZIP/source structure and version consistency.
- Python compilation for app, modules and tests.
- All Jinja templates parse.
- All installer/service shell scripts pass syntax checking.
- Installer builder/preinstall/postinstall executable permissions are retained.
- 13 Flask-independent regression/service tests pass.
- Administrator recovery rejects direct non-loopback requests and reverse-proxied non-local client addresses.
- Credential enablement requires an active Administrator.
- Read Only enforcement and auth-version session invalidation remain present.
- Sign-safe transaction editing/reclassification remains present.
- Transfer pairing and zero-value transfer protection remain present.
- Receipt content validation, server-side Quick Entry receipt ownership and 15 MB request limit remain present.
- SQLite backup API remains present.
- Dropbox pending-upload retention protection and bounded retry backoff remain present.
- Dropbox token remains in macOS Keychain rather than finance.db.
- Preinstall targets stale Finance Tracker processes by application path/identity and does not kill arbitrary port-8080 listeners.
- Package builder creates a macOS dependency wheelhouse.
- Postinstall uses only the bundled wheelhouse (`--no-index --find-links`) for Python packages.
- Installer explicitly discovers common Homebrew Python locations as well as PATH.
- LaunchAgent bootstrap/kickstart failures are not ignored.
- Installer performs LaunchAgent + local HTTP health verification before returning success.

Service tests:
[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m                                                            [100%][0m
[32m[32m[1m13 passed[0m[32m in 0.06s[0m[0m

## Remaining environmental release gate

The complete Flask HTTP test suite cannot execute in this Linux build runtime because Flask/Werkzeug are not installed here. Those tests are included in the package and should be run on the Mac build/test host after dependencies are installed.

The generated `.pkg` is offline for Python package dependencies once built on the Mac, but it still requires a working Python 3 runtime on the target Mac. The installer now detects common Homebrew/system locations and fails clearly if Python 3 is unavailable.
