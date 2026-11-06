import numpy as np

from nma.receiver import trust as T
from nma.receiver.auth_state import AUTHENTICATED, FAILED, NO_DATA, STALE, SatAuth
from nma.receiver.pvt import solve
from nma.scenario import run


def test_pvt_exact():
    rng = np.random.default_rng(0)
    truth = np.array([1.2e6, 6.0e6, 3.0e6])
    sats = rng.normal(0, 1, (7, 3))
    sats = 2.6e7 * sats / np.linalg.norm(sats, axis=1)[:, None]
    pr = np.linalg.norm(sats - truth, axis=1) + 1234.0
    pos, bias, rms = solve(sats, pr)
    assert np.linalg.norm(pos - truth) < 1e-3 and abs(bias - 1234.0) < 1e-3


def test_auth_state_machine():
    s = SatAuth(target_bits=80, max_age=100)
    assert s.state(0) == NO_DATA
    s.tag_ok("orbit", 40, 0)
    assert s.state(0) != AUTHENTICATED
    s.tag_ok("orbit", 40, 10)
    assert s.state(50) == AUTHENTICATED and s.state(200) == STALE
    s.tag_failed()
    assert s.state(20) == FAILED and not s.usable(20)


def test_clean_scenario_authenticated_under_10m():
    m = run(None, mode="hardened").metrics
    assert m["final_trust"] == T.AUTHENTICATED
    assert m["max_presented_err_m"] < 10
    assert m["fooled_frac"] == 0


def test_each_trust_level_reachable():
    assert run(None, mode="hardened").metrics["final_trust"] == T.AUTHENTICATED
    assert run("A7", 0.75, "hardened").metrics["final_trust"] == T.DEGRADED
    assert run("A6", 5.0, "hardened").metrics["final_trust"] == T.UNTRUSTED
