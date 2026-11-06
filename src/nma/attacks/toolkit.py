"""Attacker toolkit A1-A8. Each attack transforms the broadcast stream (and/or the
receiver clock via ctx) and takes a `severity` knob. Software only - nothing here
transmits anything.
"""
import dataclasses
import random

import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ..sim.constellation import gps_satellites, lla_to_ecef, visible
from ..sim.navmsg import NavData
from ..sim.nma_message import NmaMessage, RootKeyMessage
from ..sim.stream import SYSTEMS, Event, World, params_of, pseudoranges
from ..tesla.keychain import KeyChain
from ..tesla.rootkey import sign_root
from ..tesla.tags import make_tag

RECORDING_SITE = (28.4595, 77.0266, 220.0)   # meaconing antenna, Gurugram (~13 km from IGI)
FAKE_SITE = (28.40, 76.85, 220.0)            # where A7 wants the aircraft to think it is
FORGE_DELAY = 1.0                            # A4: forged tags sent this long after key disclosure


def shifted(orbit, km):
    """Move a satellite `km` along its orbit (ephemeris tampering)."""
    return dataclasses.replace(orbit, m0=orbit.m0 + km * 1000 / orbit.a)


def tamper_data(e, km):
    nav = NavData.from_bytes(e.data)
    return dataclasses.replace(e, data=dataclasses.replace(nav, orbit=shifted(nav.orbit, km)).to_bytes())


def after(ev, t, pred=lambda e: True):
    return [i for i, e in enumerate(ev) if e.time >= t and pred(e)]


def resort(ev):
    return sorted(ev, key=Event.sort_key)


# A1 ------------------------------------------------------------------------
def a1_tamper(w: World, ev, severity, ctx):
    """Edit NavIC ephemeris bits by `severity` km; tags are left as they were."""
    for i in after(ev, ctx["t_attack"], lambda e: e.kind == "nav" and e.system == "NAVIC"):
        ev[i] = tamper_data(ev[i], severity)
    return ev


# A2 ------------------------------------------------------------------------
def a2_forged_key(w, ev, severity, ctx):
    """Replace a fraction `severity` of disclosed NavIC keys with random bytes."""
    rng = random.Random(w.seed + 2)
    for i in after(ev, ctx["t_attack"], lambda e: e.kind == "nav" and e.system == "NAVIC"):
        m = NmaMessage.from_bytes(ev[i].nma)
        if m.key and rng.random() < severity:
            ev[i] = dataclasses.replace(ev[i], nma=dataclasses.replace(m, key=rng.randbytes(16)).to_bytes())
    return ev


# A3 ------------------------------------------------------------------------
def a3_fake_root(w, ev, severity, ctx):
    """From cold start: attacker's own NavIC chain, root signed with the attacker's
    key, and tampered ephemeris that carries valid tags under that chain."""
    ctx["cold"], ctx["t_attack"] = True, 0.0
    s = SYSTEMS["NAVIC"]
    chain = KeyChain(len(w.chains["NAVIC"]) - 1, seed=w.seed + 333)
    evil = Ed25519PrivateKey.from_private_bytes(random.Random(w.seed + 3).randbytes(32))
    root = RootKeyMessage("NAVIC", chain.root, params_of(s), sign_root(evil, chain.root, params_of(s)))
    sats = {(x.system, x.prn): x for x in w.sats}
    out = []
    for e in ev:
        if e.system != "NAVIC":
            out.append(e)
        elif e.kind == "root":
            out.append(dataclasses.replace(e, root=root))
        elif e.kind == "nav":
            i = NmaMessage.from_bytes(e.nma).interval
            j = i - s.delay
            sat = sats[("NAVIC", e.prn)]
            orbit = shifted(sat.orbit, severity)
            nav = NavData("NAVIC", e.prn, i, orbit).to_bytes()
            tag = make_tag(chain.key(i), nav, e.prn, i, s.tag_bits)
            key = chain.key(j) if j >= 1 else None
            m = NmaMessage(e.prn, i, tag, s.tag_bits, j if key else None, key)
            out.append(dataclasses.replace(e, data=nav, nma=m.to_bytes()))
        else:
            out.append(e)
    return out


