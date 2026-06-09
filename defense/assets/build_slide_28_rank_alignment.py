from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PREDICTIONS = ROOT / "ranked-risk-model" / "outputs" / "best_model" / "ranked_predictions.csv"
OUTPUT_DIR = ROOT / "defense" / "assets"

NAVY = "#0C171F"
GREEN = "#00F700"
LIGHT_GRAY = "#E3E6E8"


def build_figure(transparent: bool) -> plt.Figure:
    predictions = pd.read_csv(PREDICTIONS)
    test = predictions.loc[predictions["Split"].eq("test")].copy()

    counts = test.groupby("Date")["AssetID"].transform("count")
    denominator = (counts - 1).clip(lower=1)
    test["realized_rank_pct"] = (test["realized_rank"] - 1) / denominator
    test["predicted_rank_pct"] = (test["PredictedRank"] - 1) / denominator

    figure, axis = plt.subplots(figsize=(10.2, 7.0))
    figure.patch.set_alpha(0 if transparent else 1)
    if not transparent:
        figure.patch.set_facecolor(LIGHT_GRAY)
    axis.set_facecolor("none" if transparent else LIGHT_GRAY)

    axis.scatter(
        test["realized_rank_pct"],
        test["predicted_rank_pct"],
        s=34,
        color=NAVY,
        alpha=0.48,
        edgecolors="none",
    )
    axis.plot(
        [0, 1],
        [0, 1],
        color=GREEN,
        linewidth=2.0,
        linestyle=(0, (5, 5)),
        label="Perfect rank alignment",
        zorder=3,
    )

    axis.set_xlim(-0.025, 1.025)
    axis.set_ylim(-0.025, 1.025)
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("Realized-risk rank percentile within month", color=NAVY, fontsize=14, labelpad=12)
    axis.set_ylabel("Predicted-risk rank percentile within month", color=NAVY, fontsize=14, labelpad=12)

    axis.grid(True, color=NAVY, alpha=0.10, linewidth=0.8, linestyle="--")
    axis.tick_params(colors=NAVY, labelsize=11)
    for spine in axis.spines.values():
        spine.set_color(NAVY)
        spine.set_alpha(0.38)
        spine.set_linewidth(1.0)

    legend = axis.legend(loc="lower right", frameon=False, fontsize=11)
    for text in legend.get_texts():
        text.set_color(NAVY)

    figure.subplots_adjust(left=0.14, right=0.97, bottom=0.16, top=0.97)
    return figure


def main() -> None:
    for transparent, name in (
        (True, "slide_28_rank_alignment_transparent.png"),
        (False, "slide_28_rank_alignment.png"),
    ):
        figure = build_figure(transparent)
        figure.savefig(
            OUTPUT_DIR / name,
            dpi=300,
            bbox_inches="tight",
            transparent=transparent,
            facecolor="none" if transparent else LIGHT_GRAY,
        )
        plt.close(figure)


if __name__ == "__main__":
    main()
