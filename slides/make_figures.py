"""Presentation figures for the CONFROUTE talk (ICMIC 2026).

Regenerates every chart used in slides/slides.tex from the experiment outputs in
the repository root. Vector PDF output, light surface, palette validated with the
dataviz colour checks (adjacent + all-pairs, light mode, white surface).

    python slides/make_figures.py
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch, Rectangle

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(parents=True, exist_ok=True)

# --- palette -----------------------------------------------------------------
BLUE = "#2a78d6"   # categorical slot 1  -> accuracy, local, ours
ORANGE = "#eb6834"  # categorical slot 2 -> confidence, fallback
AQUA = "#1baf7a"   # categorical slot 3  -> offload
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#ffffff"

SCENARIOS = ["stable", "intermittent", "degraded"]
SCEN_LABEL = {"stable": "Stable", "intermittent": "Intermittent", "degraded": "Degraded"}

mpl.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans",
    "font.size": 12,
    "axes.titlesize": 13,
    "axes.labelsize": 12,
    "axes.labelcolor": INK2,
    "axes.edgecolor": AXIS,
    "axes.linewidth": 1.0,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelcolor": INK2,
    "ytick.labelcolor": INK2,
    "xtick.major.size": 0,
    "ytick.major.size": 0,
    "grid.color": GRID,
    "grid.linewidth": 1.0,
    "legend.frameon": False,
    "pdf.fonttype": 42,
})


def bare(ax, left=True, bottom=True):
    """Recessive chrome: drop the box, keep only the axes that carry meaning."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_visible(left)
    ax.spines["bottom"].set_visible(bottom)
    ax.spines["left"].set_color(AXIS)
    ax.spines["bottom"].set_color(AXIS)


def save(fig, name):
    """PDF for the LaTeX deck, PNG for the PowerPoint deck."""
    path = OUT / name
    fig.savefig(path, bbox_inches="tight", pad_inches=0.03)
    png = path.with_suffix(".png")
    fig.savefig(png, bbox_inches="tight", pad_inches=0.03, dpi=200)
    plt.close(fig)
    print(f"wrote {path.relative_to(ROOT)} (+png)")


# --- data --------------------------------------------------------------------
traces = pd.read_csv(ROOT / "confidence_traces.csv")
summary = pd.read_csv(ROOT / "results_summary.csv")
actions = pd.read_csv(ROOT / "action_distribution.csv")

unsafe = summary.pivot(index="policy", columns="scenario", values="Unsafe Rate") * 100
latency = summary.pivot(index="policy", columns="scenario", values="Latency (ms)")
POLICIES = ["Always Local", "Always Offload", "Confidence Threshold", "Load Only", "Three-Way (Ours)"]
SHORT = {
    "Always Local": "Always local",
    "Always Offload": "Always offload",
    "Confidence Threshold": "Confidence threshold",
    "Load Only": "Load only",
    "Three-Way (Ours)": "CONFROUTE (ours)",
}
FALLBACK_THRESHOLD = 0.65


