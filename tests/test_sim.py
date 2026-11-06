import hashlib

import numpy as np

from nma.sim.constellation import DELHI_IGI, ecef_to_lla, lla_to_ecef
from nma.sim.navmsg import NavData
from nma.sim.nma_message import NmaMessage
from nma.sim.stream import SYSTEMS, World, broadcast
from nma.tesla.tags import check_tag
from nma.tesla.verify import KeyVerifier


def digest(seed):
    h = hashlib.sha256()
    for t, sat, bits in broadcast(0, 600, seed=seed):
        h.update(repr((t, sat)).encode() + bits)
    return h.hexdigest()


def test_stream_is_reproducible():
    assert digest(1) == digest(1)
    assert digest(1) != digest(2)


def test_lla_roundtrip():
    lat, lon, h = ecef_to_lla(lla_to_ecef(*DELHI_IGI))
    assert np.allclose((lat, lon, h), DELHI_IGI, atol=1e-6)


def test_constellation_in_view():
    w = World(0)
    assert sum(s.system == "NAVIC" for s in w.sats) == 3
    assert 6 <= sum(s.system == "GALILEO" for s in w.sats) <= 10


def test_every_message_authenticates():
    w = World(0, 600)
    verifiers = {k: KeyVerifier(c.root) for k, c in w.chains.items()}
    n = 0
    for e in w.broadcast():
        if e.kind != "nav":
            continue
        m = NmaMessage.from_bytes(e.nma)
        nav = NavData.from_bytes(e.data)
        key = w.chains[e.system].key(m.interval)
        assert verifiers[e.system].verify(m.interval, key)
        assert check_tag(key, e.data, nav.prn, m.interval, m.tag, SYSTEMS[e.system].tag_bits)
        if m.key:
            assert verifiers[e.system].verify(m.key_index, m.key)
        n += 1
    assert n > 100


def test_nma_message_roundtrip():
    m = NmaMessage(10, 7, 0xDEADBEEF, 32, 5, bytes(range(16)))
    assert NmaMessage.from_bytes(m.to_bytes()) == m
    assert m.auth_bits == 160
