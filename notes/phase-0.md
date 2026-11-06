# Phase 0: repo setup
Built: repo layout, pinned `pyproject.toml`, `Makefile` (test / experiments / figures / demo / demo-html), `.venv` via uv.
Skipped: OSNMAlib install + its test vectors. The Galileo adapter is the plan's first scope cut, and Galileo is simulated with the Phase 1 library instead (plan's fallback). pandas dropped; stdlib `csv` covers it.
Open: run OSNMAlib's `icd_test_vectors.py` if real Galileo data is wanted later.
