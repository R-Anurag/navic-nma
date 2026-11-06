# Phase 3: authenticated time
Built: `time/clock.py` (offset, drift, attacker hook, separate free-running oscillator), `mock_server.py` (Ed25519-signed nonce+midpoint+radius with the draft's context string), `roughtime_client.py` (rejects bad signature and nonce mismatch).
Policy: hardened receiver ignores tags until it has signed time; re-queries every 30 s; alarms if local clock disagrees beyond radius + drift bound; oscillator check flags jumps > 0.5 s between events.
Skipped: real public Roughtime server and network I/O, delegation certificates, Merkle batching, tag/value wire encoding (plan's fallback: local mock).
Open: confirm current draft-ietf-ntp-roughtime version and a reachable server; check for ISRO NMA publications after Oct 2023.
