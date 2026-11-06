"""World model + broadcast(): a time-ordered stream of what an antenna near Delhi hears."""
import random
from dataclasses import dataclass, field

import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ..tesla.keychain import KeyChain
from ..tesla.rootkey import sign_root
from ..tesla.tags import make_tag
from .constellation import C, DELHI_IGI, galileo_satellites, lla_to_ecef, navic_satellites, visible
from .navmsg import NavData
from .nma_message import NmaMessage, RootKeyMessage


@dataclass(frozen=True)
class System:
    name: str
    period: float      # TESLA interval length (s)
    delay: int         # key disclosure delay in intervals
    tag_bits: int
    target_bits: int   # verified tag bits before a satellite counts as authenticated


# NavIC: ISRO 2023 proposal, L5/S chain (48 s frame, key disclosed 96 s later, TTFAF 144 s).
# Galileo: OSNMA, 30 s subframe, key of the previous subframe, 40-bit tags accumulated to 80.
SYSTEMS = {
    "NAVIC": System("NAVIC", 48.0, 2, 32, 32),
    "GALILEO": System("GALILEO", 30.0, 1, 40, 80),
}
OBS_PERIOD = 6.0
ROOT_EVERY = 6          # root key repeats every N intervals (modelled: real systems spread it over minutes)
RX_CLOCK_BIAS_M = 3000.0
PR_SIGMA_M = 1.5


@dataclass
class Event:
    time: float                    # true arrival time at the antenna
    kind: str                      # 'nav' | 'root' | 'obs'
    system: str = ""
    prn: int = 0
    data: bytes | None = None      # NavData bytes
    nma: bytes | None = None       # NmaMessage bytes
    root: RootKeyMessage | None = None
    t_signal: float = 0.0          # time the signal claims (time of week)
    pr: dict = field(default_factory=dict)   # (system, prn) -> pseudorange, m

    def sort_key(self):
        return (self.time, {"root": 0, "nav": 1, "obs": 2}[self.kind], self.system, self.prn)


class World:
    def __init__(self, seed=0, duration=720.0, rx_lla=DELHI_IGI):
        self.seed, self.duration = seed, duration
        self.rng = random.Random(seed)
        self.rx_lla = rx_lla
        self.rx = lla_to_ecef(*rx_lla)
        self.sats = navic_satellites() + visible(galileo_satellites(), self.rx, 0, duration)
        self.chains, self.signers, self.pubkeys, self.roots = {}, {}, {}, {}
        for name, s in SYSTEMS.items():
            n = int(duration / s.period) + s.delay + 10
            self.chains[name] = KeyChain(n, seed=self.rng.randbytes(16))
            sk = Ed25519PrivateKey.from_private_bytes(self.rng.randbytes(32))
            self.signers[name], self.pubkeys[name] = sk, sk.public_key()
            params = params_of(s)
            self.roots[name] = RootKeyMessage(name, self.chains[name].root, params,
                                              sign_root(sk, self.chains[name].root, params))

    def nav_event(self, sat, i, *, data_orbit=None, tag_key=None, key_override=None, t=None):
        s = SYSTEMS[sat.system]
        chain = self.chains[sat.system]
        nav = NavData(sat.system, sat.prn, i, data_orbit or sat.orbit)
        tag = make_tag(tag_key or chain.key(i), nav.to_bytes(), sat.prn, i, s.tag_bits)
        j = i - s.delay
        key = key_override if key_override is not None else (chain.key(j) if j >= 1 else None)
        nma = NmaMessage(sat.prn, i, tag, s.tag_bits, j if key else None, key)
        when = i * s.period if t is None else t
        return Event(when, "nav", sat.system, sat.prn, nav.to_bytes(), nma.to_bytes(), t_signal=i * s.period)

    def broadcast(self, rx=None, sats=None, seed_offset=0):
        """Every event the antenna at `rx` hears in [0, duration]."""
        rx = self.rx if rx is None else rx
        sats = self.sats if sats is None else sats
        noise = np.random.default_rng(self.seed * 1000 + seed_offset)
        ev = []
        for name, s in SYSTEMS.items():
            n = int(self.duration // s.period)
            for i in range(0, n + 1, ROOT_EVERY):
                ev.append(Event(i * s.period, "root", name, root=self.roots[name], t_signal=i * s.period))
            for sat in (x for x in sats if x.system == name):
                ev += [self.nav_event(sat, i) for i in range(1, n + 1)]
        for k in range(int(self.duration // OBS_PERIOD) + 1):
            t = k * OBS_PERIOD
            ev.append(Event(t, "obs", t_signal=t, pr=pseudoranges(sats, rx, t, noise)))
        return sorted(ev, key=Event.sort_key)


def params_of(s: System) -> dict:
    return {"system": s.name, "period": s.period, "delay": s.delay, "tag_bits": s.tag_bits}


def pseudoranges(sats, rx, t, noise):
    return {(s.system, s.prn): float(np.linalg.norm(s.orbit.ecef(t) - rx) + RX_CLOCK_BIAS_M
                                     + noise.normal(0, PR_SIGMA_M)) for s in sats}


def broadcast(t0=0.0, duration=600.0, seed=0):
    """Plan API: yields (time, satellite, bits) for every nav message."""
    for e in World(seed, t0 + duration).broadcast():
        if e.kind == "nav" and e.time >= t0:
            yield e.time, (e.system, e.prn), e.data + e.nma
