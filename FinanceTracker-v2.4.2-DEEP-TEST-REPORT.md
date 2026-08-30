# Finance Tracker v2.4.2 — Deep Test Report

Build base: v2.4.0; v2.4.1 deliberately not used.

PASS Python/module/test compilation
PASS all Jinja templates parse
PASS shell syntax
PASS service pytest: ......                                                                   [100%]
6 passed in 0.04s
PASS Quick Entry/type source contract
PASS transfer-pair deletion source contract
PASS receipt validation/cleanup service tests
PASS transaction edit route present
PASS user management/rate limiting source contract
PASS SQLite backup API source contract
PASS Keychain Dropbox storage and automatic upload source contract
PASS version/postinstall consistency

Limitation: Flask/Werkzeug are not installed in this build runtime, so HTTP tests cannot be executed here. A real tests/conftest.py fixture is included so the Flask tests can run on the macOS test host after installing requirements-dev.txt. Live Dropbox/Keychain calls also require macOS/network access.
