# Finance Tracker v2.3.1

## Release-blocking fixes

### No-login mode
- Authentication OFF now bypasses `login_required` and `admin_required` directly.
- No session and no user row are required when authentication is disabled.
- `/login` and `/setup` redirect to Dashboard while no-login mode is active.
- `auth_required=0` is enforced at application startup as well as by the macOS installer.
- Settings cannot re-enable credentials in this release; the checkbox is shown disabled.
- Quick Entry and the main application therefore use Tailnet/Tailscale as the access boundary.

### Category hierarchy
- Parent changes use one database helper: `save_category_parent`.
- The helper validates the relationship, writes `parent_id`, commits, reads it back, and fails if persistence cannot be confirmed.
- Categories displays Current Parent and a Save parent control.
- Reports read the same stored `parent_id` relationship.

This release retains all reporting, installer and data-protection changes from v2.3.0.
