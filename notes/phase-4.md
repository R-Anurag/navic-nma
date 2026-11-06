# Phase 4: hardened receiver
Built: per-satellite state machine (no data / key verified / authenticated / stale / failed), Gauss-Newton PVT, trust policy, replay check, one `Receiver` class with modes naive / tesla / hardened.
Gate: clean scenario max error 8.1 m (< 10 m) at 1.5 m pseudorange noise, trust Authenticated; all three trust levels triggered by tests.
Deviation: a failed tag drops that satellite and alarms but doesn't by itself make the fix Untrusted, so the demo's "position holds" is true.
Skipped: galileo_adapter.py (no OSNMAlib), cross-constellation time comparison (both constellations are replayed together in A6, so it adds nothing here).