# =============================================================================
# 1. Calibration failure: accuracy falls while confidence rises
# =============================================================================
def fig_calibration():
    nom = traces[traces.condition == "nominal"]
    adv = traces[traces.condition == "adverse"]
    acc = [nom.correct.mean() * 100, adv.correct.mean() * 100]
    conf = [nom.confidence.mean() * 100, adv.confidence.mean() * 100]

    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    x = [0, 1]

    ax.plot(x, acc, color=BLUE, lw=2.4, marker="o", ms=9, zorder=3,
            markeredgecolor=SURFACE, markeredgewidth=2)
    ax.plot(x, conf, color=ORANGE, lw=2.4, marker="o", ms=9, zorder=3,
            markeredgecolor=SURFACE, markeredgewidth=2)

    ax.annotate(f"{acc[0]:.1f}%", (0, acc[0]), xytext=(-12, 6), textcoords="offset points",
                ha="right", color=INK, fontsize=13, fontweight="bold")
    ax.annotate(f"{acc[1]:.1f}%", (1, acc[1]), xytext=(12, -2), textcoords="offset points",
                ha="left", color=INK, fontsize=13, fontweight="bold")
    ax.annotate(f"{conf[0]:.1f}", (0, conf[0]), xytext=(-12, -14), textcoords="offset points",
                ha="right", color=INK, fontsize=13, fontweight="bold")
    ax.annotate(f"{conf[1]:.1f}", (1, conf[1]), xytext=(12, 4), textcoords="offset points",
                ha="left", color=INK, fontsize=13, fontweight="bold")

    ax.annotate("Accuracy", (1, acc[1]), xytext=(12, -20), textcoords="offset points",
                ha="left", color=BLUE, fontsize=13, fontweight="bold")
    ax.annotate("Mean confidence", (1, conf[1]), xytext=(12, 22), textcoords="offset points",
                ha="left", color=ORANGE, fontsize=13, fontweight="bold")

    # the gap that should not exist
    ax.annotate("", xy=(1.0, acc[1]), xytext=(1.0, conf[1]),
                arrowprops=dict(arrowstyle="<->", color=INK2, lw=1.4, shrinkA=3, shrinkB=3))
    ax.text(0.95, (acc[1] + conf[1]) / 2, "9.2 pt\novershoot", ha="right", va="center",
            color=INK2, fontsize=12, linespacing=1.25)

    ax.set_xlim(-0.42, 1.62)
    ax.set_ylim(68, 96)
    ax.set_xticks(x)
    ax.set_xticklabels(["Nominal imagery", "Adverse imagery\n(haze, blur, low contrast, noise)"],
                       fontsize=12)
    ax.set_ylabel("Percent")
    ax.set_yticks([70, 75, 80, 85, 90, 95])
    ax.grid(axis="y", zorder=0)
    ax.set_axisbelow(True)
    bare(ax, left=False)
    # no chart title: the slide headline states the takeaway
    save(fig, "fig_calibration.pdf")


# =============================================================================
# 2. Where the errors sit relative to the fallback threshold
# =============================================================================
def fig_error_confidence():
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9), sharey=True)
    bins = np.linspace(0.45, 1.0, 23)

    for ax, cond, colour in zip(axes, ["nominal", "adverse"], [BLUE, ORANGE]):
        errs = traces[(traces.condition == cond) & (~traces.correct)].confidence
        missed = (errs >= FALLBACK_THRESHOLD).sum()

        ax.axvspan(FALLBACK_THRESHOLD, 1.0, color=GRID, alpha=0.55, lw=0, zorder=0)
        ax.hist(errs, bins=bins, color=colour, zorder=2)
        ax.axvline(FALLBACK_THRESHOLD, color=INK, lw=1.6, ls=(0, (4, 3)), zorder=3)

        ax.set_xlim(0.45, 1.0)
        ax.set_xlabel("Classifier confidence on errors")
        ax.grid(axis="y", zorder=0)
        ax.set_axisbelow(True)
        bare(ax, left=False)
        ax.set_title(f"{cond.capitalize()}  ({len(errs)} errors)", color=INK, loc="left", pad=26)
        ax.text(0.0, 1.03, f"{missed / len(errs):.0%} of errors escape fallback",
                transform=ax.transAxes, color=INK, fontsize=12.5, fontweight="bold")
        # axes fractions, so the shared y-limit set below cannot move these
        ax.text(FALLBACK_THRESHOLD - 0.012, 0.97, "caught", transform=ax.get_xaxis_transform(),
                ha="right", va="top", color=INK2, fontsize=11)
        ax.text(FALLBACK_THRESHOLD + 0.012, 0.97, "missed", transform=ax.get_xaxis_transform(),
                ha="left", va="top", color=INK2, fontsize=11)
        ax.text(FALLBACK_THRESHOLD + 0.012, 0.88, f"fallback\nthreshold {FALLBACK_THRESHOLD}",
                transform=ax.get_xaxis_transform(), ha="left", va="top",
                color=INK2, fontsize=10, linespacing=1.25)

    axes[0].set_ylim(0, 20)
    axes[0].set_ylabel("Error count")
    save(fig, "fig_error_confidence.pdf")


