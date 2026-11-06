"""Run one (attack, severity, receiver mode, seed) scenario and score it."""
from dataclasses import dataclass

import numpy as np

from .attacks.toolkit import ATTACKS
from .receiver import trust as T
from .receiver.receiver import Receiver
from .sim.constellation import ecef_to_lla
from .sim.stream import World
from .time.clock import Clock
from .time.mock_server import MockRoughtimeServer

WRONG_M = 100.0   # a presented fix further than this from the truth counts as "fooled"
T_ATTACK = 300.0


@dataclass
class Result:
    metrics: dict
    fixes: list
    world: World
    receiver: Receiver


def run(attack=None, severity=0.0, mode="hardened", seed=0, cold=False, t_attack=T_ATTACK,
        duration=720.0, power_on=0.0) -> Result:
    w = World(seed, duration)
    ev = w.broadcast()
    ctx = {"clock": Clock(), "cold": cold, "t_attack": t_attack if attack else duration}
    if attack:
        ev = ATTACKS[attack](w, ev, severity, ctx)
    ev = [e for e in ev if e.time >= power_on]
    roots = None if ctx["cold"] else {k: r.root for k, r in w.roots.items()}
    rx = Receiver(mode, w.pubkeys, clock=ctx["clock"], time_server=MockRoughtimeServer(seed),
                  warm_roots=roots)
    fixes = rx.run(ev)
    t0 = ctx["t_attack"]
    post = [f for f in fixes if f.t >= t0] or fixes
    errs = [float(np.linalg.norm(f.pos - w.rx)) if f.pos is not None else None for f in post]
    presented = [f.pos is not None and f.trust in (T.AUTHENTICATED, T.UNCHECKED) for f in post]
    fooled = [p and e > WRONG_M for p, e in zip(presented, errs)]
    alarms = [a for a in rx.alarms if a[0] >= t0]
    flagged = [f.t for f in post if f.trust in (T.DEGRADED, T.UNTRUSTED)]
    first = min([a[0] for a in alarms] + flagged, default=None)
    first_auth = next((f.t - power_on for f in fixes if f.trust == T.AUTHENTICATED), None)
    shown = [e for p, e in zip(presented, errs) if p]
    m = {
        "attack": attack or "clean", "severity": severity, "mode": mode, "seed": seed,
        "detected": int(first is not None),
        "time_to_detect_s": round(first - t0, 1) if first is not None else "",
        "fooled_frac": round(float(np.mean(fooled)), 3),
        "max_presented_err_m": round(max(shown), 1) if shown else "",
        "median_presented_err_m": round(float(np.median(shown)), 2) if shown else "",
        "final_trust": post[-1].trust,
        # clock error while the receiver still vouches for itself (not yet Untrusted)
        "max_trusted_clock_err_s": round(max([abs(f.clock_error) for f in post if f.trust != T.UNTRUSTED],
                                             default=0.0), 3),
        "first_auth_fix_s": first_auth if first_auth is not None else "",
        "alarm_kinds": ";".join(sorted({a[1] for a in alarms})),
    }
    return Result(m, fixes, w, rx)


def lla(pos):
    return None if pos is None else tuple(float(x) for x in ecef_to_lla(pos))
