# Finance Tracker v2.4.3

Corrective security and transaction-integrity release.

- Enforces Read Only users across all write requests.
- Preserves the negative sign when editing uncategorised expenses.
- Recategorisation and bulk reclassification normalise signs to the destination category kind.
- Linked transfer rows remain protected from individual edit/reclassification.
- Protects the last active Administrator from disable/demotion/delete.
- Adds auth_version session invalidation after password/role/active changes.
- Quick Entry receipt ownership is server-side, not trusted from a hidden receipt path.
- Replacement receipt cleanup handles remove/replacement/error cases.
- Sets a 15 MB request/upload ceiling.
- Delegates account-balance calculation to the finance_tracker.accounts service implementation.
- Retains v2.4.2 SQLite backup, Keychain Dropbox token, automatic Dropbox upload, report sharing and receipt content validation.
