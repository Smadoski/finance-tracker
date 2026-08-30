# Finance Tracker v2.3.1 — Deep Acceptance Test Report

- Python compilation: PASS
- All Jinja templates parse: PASS
- AST parse: PASS
- Petrol -> Motoring save + DB readback: PASS
- Hierarchy validation (self/nesting/kind): PASS
- Report hierarchy sees Motoring -> Fuel/Petrol: PASS
- Remove parent + DB readback: PASS
- No-login hard-off + route bypass source assertions: PASS
- Installer auth_required=0 write + verification: PASS
- Settings cannot re-enable credentials: PASS
- Version/package verification: PASS
- ZIP integrity + executable permissions: PASS

Limitation: the build environment does not contain Flask/Werkzeug, so a real HTTP test-client session cannot be launched here. To compensate, authentication gates were refactored so the no-login decision is explicit and independently source-asserted, and category persistence was extracted into a pure SQLite helper and executed against an isolated database.