# =============================================================================
# 3. Unsafe rate across link regimes, all policies
# =============================================================================
def fig_unsafe_by_scenario():
    fig, ax = plt.subplots(figsize=(8.2, 4.5))
    x = np.arange(3)
    baselines = [p for p in POLICIES if p != "Three-Way (Ours)"]

    for policy in baselines:
        y = [unsafe.loc[policy, s] for s in SCENARIOS]
        ax.plot(x, y, color=MUTED, lw=1.5, marker="o", ms=5,
                markeredgecolor=SURFACE, markeredgewidth=1.8, zorder=2, alpha=0.75)

    ours_y = [unsafe.loc["Three-Way (Ours)", s] for s in SCENARIOS]
    ax.plot(x, ours_y, color=BLUE, lw=2.8, marker="o", ms=9,
            markeredgecolor=SURFACE, markeredgewidth=2, zorder=4)
    for i, v in enumerate(ours_y):
        ax.annotate(f"{v:.1f}%", (i, v), xytext=(0, -22), textcoords="offset points",
                    ha="center", color=BLUE, fontsize=12.5, fontweight="bold")
    ax.annotate("CONFROUTE\n(ours)", (2, ours_y[2]), xytext=(14, 0),
                textcoords="offset points", va="center", color=BLUE,
                fontsize=12.5, fontweight="bold", linespacing=1.25)

    # the four baselines converge under degraded links: bracket them as one group
    lo = min(unsafe.loc[p, "degraded"] for p in baselines)
    hi = max(unsafe.loc[p, "degraded"] for p in baselines)
    ax.annotate("", xy=(2.14, lo), xytext=(2.14, hi),
                arrowprops=dict(arrowstyle="-", color=INK2, lw=1.3))
    ax.plot([2.10, 2.14], [lo, lo], color=INK2, lw=1.3)
    ax.plot([2.10, 2.14], [hi, hi], color=INK2, lw=1.3)
    ax.annotate(f"all 4 baselines\n{lo:.1f} – {hi:.1f}%", (2.18, (lo + hi) / 2),
                xytext=(4, 0), textcoords="offset points", va="center",
                color=INK2, fontsize=11.5, linespacing=1.25)

    handles = [
        plt.Line2D([], [], color=BLUE, lw=2.8, marker="o", ms=8,
                   markeredgecolor=SURFACE, markeredgewidth=2, label="CONFROUTE (ours)"),
        plt.Line2D([], [], color=MUTED, lw=1.5, marker="o", ms=5, alpha=0.75,
                   label="Baselines (4 policies)"),
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=11.5, labelcolor=INK2,
              handlelength=2.2, borderpad=0)

    ax.set_xlim(-0.25, 3.5)
    ax.set_ylim(0, 9.4)
    ax.set_xticks(x)
    ax.set_xticklabels([SCEN_LABEL[s] for s in SCENARIOS])
    ax.set_ylabel("Unsafe outcome rate (%)")
    ax.set_xlabel("Link regime")
    ax.grid(axis="y", zorder=0)
    ax.set_axisbelow(True)
    bare(ax, left=False)
    save(fig, "fig_unsafe_by_scenario.pdf")


# =============================================================================
# 4. Safety / latency trade-off under degraded links
# =============================================================================
def fig_tradeoff():
    fig, ax = plt.subplots(figsize=(7.6, 4.5))
    # (dx, dy, ha) chosen so no label overlaps a neighbouring marker
    offsets = {
        "Always Local": (0, 15, "center"),
        "Always Offload": (0, -20, "center"),
        "Confidence Threshold": (-14, 0, "right"),
        "Load Only": (0, 15, "center"),
        "Three-Way (Ours)": (16, 0, "left"),
    }

    for policy in POLICIES:
        ours = policy == "Three-Way (Ours)"
        xv, yv = latency.loc[policy, "degraded"], unsafe.loc[policy, "degraded"]
        ax.scatter([xv], [yv], s=230 if ours else 110,
                   color=BLUE if ours else MUTED, zorder=4 if ours else 3,
                   edgecolor=SURFACE, linewidth=2)
        dx, dy, ha = offsets[policy]
        ax.annotate(SHORT[policy], (xv, yv), xytext=(dx, dy),
                    textcoords="offset points", ha=ha, va="center",
                    color=BLUE if ours else INK2,
                    fontsize=12.5 if ours else 11,
                    fontweight="bold" if ours else "normal")

    # improvement arrow parked on the axis, clear of every marker
    ax.annotate("", xy=(41.3, 4.15), xytext=(41.3, 4.75),
                arrowprops=dict(arrowstyle="->", color=MUTED, lw=1.8))
    ax.text(42.3, 4.45, "better", color=MUTED, fontsize=11.5, ha="left", va="center")

    ax.set_xlim(38, 116)
    ax.set_ylim(4.0, 8.0)
    ax.set_xlabel("Mean latency (ms)")
    ax.set_ylabel("Unsafe outcome rate (%)")
    ax.grid(zorder=0)
    ax.set_axisbelow(True)
    bare(ax, left=False)
    save(fig, "fig_tradeoff.pdf")


