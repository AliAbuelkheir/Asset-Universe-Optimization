from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PREDICTIONS = ROOT / "ranked-risk-model" / "outputs" / "best_model" / "ranked_predictions.csv"
OUTPUT = ROOT / "defense" / "assets" / "ch4_test_rank_alignment_transparent.png"


def main() -> None:
    predictions = pd.read_csv(PREDICTIONS)
    test = predictions.loc[predictions["Split"].eq("test")].copy()

    counts = test.groupby("Date")["AssetID"].transform("count")
    denominator = (counts - 1).clip(lower=1)
    test["realized_rank_pct"] = (test["realized_rank"] - 1) / denominator
    test["predicted_rank_pct"] = (test["PredictedRank"] - 1) / denominator
    test["absolute_rank_gap"] = (test["realized_rank"] - test["PredictedRank"]).abs()

    figure, axis = plt.subplots(figsize=(10.65, 7.96))
    figure.patch.set_alpha(0)
    axis.set_facecolor("none")

    scatter = axis.scatter(
        test["realized_rank_pct"],
        test["predicted_rank_pct"],
        c=test["absolute_rank_gap"],
        cmap="viridis",
        s=42,
        alpha=0.82,
        edgecolors="none",
    )
    axis.plot(
        [0, 1],
        [0, 1],
        color="#F18700",
        linewidth=2,
        linestyle="--",
        label="Perfect rank alignment",
    )
    axis.set_xlim(-0.03, 1.03)
    axis.set_ylim(-0.03, 1.03)
    axis.set_xlabel("Realized-risk rank percentile within month", fontsize=13)
    axis.set_ylabel("Predicted-risk rank percentile within month", fontsize=13)
    axis.grid(True, alpha=0.3, linestyle="--")
    axis.legend(loc="lower right", fontsize=11)

    colorbar = figure.colorbar(scatter, ax=axis, pad=0.04)
    colorbar.set_label("Absolute rank gap", fontsize=12)
    figure.tight_layout()
    figure.savefig(OUTPUT, dpi=200, bbox_inches="tight", transparent=True)
    plt.close(figure)


if __name__ == "__main__":
    main()
