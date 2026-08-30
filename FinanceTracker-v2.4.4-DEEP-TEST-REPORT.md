# Finance Tracker v2.4.4 — Deep Test Report

PASS: Python/module/test compilation
PASS: Jinja templates
PASS: shell syntax
PASS: Flask-independent service/regression tests
PASS: active Administrator credential guard
PASS: login/setup recovery logic
PASS: pip dependency failures no longer ignored
PASS: broad port-8080 kill logic removed
PASS: Dropbox retry tracking
PASS: zero transfer rejection
PASS: transaction/valuation validation
PASS: version/postinstall consistency

Service tests:
[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m                                                               [100%][0m
[32m[32m[1m10 passed[0m[32m in 0.05s[0m[0m

HTTP Flask tests are included but cannot execute in this build runtime because Flask/Werkzeug are unavailable.

Offline installer note: a network-independent macOS package requires a macOS-compatible wheelhouse prepared on the Mac build host.
