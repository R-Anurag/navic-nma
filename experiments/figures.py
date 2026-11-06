"""results/*.csv -> figures/*.png. One command: make figures."""
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
# validated categorical slots 1-3 (pass all-pairs CVD checks)
COLOR = {"naive": "#eb6834", "tesla": "#2a78d6", "hardened": "#1baf7a"}
LABEL = {"naive": "Naive receiver", "tesla": "TESLA only", "hardened": "Hardened (ours)"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "lines.linewidth": 2, "lines.markersize": 7, "figure.dpi": 150, "savefig.bbox": "tight",
    "axes.titleweight": "bold", "axes.titlesize": 13, "axes.titlelocation": "left",
})


def load(name):
    with open(ROOT / "results" / name) as f:
        return list(csv.DictReader(f))


def agg(rows, attack, field):
    """{mode: [(severity, mean(field))]}"""
    d = defaultdict(list)
    for r in rows:
        if r["attack"] == attack:
            d[(r["mode"], float(r["severity"]))].append(float(r[field]))
    out = defaultdict(list)
    for (mode, sev), v in sorted(d.items(), key=lambda kv: kv[0][1]):
        out[mode].append((sev, mean(v)))
    return out


def lines(ax, data, modes=("naive", "tesla", "hardened"), pct=True):
    for m in modes:
        xs, ys = zip(*data[m])
        ys = [y * 100 for y in ys] if pct else ys
        ax.plot(xs, ys, "-o", color=COLOR[m], label=LABEL[m], markeredgecolor="white", markeredgewidth=1.5)
    ax.legend(frameon=False, loc="best")


def save(fig, name):
    FIG.mkdir(exist_ok=True)
    fig.savefig(FIG / name)
    plt.close(fig)
    print(f"wrote figures/{name}")


def summary(rows, headline):
    names = {"A1": "Data\ntampering", "A2": "Forged\nkey", "A3": "Fake\nroot key", "A4": "Old-key\nreuse",
             "A5": "Clock\ndrag", "A6": "Replay\n(5 s)", "A7": "Downgrade"}
    fig, ax = plt.subplots(figsize=(10, 4.2))
    w = 0.26
    for k, m in enumerate(("naive", "tesla", "hardened")):
        vals = []
        for a, sev in headline.items():
            v = [float(r["fooled_frac"]) for r in rows if r["attack"] == a and r["mode"] == m and float(r["severity"]) == sev]
            vals.append(100 * mean(v))
        xs = [i + (k - 1) * (w + 0.02) for i in range(len(headline))]
        bars = ax.bar(xs, vals, w, color=COLOR[m], label=LABEL[m], edgecolor="white", linewidth=1)
        for x, v in zip(xs, vals):
            if v < 1:
                ax.bar(x, 0.8, w, color=COLOR[m], edgecolor="none")
                ax.text(x, 1.5, "0", ha="center", va="bottom", fontsize=8, color=MUTED)
    ax.set_xticks(range(len(headline)), [names[a] for a in headline])
    ax.set_ylabel("Time spent showing a wrong position\nas valid (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Hardened receiver is never fooled by the seven headline attacks")
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    ax.grid(axis="x", visible=False)
    save(fig, "fig1_attack_summary.png")


def replay(rows):
    d = agg(rows, "A6", "fooled_frac")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.axvspan(0.08, 1.0, color="#f3f2ee", zorder=0)
    ax.text(0.11, 50, "honest loss:\nreplay delay inside\nthe clock-error band", fontsize=9, color=MUTED)
    lines(ax, d)
    ax.axvline(1.0, color=MUTED, ls="--", lw=1)
    ax.text(1.07, 96, "replay threshold 1 s", fontsize=9, color=MUTED, va="top")
    ax.axvline(29, color=MUTED, ls=":", lw=1)
    ax.text(26, 8, "Galileo key\ndisclosed (30 s)", fontsize=9, color=MUTED, ha="right")
    ax.set_xscale("log")
    ax.set_xlim(0.08, 70)
    ax.set_xlabel("Replay delay d (s, log scale)")
    ax.set_ylabel("Time fooled (%)")
    ax.set_title("A6 Replay: TESLA alone can't see a delayed rebroadcast")
    save(fig, "fig2_a6_replay.png")


