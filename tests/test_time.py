import pytest

from nma.receiver.receiver import Receiver
from nma.sim.stream import World
from nma.time.clock import Clock
from nma.time.mock_server import MockRoughtimeServer
from nma.time.roughtime_client import TimeRejected, new_nonce, query, verify_response


def test_valid_response():
    s = MockRoughtimeServer(seed=1, radius=0.5)
    mid, rad = query(s, 1000.0)
    assert abs(mid - 1000.0) <= 0.5 and rad >= 0.5


def test_forged_response_rejected():
    s, evil = MockRoughtimeServer(seed=1), MockRoughtimeServer(seed=2)
    nonce = new_nonce()
    body, sig = evil.respond(nonce, 5000.0)
    with pytest.raises(TimeRejected, match="signature"):
        verify_response(s.public_key, nonce, body, sig)


def test_replayed_response_rejected():
    s = MockRoughtimeServer(seed=1)
    old_nonce = new_nonce()
    body, sig = s.respond(old_nonce, 100.0)
    with pytest.raises(TimeRejected, match="nonce"):
        verify_response(s.public_key, new_nonce(), body, sig)


def test_clock_attack_hook():
    c = Clock(drift_ppm=0)
    c.attack = lambda t: -5.0 if t > 10 else 0.0
    assert c.now(5) == 5 and c.now(20) == 15 and c.oscillator(20) == 20


def test_uncertainty_bound_feeds_security_condition():
    w = World(0)
    r = Receiver("hardened", w.pubkeys, time_server=MockRoughtimeServer(0, radius=0.5))
    r._time_checks(10.0)
    assert r.synced and 0.5 <= r.bound(10.0) < 0.6
    assert r.bound(1010.0) > r.bound(10.0)  # widens with drift until resync
