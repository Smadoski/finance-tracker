# Finance Tracker development

This working copy was created from `FinanceTracker-v2.4.6.zip`. The original
archive remains unchanged in `../Oriiginal Files`.

## Run

```sh
./dev-start.sh
```

Open <http://127.0.0.1:8080>. Development data is written to `data/` inside
this working copy and is intentionally excluded from Git.

## Test

```sh
source .venv/bin/activate
pytest
```

The development launcher listens only on this Mac. Use the release service
scripts only when intentionally testing LAN or production deployment.

