"""Regenerate public README figures from the released scientific results.

Optional plotting dependencies: matplotlib==3.11.0, numpy==2.3.5.
Run from anywhere: python assets/render_figures.py
No model requests are made.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "results" / "summary.json"
MODELS = [
    ("luna_decisions_choice", "OpenAI GPT-6 Luna Decisions", "#234E70"),
    ("luna_chat", "OpenAI GPT-6 Luna (chat)", "#087F8C"),
    ("jev_choice", "TypeSafe Jev 1.13", "#7C3AED"),
    ("jev_114_choice", "TypeSafe Jev 1.14", "#2563EB"),
    ("pplx_decider_12_choice", "Perplexity Decider V1.2", "#00856A"),
    ("clef_choice", "Cloudflare Clef", "#B45309"),
    ("clef_flash_choice", "Cloudflare Clef-flash", "#BE185D"),
]
TACTICS = ["neutral_direct", "name_property_pressure", "urgency_saturation"]
STYLE = {
    "font.family": "DejaVu Sans",
    "font.size": 12,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "svg.fonttype": "none",
    "svg.hashsalt": "goldfishbench-public-v1",
    "pdf.fonttype": 42,
    "axes.edgecolor": "#D3DDE7",
    "axes.labelcolor": "#34465B",
    "xtick.color": "#526276",
    "ytick.color": "#1E3047",
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
}
plt.rcParams.update(STYLE)


def export(fig, name):
    fig.savefig(HERE / f"{name}.svg", bbox_inches="tight", pad_inches=0.30,
                metadata={"Date": None})
    fig.savefig(HERE / f"{name}.png", dpi=200, bbox_inches="tight", pad_inches=0.30,
                metadata={"Software": f"GoldfishBench; matplotlib {matplotlib.__version__}"})
    plt.close(fig)


def title(fig, main, sub):
    fig.text(0.03, 0.975, main, fontsize=22, weight="bold", color="#13273F", va="top")
    fig.text(0.03, 0.915, sub, fontsize=12, color="#526276", va="top")


def main():
    raw = SOURCE.read_bytes()
    source = json.loads(raw)
    rows = {(r["condition_id"], r["tactic"]): r for r in source["conditions"]}
    data = []
    for cid, name, color in MODELS:
        assert source["model_conditions"][cid]["display_name"] == name
        group = [rows[(cid, tactic)] for tactic in TACTICS]
        joint = [r["core_and_components"]["joint_core"] for r in group]
        far = [next(c for c in r["by_need"] if c["N"] and not c["S"])["false_acceptance_usable"] for r in group]
        assert all(z["denominator"] > 0 for z in far)
        assert all(abs(z["value"] - z["numerator"] / z["denominator"]) < 1e-12 for z in far)
        data.append({
            "condition_id": cid, "display_name": name, "color": color,
            "balanced_accuracy_mean": sum(x["balanced_accuracy_usable"] for x in joint) / 3,
            "joint_intended": sum(x["intended"] for x in joint),
            "joint_usable": sum(x["usable"] for x in joint),
            "joint_errors": sum(x["usable"] - x["correct"] for x in joint),
            "false_acceptance_N1_S0": {t: v for t, v in zip(TACTICS, far)},
        })

    # Diagnostic error rates are different from global balanced accuracy.
    values = np.array([[d["false_acceptance_N1_S0"][t]["value"] * 100 for t in TACTICS] for d in data])
    cmap = LinearSegmentedColormap.from_list("wrong_yes", ["#F2F7FA", "#FED7AA", "#EF6A46", "#972D3E"])
    fig, ax = plt.subplots(figsize=(12.4, 7.1))
    fig.subplots_adjust(left=0.35, right=0.94, top=0.80, bottom=0.17)
    title(fig, "When intervention is needed, does the model reject an unsuitable recipient?",
          "Wrong YES answers in the N=1, S=0 cell. Correct answer: NO. Ideal error rate: 0%.")
    ax.imshow(values, cmap=cmap, vmin=0, vmax=80, aspect="auto")
    ax.set_xticks(range(3), ["Neutral", "Names / properties", "Urgency"], fontsize=12, weight="bold")
    ax.xaxis.tick_top()
    ax.tick_params(axis="both", which="both", length=0, pad=12)
    ax.set_yticks(range(7), [d["display_name"] for d in data])
    for label, d in zip(ax.get_yticklabels(), data):
        label.set_color(d["color"])
    for i, d in enumerate(data):
        ax.plot(-0.50, i, "o", color=d["color"], markersize=8,
                transform=ax.get_yaxis_transform(), clip_on=False)
        for j, t in enumerate(TACTICS):
            f = d["false_acceptance_N1_S0"][t]
            ink = "white" if values[i, j] > 48 else "#172D46"
            ax.text(j, i-0.09, f"{f['value']*100:.2f}%", ha="center", va="center", fontsize=16, weight="bold", color=ink)
            ax.text(j, i+0.22, f"{f['numerator']} / {f['denominator']}", ha="center", va="center", fontsize=10, color=ink)
    ax.set_xticks(np.arange(-0.5, 3, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 7, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=4)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.text(0.03, 0.065, "662 fixed scenario families × 3 renderings. Counts use usable outputs; technical failures remain unavailable.", fontsize=11, color="#526276")
    fig.text(0.03, 0.03, "Exploratory controlled evaluation · Zero independent human semantic reviews · These are observed error rates, not causal effects.", fontsize=10, color="#526276")
    export(fig, "wrong-recipient-errors")

    # A full zero-to-one-hundred axis preserves the scale and the 50% baseline.
    ranked = sorted(data, key=lambda d: -d["balanced_accuracy_mean"])
    fig, ax = plt.subplots(figsize=(12.4, 6.9))
    fig.subplots_adjust(left=0.34, right=0.93, top=0.80, bottom=0.18)
    title(fig, "Overall performance across all four policy cells",
          "Balanced accuracy, equally averaged over neutral, names / properties, and urgency. Higher is better.")
    y = np.arange(7)
    bars = ax.barh(y, [r["balanced_accuracy_mean"] * 100 for r in ranked], height=0.55,
                   color=[r["color"] for r in ranked])
    ax.set_yticks(y, [r["display_name"] for r in ranked])
    ax.invert_yaxis()
    ax.set_xlim(0, 105)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.xaxis.set_major_formatter(PercentFormatter(100, decimals=0))
    ax.set_axisbelow(True)
    ax.grid(axis="x", color="#E6EDF3", linewidth=0.8)
    ax.axvline(50, color="#8392A4", linewidth=1, linestyle=(0, (3, 3)))
    ax.axvline(100, color="#8392A4", linewidth=1, linestyle=(0, (3, 3)))
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=14)
    for i, r in enumerate(ranked):
        ax.plot(-0.50, i, "o", color=r["color"], markersize=8,
                transform=ax.get_yaxis_transform(), clip_on=False)
        ax.text(r["balanced_accuracy_mean"]*100-1, i, f"{r['balanced_accuracy_mean']*100:.2f}%",
                va="center", ha="right", color="white", weight="bold", fontsize=12)
    fig.text(0.03, 0.075, "Always NO: 75% raw accuracy, 50% balanced accuracy. Perfect policy decisions: 100% balanced accuracy.", fontsize=11, color="#526276")
    fig.text(0.03, 0.035, "Descriptive ordering on this fixed suite; no ranking significance claim. Five Jev 1.14 joint outputs are unavailable.", fontsize=10, color="#526276")
    export(fig, "balanced-accuracy")

    # Audit-friendly source values used by the two figures.
    payload = {"source": "results/summary.json", "source_sha256": hashlib.sha256(raw).hexdigest(),
               "measures": data, "status": "observed_exploratory_model_measurements"}
    (HERE / "figure-data.json").write_text(json.dumps(payload, indent=2) + "\n")
    (HERE / "model-dots").mkdir(exist_ok=True)
    for cid, name, color in MODELS:
        (HERE / "model-dots" / f"{cid}.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12">'
            f'<title>{name}</title><circle cx="6" cy="6" r="4.5" fill="{color}"/></svg>\n')
    outputs = ["wrong-recipient-errors.svg", "wrong-recipient-errors.png", "balanced-accuracy.svg", "balanced-accuracy.png", "figure-data.json"]
    manifest = {"source": "results/summary.json", "source_sha256": payload["source_sha256"],
                "script": "assets/render_figures.py", "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "matplotlib": matplotlib.__version__, "numpy": np.__version__,
                "figures": {n: hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in outputs},
                "notes": ["No simulated values. No live model calls.", "Both plots use the frozen released scientific summary.",
                          "Figure-data records all chart values and exact denominators."]}
    (HERE / "figure-manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print("Rendered two figures in SVG and PNG from released results; wrote data and hash manifest.")


if __name__ == "__main__":
    main()