def drag(rows):
    d = agg(rows, "A5", "max_trusted_clock_err_s")
    f = agg(rows, "A5", "fooled_frac")
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    lines(ax, d, ("tesla", "hardened"), pct=False)
    ax.set_xscale("log")
    ax.set_yscale("symlog", linthresh=1)
    ax.set_ylim(0, 150)
    ax.axhline(1.0, color=MUTED, ls="--", lw=1)
    ax.text(0.27, 1.25, "signed-time bound ~1 s", fontsize=9, color=MUTED)
    ax.set_xlabel("Clock drag applied by attacker (s)")
    ax.set_ylabel("Worst clock error while still\nclaiming trust (s)")
    ax.set_title("A5 Clock drag: signed time caps the error")
    lines(ax2, f)
    ax2.set_xscale("log")
    ax2.set_xlabel("Clock drag applied by attacker (s)")
    ax2.set_ylabel("Time fooled (%)")
    ax2.set_title("…so old-key forgery stops working")
    save(fig, "fig3_a5_clock_drag.png")


def oldkey(rows):
    fig, ax = plt.subplots(figsize=(8, 4.2))
    lines(ax, agg(rows, "A4", "fooled_frac"))
    ax.set_xscale("symlog", linthresh=1)
    ax.set_xlabel("Receiver clock running slow by (s)")
    ax.set_ylabel("Time fooled (%)")
    ax.set_title("A4 Old-key reuse: TESLA is only as good as the clock")
    save(fig, "fig4_a4_old_key.png")


def tamper(rows):
    d = agg(rows, "A1", "max_presented_err_m")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    lines(ax, d, pct=False)
    ax.set_xlabel("Ephemeris shift injected by attacker (km)")
    ax.set_ylabel("Worst position error shown (m)")
    ax.set_title("A1 Data tampering: naive receiver drifts kilometres")
    save(fig, "fig5_a1_tamper.png")


def downgrade(rows):
    fig, ax = plt.subplots(figsize=(8, 4.2))
    d = agg(rows, "A7", "fooled_frac")
    d = {m: [(x * 100, y) for x, y in v] for m, v in d.items()}
    lines(ax, d)
    ax.set_xlabel("Authenticated satellites jammed (%)")
    ax.set_ylabel("Time fooled (%)")
    ax.set_title("A7 Downgrade: spoofed GPS never reaches the solver")
    save(fig, "fig6_a7_downgrade.png")


def brute(rows):
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for acc, color in ((1, "#2a78d6"), (2, "#1baf7a")):
        r = [x for x in rows if int(x["tags_accumulated"]) == acc]
        th = [(int(x["tag_bits"]), float(x["theoretical_rate"])) for x in r]
        ax.plot(*zip(*th), "-", color=color, label=f"{acc} tag{'s' if acc > 1 else ''}: theory 2^-{'2' if acc > 1 else ''}L")
        sim = [(int(x["tag_bits"]), float(x["simulated_rate"])) for x in r if x["hits"] not in ("", "0")]
        if sim:
            ax.plot(*zip(*sim), "o", color=color, markeredgecolor="white", markeredgewidth=1.5, label=f"{acc} tag{'s' if acc > 1 else ''}: simulated")
    ax.set_yscale("log", base=2)
    ax.axvline(32, color=MUTED, ls="--", lw=1); ax.text(32.5, 2**-20, "NavIC\n32-bit", fontsize=9, color=MUTED)
    ax.axvline(40, color=MUTED, ls=":", lw=1); ax.text(39.5, 2**-20, "Galileo\n40-bit", ha="right", fontsize=9, color=MUTED)
    ax.set_xlabel("Tag length L (bits)")
    ax.set_ylabel("Forgery success per guess")
    ax.set_title("A8 Tag brute force matches 2^-L; accumulation squares it")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    save(fig, "fig7_a8_bruteforce.png")


if __name__ == "__main__":
    rows = load("attack_matrix.csv")
    headline = yaml.safe_load(open(ROOT / "experiments/configs/matrix.yaml"))["headline"]
    summary(rows, headline)
    replay(rows)
    drag(rows)
    oldkey(rows)
    tamper(rows)
    downgrade(rows)
    brute(load("a8_bruteforce.csv"))
