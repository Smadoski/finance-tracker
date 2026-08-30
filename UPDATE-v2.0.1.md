# Finance Tracker v2.0.1

Maintenance release for Finance Tracker v2.0.

## Fixed

- Automatic ECB GBP/EUR exchange-rate updates now use the `certifi` CA certificate bundle explicitly.
- Fixes `SSL: CERTIFICATE_VERIFY_FAILED` on macOS Python installations whose default certificate store is incomplete.
- HTTPS certificate verification remains fully enabled.

## Update

After copying the v2.0.1 program files over v2.0 while preserving the `data` folder, activate the existing virtual environment and run:

```bash
cd /Applications/finance_tracker
source .venv/bin/activate
pip install -r requirements.txt
```

Then restart the Finance Tracker LaunchAgent.
