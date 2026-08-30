# Finance Tracker v2.4.3 — Deep Test Report

PASS: Python compilation
PASS: finance_tracker module compilation
PASS: pytest module compilation
PASS: all Jinja templates parse
PASS: installer/service shell syntax
PASS: Flask-independent regression/service tests
PASS: Read Only write enforcement present
PASS: auth_version session invalidation present
PASS: sign-safe uncategorised edit and recategorisation logic present
PASS: last active Administrator protection present
PASS: server-side Quick Entry receipt ownership present
PASS: 15 MB upload/request ceiling
PASS: account-balance service delegation
PASS: VERSION/postinstall consistency

Service tests:
[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m                                                                 [100%][0m
[32m[32m[1m8 passed[0m[32m in 0.05s[0m[0m

HTTP Flask test-client tests are included for Read Only enforcement and uncategorised expense editing. This build runtime does not have Flask/Werkzeug installed, so those HTTP tests must be executed on the macOS test host with requirements-dev.txt.
