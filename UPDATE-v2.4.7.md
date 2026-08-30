# Finance Tracker v2.4.7

This corrective release retains the v2.4.6 database schema and requires no
data migration.

## Corrections

- Editing an account with a malformed currency now shows a validation message
  without changing the account or returning a server error.
- Posting a pending Quick Entry now rejects malformed or zero amounts without
  losing the pending item.
- Quick Entry now enforces the same transaction-capable account types on the
  server as the account selector does in the interface.
- On iPhone and iPad, Share opens the generated report inline in Safari's native
  PDF viewer. Use Safari's Share control to open the genuine iOS Share Sheet.
  Desktop browsers retain direct file sharing where supported and otherwise
  download the PDF.
- Generated Python and pytest caches are excluded from the release archive.

## Upgrade

Back up the live Finance Tracker data, stop the service, install the new release
and restart. Existing accounts, transactions, settings, receipts and users are
preserved.
