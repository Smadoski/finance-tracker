# Finance Tracker v2.4.6 - Deep Test Report

Source: user-supplied `FinanceTracker-v2.4.5-build-bugfixed.zip`.

PASS - ZIP integrity
PASS - Claude five-fix source indicators
PASS - VERSION/postinstall promoted to 2.4.6
PASS - Python compilation
PASS - Jinja parsing
PASS - shell syntax
PASS - v2.4.5 offline installer and health verification retained
PASS - Dropbox retry/backoff retained
PASS - local Administrator recovery guard retained

Regression tests:
[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m                                                            [100%][0m
[32m[32m[1m13 passed[0m[32m in 0.07s[0m[0m
Spreadsheet runtime warmup failed during python startup
Traceback (most recent call last):
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/patches/warm_spreadsheet_runtime_on_startup.py", line 26, in warm_spreadsheet_runtime_on_startup
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/spreadsheet_warmup.py", line 772, in warm_spreadsheet_runtime
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/rpc/connection.py", line 37, in get_or_create_client
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/rpc/daemon.py", line 124, in start_daemon
TimeoutError: Timed out waiting for artifact tool daemon socket. Set ARTIFACT_TOOL_RPC_DAEMON_STARTUP_TIMEOUT_S=<seconds> to increase the limit.

Known outstanding: native iPhone/iOS report sharing remains unresolved and is not claimed as fixed in v2.4.6.

A complete macOS/iOS end-to-end test remains an environment-specific acceptance test.
