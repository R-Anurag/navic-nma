"""python -m nma.attacks A1 --severity 10 [--mode naive|tesla|hardened|all] [--seed 0]"""
import argparse

from ..scenario import run

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("attack", choices=[f"A{i}" for i in range(1, 8)])
p.add_argument("--severity", type=float, required=True)
p.add_argument("--mode", default="all")
p.add_argument("--seed", type=int, default=0)
a = p.parse_args()
for mode in ("naive", "tesla", "hardened") if a.mode == "all" else (a.mode,):
    m = run(a.attack, a.severity, mode, a.seed).metrics
    print(f"{mode:9s} detected={m['detected']} fooled={m['fooled_frac']:.0%} "
          f"max_err={m['max_presented_err_m']} m trust={m['final_trust']} alarms={m['alarm_kinds']}")
