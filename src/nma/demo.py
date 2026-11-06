"""The 5-step live demo (plan, Phase 7).

python -m nma.demo               terminal walkthrough
python -m nma.demo --html FILE   self-contained interactive page (works offline)
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np

from .attacks.toolkit import RECORDING_SITE
from .scenario import T_ATTACK, run
from .sim.constellation import DELHI_IGI, lla_to_ecef

STEPS = [
    dict(id="clean", attack=None, sev=0, left="naive", right="hardened", range_km=0.1,
         title="Clean sky", ask="Both receivers agree on the true position.",
         say="No attacker. The hardened receiver reaches an authenticated fix 90 s after switch-on "
             "(Galileo first, NavIC joins at 144 s, as in ISRO's proposal)."),
    dict(id="tamper", attack="A1", sev=50, left="naive", right="hardened", range_km=4,
         title="A1 Data tampering", ask="Attacker edits NavIC ephemeris bits at T+300 s.",
         say="The naive receiver jumps kilometres with no warning. The hardened receiver buffers the "
             "data until the key is disclosed 96 s later, sees the tags fail, drops the three NavIC "
             "satellites and holds position on Galileo."),
    dict(id="drag", attack="A5", sev=10, left="tesla", right="hardened", range_km=2,
         title="A5 Clock drag", ask="Attacker drags the receiver clock back 10 s, then reuses disclosed keys.",
         say="TESLA alone trusts its own clock, so forged tags look 'early' and pass: fooled. "
             "The hardened receiver's oscillator and signed time both disagree with the dragged clock "
             "and it goes Untrusted."),
    dict(id="replay-long", attack="A6", sev=5, left="tesla", right="hardened", range_km=16,
         title="A6 Replay, 5 s", ask="Signals recorded in Gurugram are rebroadcast 5 s late.",
         say="Every MAC is genuine, so TESLA alone follows the replay to Gurugram. Signed time says the "
             "signal is 5 s old: the hardened receiver flags it at once."),
    dict(id="replay-short", attack="A6", sev=0.3, left="tesla", right="hardened", range_km=16,
         title="A6 Replay, 0.3 s", ask="Same replay with only 0.3 s delay.",
         say="Expected loss. 0.3 s is inside the ~1 s uncertainty of signed internet time, so the "
             "hardened receiver is fooled too. Closing this gap needs spreading-code authentication "
             "or a better clock."),
]


def enu_km(pos, ref_ecef, lat, lon):
    lat, lon = np.radians(lat), np.radians(lon)
    d = pos - ref_ecef
    e = -np.sin(lon) * d[0] + np.cos(lon) * d[1]
    n = -np.sin(lat) * np.cos(lon) * d[0] - np.sin(lat) * np.sin(lon) * d[1] + np.cos(lat) * d[2]
    return round(float(e) / 1000, 4), round(float(n) / 1000, 4)


def sky(w):
    lat, lon = np.radians(DELHI_IGI[0]), np.radians(DELHI_IGI[1])
    out = []
    for s in w.sats:
        d = s.orbit.ecef(T_ATTACK) - w.rx
        e = -np.sin(lon) * d[0] + np.cos(lon) * d[1]
        n = -np.sin(lat) * np.cos(lon) * d[0] - np.sin(lat) * np.sin(lon) * d[1] + np.cos(lat) * d[2]
        u = np.cos(lat) * np.cos(lon) * d[0] + np.cos(lat) * np.sin(lon) * d[1] + np.sin(lat) * d[2]
        out.append({"key": f"{s.system}-{s.prn}", "name": s.name, "sys": s.system,
                    "az": round(float(np.degrees(np.arctan2(e, n))) % 360, 1),
                    "el": round(float(np.degrees(np.arctan2(u, np.hypot(e, n)))), 1)})
    return out


def receiver_track(res, w):
    ref = w.rx
    track = []
    for f in res.fixes:
        en = enu_km(f.pos, ref, *DELHI_IGI[:2]) if f.pos is not None else None
        err = round(float(np.linalg.norm(f.pos - w.rx)), 1) if f.pos is not None else None
        track.append([f.t, en, err, f.trust, [f"{k[0]}-{k[1]}" for k in f.used]])
    alarms = [[a[0], a[1], a[2]] for a in res.receiver.alarms]
    return {"mode": res.metrics["mode"], "track": track, "alarms": alarms, "metrics": res.metrics}


def build():
    data = []
    for s in STEPS:
        L, R = run(s["attack"], s["sev"], s["left"]), run(s["attack"], s["sev"], s["right"])
        rec = enu_km(lla_to_ecef(*RECORDING_SITE), L.world.rx, *DELHI_IGI[:2])
        data.append({**{k: s[k] for k in ("id", "title", "ask", "say", "range_km")},
                     "attack_t": T_ATTACK if s["attack"] else None,
                     "recording": rec if s["attack"] == "A6" else None,
                     "sky": sky(L.world), "left": receiver_track(L, L.world),
                     "right": receiver_track(R, R.world)})
    return data


def terminal():
    colors = {"Authenticated": "\033[32m", "Degraded": "\033[33m", "Untrusted": "\033[31m", "Unchecked": "\033[90m"}
    names = {"naive": "Naive receiver", "tesla": "TESLA only", "hardened": "Hardened"}
    t0 = time.time()
    for i, s in enumerate(STEPS, 1):
        print(f"\n\033[1mStep {i}: {s['title']}\033[0m  {s['ask']}")
        for mode in (s["left"], s["right"]):
            m = run(s["attack"], s["sev"], mode).metrics
            c = colors[m["final_trust"]]
            err = m["max_presented_err_m"]
            err = f"{err / 1000:.2f} km" if err != "" and err >= 1000 else (f"{err} m" if err != "" else "no fix shown")
            print(f"  {names[mode]:15s} trust {c}{m['final_trust']:13s}\033[0m worst error shown {err:>12s}"
                  f"   {m['alarm_kinds'] or 'no alarms'}")
        print(f"  \033[90m{s['say']}\033[0m")
    print(f"\nDemo finished in {time.time() - t0:.1f} s")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--html")
    p.add_argument("--fragment", action="store_true", help="omit the <html> wrapper (for hosts that add one)")
    a = p.parse_args()
    if a.html:
        tpl = (Path(__file__).parent / "demo_template.html").read_text()
        page = tpl.replace("/*DATA*/null", json.dumps(build(), separators=(",", ":")))
        if not a.fragment:
            page = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
                    '<style>body{margin:0}[hidden]{display:none!important}</style></head><body>'
                    + page + "</body></html>")
        out = Path(a.html)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page)
        print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    else:
        terminal()