# =============================================================================
# 5. Action mix of the three-way router
# =============================================================================
def fig_actions():
    mix = actions[actions.policy == "Three-Way (Ours)"].set_index("scenario")
    fig, ax = plt.subplots(figsize=(8.0, 3.5))
    y = np.arange(3)[::-1]
    order = [("local", "Local", BLUE), ("offload", "Offload", AQUA), ("fallback", "Fallback", ORANGE)]

    left = np.zeros(3)
    for key, label, colour in order:
        vals = np.array([mix.loc[s, key] for s in SCENARIOS])
        # 2px surface gap between adjacent segments
        ax.barh(y, vals, left=left, height=0.58, color=colour, zorder=3,
                edgecolor=SURFACE, linewidth=2)
        for yi, (v, l) in enumerate(zip(vals, left)):
            if v >= 9:
                # fallback keeps a decimal: 7.6% is the number quoted in the paper
                txt = f"{v:.1f}%" if key == "fallback" else f"{v:.0f}%"
                ax.text(l + v / 2, y[yi], txt, ha="center", va="center",
                        color="white", fontsize=12, fontweight="bold", zorder=4)
        left = left + vals

    for yi, s in enumerate(SCENARIOS):
        fb = mix.loc[s, "fallback"]
        if 0 < fb < 9:
            ax.annotate(f"{fb:.1f}%", (100, y[yi]), xytext=(8, 0), textcoords="offset points",
                        va="center", color=ORANGE, fontsize=12, fontweight="bold")

    handles = [Patch(facecolor=c, label=l) for _, l, c in order]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0, 1.28),
              ncol=3, fontsize=12, handlelength=1.1, handleheight=1.1,
              columnspacing=1.6, labelcolor=INK2)

    ax.set_yticks(y)
    ax.set_yticklabels([SCEN_LABEL[s] for s in SCENARIOS], fontsize=12)
    ax.set_xlim(0, 108)
    ax.set_xticks([])
    ax.set_xlabel("Share of 2,500 tasks per regime")
    bare(ax, left=False, bottom=False)
    save(fig, "fig_actions.pdf")


# =============================================================================
# 6. Decision regions of the deployed threshold policy
# =============================================================================
def fig_boundary():
    conf_t, bw_t, bw_max = FALLBACK_THRESHOLD, 1.8, 6.0
    fig, ax = plt.subplots(figsize=(6.8, 4.6))

    ax.add_patch(Rectangle((0, bw_t), 1, bw_max - bw_t, facecolor=AQUA, alpha=0.20, lw=0))
    ax.add_patch(Rectangle((0, 0), conf_t, bw_t, facecolor=ORANGE, alpha=0.28, lw=0))
    ax.add_patch(Rectangle((conf_t, 0), 1 - conf_t, bw_t, facecolor=BLUE, alpha=0.22, lw=0))

    ax.axhline(bw_t, color=INK2, lw=1.5, ls=(0, (4, 3)), zorder=3)
    ax.plot([conf_t, conf_t], [0, bw_t], color=INK2, lw=1.5, ls=(0, (4, 3)), zorder=3)

    ax.text(0.5, 4.3, "OFFLOAD", ha="center", va="center", color="#0f7a53",
            fontsize=15, fontweight="bold")
    ax.text(0.5, 3.85, "link is usable and a peer is reachable", ha="center", va="center",
            color=INK2, fontsize=11.5)
    ax.text(0.325, 1.02, "FALLBACK", ha="center", va="center", color="#a8410f",
            fontsize=15, fontweight="bold")
    ax.text(0.325, 0.62, "uncertain $\\it{and}$ cut off", ha="center", va="center",
            color=INK2, fontsize=11.5)
    ax.text(0.83, 1.02, "LOCAL", ha="center", va="center", color="#1a5798",
            fontsize=15, fontweight="bold")
    ax.text(0.83, 0.62, "confident enough to act alone", ha="center", va="center",
            color=INK2, fontsize=10)

    ax.annotate(f"bandwidth floor {bw_t} Mbps", xy=(0.015, bw_t), xytext=(0.015, bw_t + 0.22),
                color=INK2, fontsize=11)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, bw_max)
    # the confidence floor rides on the axis itself rather than floating in a region
    ax.set_xticks([0.0, 0.2, 0.4, conf_t, 0.8, 1.0])
    ax.set_xticklabels(["0.0", "0.2", "0.4", f"{conf_t}", "0.8", "1.0"])
    for lbl in ax.get_xticklabels():
        if lbl.get_text() == f"{conf_t}":
            lbl.set_color(INK)
            lbl.set_fontweight("bold")
    ax.set_xlabel("Vessel classifier confidence")
    ax.set_ylabel("Effective bandwidth (Mbps)")
    bare(ax)
    save(fig, "fig_boundary.pdf")


