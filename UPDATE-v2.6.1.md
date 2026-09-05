# Finance Tracker v2.6.1 — navigation regression correction

Baseline: released v2.6.0. No v2.7.0 planning or forecasting functionality.

## Cause and correction

The responsive redesign put navigation inside a closed native `details` element
and hid its summary at desktop widths. CSS `display:flex` on the child navigation
did not open the native disclosure, leaving desktop users without a menu.

- The shared navigation is open in server-rendered HTML, including without JavaScript.
- At 901px and above, every authorised destination is visible in a wrapping desktop bar.
- At 900px and below, a visible native `☰ Menu` disclosure opens a two-column menu.
- A matching media-query listener synchronises disclosure state when resizing or
  rotating; mobile navigation closes after selection, on Escape, and on page return.
- Active destinations have `aria-current="page"` and a visible highlight.
- Destination names/order, administrator-only links, Sign out and Read Only badges
  are preserved. One menu tree serves all widths.
- The header stays in normal document flow so an expanded menu cannot cover content.

The v2.6.0 cards, collapsible forms, Settings/Status split and other responsive
improvements are retained. Application runtime changes are limited to the shared
navigation template and CSS. No Python application code, financial calculations,
schema, scheduling, authentication or installer logic has changed. Other changes
are version metadata, release documentation and regression tests.

## Upgrade

Use the established macOS PKG process over v2.6.0. A temporary v2.6.0 fixture was
upgraded and all 12 application tables, schema and configuration remained intact.
Actual Apple Installer/LaunchAgent upgrade on the live installation remains an
on-machine acceptance check; it was not run as part of destructive live testing.