# A4 ------------------------------------------------------------------------
def forge_late(w, ev, t_from, km, systems=("NAVIC", "GALILEO")):
    """Wait for each key to be disclosed, then send tampered data with a valid tag
    for the old interval FORGE_DELAY s later. The on-time message keeps only its key."""
    sats = {(x.system, x.prn): x for x in w.sats}
    out = []
    for e in ev:
        if e.kind == "nav" and e.system in systems and e.time >= t_from:
            s = SYSTEMS[e.system]
            m = NmaMessage.from_bytes(e.nma)
            out.append(dataclasses.replace(e, data=None, nma=dataclasses.replace(m, tag=None).to_bytes()))
            late = (m.interval + s.delay) * s.period + FORGE_DELAY
            if late <= w.duration:
                sat = sats[(e.system, e.prn)]
                f = w.nav_event(sat, m.interval, data_orbit=shifted(sat.orbit, km), t=late)
                fm = NmaMessage.from_bytes(f.nma)
                out.append(dataclasses.replace(f, nma=dataclasses.replace(fm, key=None).to_bytes()))
        else:
            out.append(e)
    return resort(out)


def a4_old_key(w, ev, severity, ctx):
    """Receiver clock runs `severity` s slow (unknown to it); attacker re-uses
    disclosed keys to sign 10 km-shifted ephemeris."""
    ctx["clock"].offset -= severity
    return forge_late(w, ev, ctx["t_attack"], 10.0)


# A5 ------------------------------------------------------------------------
def a5_clock_drag(w, ev, severity, ctx):
    """Drag the receiver clock back by `severity` s over 30 s, then run A4."""
    t0 = ctx["t_attack"]
    ctx["clock"].attack = lambda t: -severity * min(max((t - t0) / 30.0, 0.0), 1.0)
    return forge_late(w, ev, t0 + 30.0, 10.0)


# A6 ------------------------------------------------------------------------
def a6_replay(w, ev, severity, ctx):
    """Record real signals at RECORDING_SITE, rebroadcast them `severity` s late."""
    t0, d = ctx["t_attack"], severity
    rec = w.broadcast(rx=lla_to_ecef(*RECORDING_SITE), seed_offset=1)
    live = [e for e in ev if e.time < t0]
    replay = [dataclasses.replace(e, time=e.time + d) for e in rec if t0 <= e.time + d <= w.duration]
    return resort(live + replay)


# A7 ------------------------------------------------------------------------
def a7_downgrade(w, ev, severity, ctx):
    """Jam a fraction `severity` of authenticated satellites and inject unauthenticated
    GPS signals that place the receiver at FAKE_SITE."""
    t0 = ctx["t_attack"]
    rng = random.Random(w.seed + 7)
    keys = sorted((s.system, s.prn) for s in w.sats)
    jammed = set(rng.sample(keys, round(severity * len(keys))))
    fake = lla_to_ecef(*FAKE_SITE)
    gps = visible(gps_satellites(), fake, 0, w.duration)
    noise = np.random.default_rng(w.seed + 77)
    out = []
    for e in ev:
        if e.time < t0:
            out.append(e)
        elif e.kind == "nav" and (e.system, e.prn) in jammed:
            continue
        elif e.kind == "obs":
            pr = {k: v for k, v in e.pr.items() if k not in jammed}
            pr.update(pseudoranges(gps, fake, e.t_signal, noise))
            out.append(dataclasses.replace(e, pr=pr))
        else:
            out.append(e)
    for k in range(int(t0 // 30), int(w.duration // 30) + 1):
        for s in gps:
            if k * 30 >= t0:
                out.append(Event(k * 30.0, "nav", "GPS", s.prn, NavData("GPS", s.prn, k, s.orbit).to_bytes(), None, t_signal=k * 30.0))
    return resort(out)


# A8 ------------------------------------------------------------------------
def a8_bruteforce(tag_bits, guesses, accumulate=1, seed=0):
    """Guess `accumulate` random tags per forgery; returns the number of forgeries accepted."""
    rng = random.Random(seed)
    key = KeyChain(1, seed=seed).key(1)
    hits = 0
    for g in range(guesses):
        hits += all(rng.getrandbits(tag_bits) == make_tag(key, b"fake", 1, g * accumulate + a, tag_bits)
                    for a in range(accumulate))
    return hits


ATTACKS = {
    "A1": a1_tamper, "A2": a2_forged_key, "A3": a3_fake_root, "A4": a4_old_key,
    "A5": a5_clock_drag, "A6": a6_replay, "A7": a7_downgrade,
}