# =============================================================================
# 7. Real chips: the same vessel before and after degradation
# =============================================================================
def fig_chips(indices=(252, 533, 925)):
    """Actual ShipsNet chips the classifier got right, then confidently wrong.

    Chips are reconstructed from shipsnet.json and put through the identical
    adverse transform used in the experiment (experiments/run_edge_ai_routing_
    experiments.py::apply_adverse_maritime_condition), so the pictures match the
    confidences recorded in confidence_traces.csv.
    """
    import json
    import random

    from PIL import Image, ImageEnhance, ImageFilter

    SEED = 42  # must match experiments/run_edge_ai_routing_experiments.py

    def adverse(image, index):
        rng = random.Random(SEED + index)
        image = ImageEnhance.Contrast(image).enhance(rng.uniform(0.45, 0.75))
        image = ImageEnhance.Brightness(image).enhance(rng.uniform(0.55, 0.85))
        image = image.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.6, 1.4)))
        arr = np.asarray(image).astype(np.float32)
        alpha = rng.uniform(0.16, 0.32)
        arr = (1.0 - alpha) * arr + alpha * np.full_like(arr, 205.0)
        arr = np.clip(arr + np.random.default_rng(SEED + index).normal(0, 8, arr.shape), 0, 255)
        return Image.fromarray(arr.astype(np.uint8), mode="RGB")

    raw = json.loads((ROOT / "data" / "ships-in-satellite-imagery" / "shipsnet.json")
                     .read_text(encoding="utf-8"))
    nom_t = traces[traces.condition == "nominal"].set_index("sample_index")
    adv_t = traces[traces.condition == "adverse"].set_index("sample_index")

    def draw(conditions, name, subtitle):
        nrows = len(conditions)
        fig, axes = plt.subplots(nrows, len(indices),
                                 figsize=(3.05 * len(indices), 3.55 * nrows + 0.9),
                                 squeeze=False)
        for col, idx in enumerate(indices):
            chip = np.array(raw["data"][idx], dtype=np.uint8).reshape(3, 80, 80).transpose(1, 2, 0)
            img = Image.fromarray(chip, mode="RGB")
            variants = {"Nominal": (img, nom_t.loc[idx]),
                        "Adverse": (adverse(img, idx), adv_t.loc[idx])}
            for row, label in enumerate(conditions):
                im, rec = variants[label]
                ax = axes[row][col]
                ax.imshow(np.asarray(im), interpolation="nearest")
                ax.set_xticks([]); ax.set_yticks([])
                ok = bool(rec.correct)
                edge = "#0ca30c" if ok else "#d03b3b"
                for s in ax.spines.values():
                    s.set_edgecolor(edge)
                    s.set_linewidth(4)
                verdict = "SHIP" if int(rec.predicted) == 1 else "NO SHIP"
                ax.set_xlabel(f"“{verdict}”   conf {rec.confidence:.2f}\n"
                              f"{'correct' if ok else 'WRONG'}",
                              color=edge, fontsize=13.5,
                              fontweight="bold" if not ok else "normal", linespacing=1.5)
                if col == 0:
                    ax.set_ylabel(label, color=INK, fontsize=15,
                                  fontweight="bold", labelpad=14)

        # no in-figure title: the slide carries it
        fig.tight_layout(h_pad=3.0)
        save(fig, name)

    draw(["Nominal"], "fig_chips_nominal.pdf", None)
    draw(["Nominal", "Adverse"], "fig_chips.pdf", None)


if __name__ == "__main__":
    fig_chips()
    fig_calibration()
    fig_error_confidence()
    fig_unsafe_by_scenario()
    fig_tradeoff()
    fig_actions()
    fig_boundary()
