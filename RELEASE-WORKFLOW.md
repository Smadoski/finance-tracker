# Finance Tracker release workflow

The release record is GitHub source, tags and downloadable assets together. Building an installer locally is not a published release.

1. Inspect current GitHub main, tags and Releases, plus the latest installed/released version. Resolve discrepancies before selecting a baseline. Never reuse a released version number for different source.
2. Develop on a `codex/` feature/release branch based on the latest released source. Preserve all existing features unless their removal is explicitly approved.
3. Run the complete tests and migration checks on isolated copies. Record counts, browser checks, upgrade rehearsal and any unperformed live/device checks in the versioned test report.
4. Update VERSION, current README/release manifest and release/migration notes. Installer metadata reads VERSION. Historical release documents keep their original versions.
5. Commit source and documentation; build with the existing Finder-compatible installer builder. Inspect the expanded package against committed source and verify private data, secrets, caches and old build artifacts are excluded. Generate SHA-256 asset checksums.
6. Push the release branch and open a pull request. Verify its head commit and checks. Merge to main only when release/promotion is authorised; do not rewrite shared history or bypass required reviews.
7. Create the version tag on the exact released commit. Publish a GitHub Release containing the matching macOS installer, source ZIP, release/test notes and checksums.
8. Verify remote main/tag commits, release visibility and every asset's size/digest. Report the GitHub release URL and commit hash; confirm local Git status is clean.

Deployment over the live installation is a separate action and requires explicit authorisation. Publishing must never be reported as a tested live installation.

## Recovered history

The original 9 September 2026 v2.7.0 source was recovered from its preserved ZIP and committed/tagged before v2.8.0. The historical release includes that original ZIP. Its original installer was overwritten by the incorrectly numbered local fixes build and cannot be represented as an original artifact; use the updated v2.8.0 installer. The earlier planning stash and fixes branch were retained for audit/recovery.
