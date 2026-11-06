"""Run the full experiment matrix -> results/*.csv. One command: make experiments."""
import csv
import statistics
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nma.attacks.toolkit import a8_bruteforce  # noqa: E402
from nma.scenario import run  # noqa: E402
from nma.sim.navmsg import NavData  # noqa: E402
from nma.sim.nma_message import NmaMessage  # noqa: E402
from nma.sim.stream import SYSTEMS, World  # noqa: E402
from nma.tesla.keychain import KeyChain  # noqa: E402
from nma.tesla.tags import check_tag, make_tag  # noqa: E402
from nma.tesla.verify import KeyVerifier  # noqa: E402

OUT = ROOT / "results"


def write(name, rows):
    OUT.mkdir(exist_ok=True)
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote results/{name} ({len(rows)} rows)")


def matrix(cfg):
    rows = []
    for attack, sevs in cfg["attacks"].items():
        seeds = range(cfg["replay_seeds"]) if attack == "A6" else cfg["seeds"]
        for sev in sevs:
            for mode in cfg["modes"]:
                for seed in seeds:
                    rows.append(run(attack, sev, mode, seed).metrics)
        print(f"  {attack} done")
    for mode in cfg["modes"]:
        for seed in cfg["seeds"]:
            rows.append(run(None, 0, mode, seed).metrics)
    write("attack_matrix.csv", rows)


def bruteforce():
    rows = []
    for bits in (8, 10, 12, 14, 16):
        for acc in (1, 2):
            guesses = 200_000 if acc == 1 else 400_000
            hits = a8_bruteforce(bits, guesses, acc, seed=bits)
            rows.append({"tag_bits": bits, "tags_accumulated": acc, "guesses": guesses, "hits": hits,
                         "simulated_rate": hits / guesses, "theoretical_rate": 2.0 ** (-bits * acc)})
    for bits, acc in ((32, 1), (40, 1), (40, 2)):
        rows.append({"tag_bits": bits, "tags_accumulated": acc, "guesses": "", "hits": "",
                     "simulated_rate": "", "theoretical_rate": 2.0 ** (-bits * acc)})
    write("a8_bruteforce.csv", rows)


def performance(cfg):
    rows = []
    for start in ("cold", "warm"):
        t = [run(None, 0, "hardened", s, cold=start == "cold", power_on=7.0 + 23.0 * s).metrics["first_auth_fix_s"]
             for s in range(20)]
        rows.append({"metric": f"time_to_first_authenticated_fix_{start}", "value": statistics.median(t), "unit": "s (median of 20 switch-on times)"})
    # NavIC alone: first time all three NavIC satellites are authenticated
    r = run(None, 0, "hardened", 0)
    navic = next(f.t for f in r.fixes if sum(k[0] == "NAVIC" for k in f.used) == 3)
    rows.append({"metric": "navic_ttfaf_warm", "value": navic, "unit": "s"})
    # bandwidth: authentication bits as a share of message bits (modelled layout)
    w = World(0)
    for name in SYSTEMS:
        nav = auth = 0
        for e in w.broadcast():
            if e.kind == "nav" and e.system == name:
                m = NmaMessage.from_bytes(e.nma)
                nav += NavData.from_bytes(e.data).bits
                auth += m.auth_bits
        rows.append({"metric": f"auth_bandwidth_share_{name.lower()}", "value": round(auth / (nav + auth), 3), "unit": "fraction"})
    rows.append({"metric": "navic_auth_bits_per_second_per_sat", "value": (32 + 128) / SYSTEMS["NAVIC"].period, "unit": "bit/s"})
    rows.append({"metric": "tesla_tag_bits_vs_ed25519_signature_bits", "value": "32 vs 512", "unit": "bits"})
    # CPU per verified tag / per chain step
    key, n = KeyChain(1, 1).key(1), 20_000
    tag = make_tag(key, b"x" * 40, 1, 1, 32)
    t0 = time.perf_counter()
    for _ in range(n):
        check_tag(key, b"x" * 40, 1, 1, tag, 32)
    rows.append({"metric": "cpu_per_tag_verify", "value": round((time.perf_counter() - t0) / n * 1e6, 2), "unit": "us"})
    c = KeyChain(5000, 2)
    t0 = time.perf_counter()
    KeyVerifier(c.root).verify(5000, c.key(5000))
    rows.append({"metric": "cpu_per_chain_hash", "value": round((time.perf_counter() - t0) / 5000 * 1e6, 2), "unit": "us"})
    write("performance.csv", rows)


if __name__ == "__main__":
    cfg = yaml.safe_load(open(ROOT / "experiments/configs/matrix.yaml"))
    t = time.time()
    matrix(cfg)
    bruteforce()
    performance(cfg)
    print(f"done in {time.time() - t:.0f} s")
