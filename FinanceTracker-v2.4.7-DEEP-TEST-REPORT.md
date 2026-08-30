# Finance Tracker v2.4.7 deep test report

Date: 30 August 2026

## Result

Finance Tracker v2.4.7 passed the complete automated suite and local live-server
verification in an isolated development environment using Python 3.11.4.

## Automated verification

- 26 pytest tests passed.
- All application, service and test Python files compiled successfully.
- Shell syntax validation passed for startup, service, backup and packaging
  scripts.
- New regression coverage verifies:
  - malformed Edit Account currency input is rejected without data changes;
  - malformed pending-entry amounts are rejected without losing the pending item;
  - Quick Entry rejects pension, other-asset and liability accounts server-side;
  - PDF download responses remain attachments;
  - iOS share-mode PDF responses are served inline;
  - the rendered interface contains the iOS native-PDF routing logic.

## Live verification

- Waitress started successfully on an isolated loopback port.
- The dashboard returned a successful HTTP response.
- The inline net-worth report returned a valid one-page PDF.
- The verification server was stopped after testing.

## iPhone sharing note

The failing JavaScript-generated file-share approach has been replaced on iPhone
and iPad with Safari's inline PDF viewer, from which the platform's native Share
control is available. The server response and device-routing behavior are covered
by automated tests. Final confirmation of the visible iOS Share Sheet requires a
physical iPhone or iPad and should be included in live acceptance testing.

## Data safety

Testing used only the isolated development database. No live Finance Tracker
database, receipt collection, credentials or backup settings were accessed.
