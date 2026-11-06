# Phase 1: TESLA core
Built: `tesla/keychain.py` (K(i)=SHA-256(K(i+1))[:128]), `verify.py` (hash down to nearest verified key, out-of-order ok, cached), `tags.py` (truncated HMAC-SHA-256, any L; accumulation), `rootkey.py` (Ed25519 over root + params), `safety.py` (local + uncertainty < disclosure).
Tests: RFC 4231 case 2 HMAC vector, chain relation, flipped bits in any key fail, wrong root fails, out-of-order disclosure, security condition.
Simplified vs OSNMA: no GST/alpha salt in the chain hash, no MACSEQ/ADKD, one tag per satellite per interval, root key sent whole (not split across DSM blocks), Ed25519 instead of ECDSA P-256 for Galileo too.
