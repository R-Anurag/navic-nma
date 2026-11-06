"""The receiver in three modes:

naive     - no authentication at all (today's civil receiver)
tesla     - TESLA checks on both constellations, trusts its own clock
hardened  - tesla + Roughtime bootstrap, clock-jump detection, replay check
"""
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from ..sim.navmsg import NavData
from ..sim.nma_message import NmaMessage
from ..sim.stream import SYSTEMS
from ..tesla.rootkey import verify_root
from ..tesla.safety import disclosure_time, key_not_yet_disclosed
from ..tesla.tags import check_tag
from ..tesla.verify import KeyVerifier
from ..time.clock import Clock
from ..time.roughtime_client import TimeRejected, query
from . import trust as T
from .auth_state import SatAuth
from .pvt import solve
from .replay_check import replay_suspected

DRIFT_BOUND = 2e-6  # assumed worst-case oscillator drift (s/s)


@dataclass
class Fix:
    t: float
    pos: np.ndarray | None
    n_used: int
    trust: str
    used: list
    alarms: list = field(default_factory=list)
    clock_error: float = 0.0


class Receiver:
    def __init__(self, mode, pubkeys, *, clock=None, time_server=None, warm_roots=None,
                 nominal_bound=1.0, replay_threshold=1.0, jump_bound=0.5, resync_every=30.0):
        assert mode in ("naive", "tesla", "hardened")
        self.mode, self.pubkeys = mode, pubkeys
        self.clock = clock or Clock()
        self.server = time_server
        self.nominal_bound, self.replay_threshold = nominal_bound, replay_threshold
        self.jump_bound, self.resync_every = jump_bound, resync_every
        self.verifiers = {k: KeyVerifier(r) for k, r in (warm_roots or {}).items()}
        self.sats = {}
        self.naive_eph = {}
        self.pending = defaultdict(list)
        self.keys_waiting = defaultdict(list)
        self.alarms, self.fixes = [], []
        self.time_alarm = False
        self.synced = mode != "hardened"
        self.last_sync = self.sync_radius = self.last_diff = None
        self._new_alarms = []

    # ---------- helpers ----------
    def alarm(self, t, kind, detail=""):
        a = (round(t, 3), kind, detail)
        self.alarms.append(a)
        self._new_alarms.append(a)

    def bound(self, t):
        if self.mode == "hardened" and self.synced:
            return self.sync_radius + DRIFT_BOUND * (t - self.last_sync)
        return self.nominal_bound

    def sat(self, system, prn):
        if (system, prn) not in self.sats:
            s = SYSTEMS[system]
            self.sats[(system, prn)] = SatAuth(s.target_bits, (s.delay + 3) * s.period)
        return self.sats[(system, prn)]

    # ---------- main entry ----------
    def run(self, events):
        for e in events:
            self.process(e)
        return self.fixes

    def process(self, e):
        if self.mode == "hardened":
            self._time_checks(e.time)
        getattr(self, "_" + e.kind)(e)

    # ---------- time ----------
    def _time_checks(self, t):
        diff = self.clock.now(t) - self.clock.oscillator(t)
        if self.last_diff is not None and abs(diff - self.last_diff) > self.jump_bound:
            self.alarm(t, "clock jump", f"{diff - self.last_diff:+.2f} s")
            self.time_alarm = True
        self.last_diff = diff
        if self.server and (not self.synced or t - self.last_sync >= self.resync_every):
            try:
                mid, rad = query(self.server, t)
            except TimeRejected as err:
                self.alarm(t, "signed time rejected", str(err))
                return
            local = self.clock.now(t)
            if self.synced and abs(local - mid) > rad + self.bound(t):
                self.alarm(t, "clock disagrees with signed time", f"{local - mid:+.2f} s")
                self.time_alarm = True
            self.clock.set_to(t, mid)
            self.last_diff = self.clock.now(t) - self.clock.oscillator(t)
            self.synced, self.last_sync, self.sync_radius = True, t, rad

    # ---------- messages ----------
    def _root(self, e):
        if self.mode == "naive":
            return
        r = e.root
        if not verify_root(self.pubkeys[e.system], r.root, r.params, r.signature):
            self.alarm(e.time, "root key signature", e.system)
            return
        if e.system not in self.verifiers:
            self.verifiers[e.system] = KeyVerifier(r.root)
            for j, key, t in self.keys_waiting.pop(e.system, []):
                self._key(e.system, j, key, t)

    def _nav(self, e):
        if e.nma is None or self.mode == "naive":
            if self.mode == "naive" and e.data:
                self.naive_eph[(e.system, e.prn)] = NavData.from_bytes(e.data).orbit
            return
        nma = NmaMessage.from_bytes(e.nma)
        if nma.key is not None:
            self._key(e.system, nma.key_index, nma.key, e.time)
        if e.data is None or nma.tag is None or not self.synced:
            return
        s, i = SYSTEMS[e.system], nma.interval
        local = self.clock.now(e.time)
        if not key_not_yet_disclosed(local, self.bound(e.time), disclosure_time(i, s.period, s.delay)):
            self.alarm(e.time, "late tag rejected", f"{e.system} {e.prn}")
            return
        item = (e.prn, NavData.from_bytes(e.data), nma.tag)
        v = self.verifiers.get(e.system)
        if v and i in v.known:
            self._check(e.system, i, v.known[i], item, e.time)
        else:
            self.pending[(e.system, i)].append(item)

    def _key(self, system, j, key, t):
        v = self.verifiers.get(system)
        if v is None:
            self.keys_waiting[system].append((j, key, t))
            return
        if not v.verify(j, key):
            self.alarm(t, "key chain check failed", f"{system} K{j}")
            return
        for (sys_, prn), sa in self.sats.items():
            if sys_ == system:
                sa.key_verified = True
        for item in self.pending.pop((system, j), []):
            self._check(system, j, key, item, t)

    def _check(self, system, i, key, item, t):
        prn, nav, tag = item
        s, sa = SYSTEMS[system], self.sat(system, prn)
        sa.key_verified = True
        if check_tag(key, nav.to_bytes(), prn, i, tag, s.tag_bits):
            sa.tag_ok(nav.orbit, s.tag_bits, t)
        else:
            self.alarm(t, "tag failed, satellite dropped", f"{system} {prn}")
            sa.tag_failed()

    def _obs(self, e):
        local = self.clock.now(e.time)
        if self.mode == "hardened" and self.synced and replay_suspected(local, e.t_signal, self.replay_threshold):
            if not self.time_alarm:
                self.alarm(e.time, "replay suspected", f"signal time off by {local - e.t_signal:+.2f} s")
            self.time_alarm = True
        if self.mode == "naive":
            orbits = {k: o for k, o in self.naive_eph.items() if k in e.pr}
        else:
            orbits = {k: sa.orbit for k, sa in self.sats.items() if k in e.pr and sa.usable(e.time)}
        keys = sorted(orbits)
        pos = None
        if len(keys) >= 4:
            sp = np.array([orbits[k].ecef(e.t_signal) for k in keys])
            pos, _, _ = solve(sp, np.array([e.pr[k] for k in keys]))
        trust = T.trust_level(self.mode, len(keys), self.synced and not self.time_alarm)
        if len(keys) < 4:
            pos = None
        self.fixes.append(Fix(e.time, pos, len(keys), trust, keys, self._new_alarms,
                              local - e.time))
        self._new_alarms = []
