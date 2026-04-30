"""Generate diagnostic plots from saved experiment prediction artifacts."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config

RISK_DISTRIBUTION_FILE_NAME = "test_risk_score_distribution.png"
RANK_ALIGNMENT_FILE_NAME = "test_rank_alignment.png"
MONTHLY_PERFORMANCE_FILE_NAME = "test_monthly_performance.png"
BEST_MONTH_RANK_FILE_NAME = "test_best_month_rank_comparison.png"
CALIBRATION_FILE_NAME = "test_score_calibration.png"
SUMMARY_FILE_NAME = "test_diagnostic_summary.json"

PREDICTIONS_FILE_NAME = "ranked_predictions.csv"
MONTHLY_METRICS_FILE_NAME = "monthly_metrics.csv"
SETUP_SUMMARY_FILE_NAME = "setup_summary.json"

PREDICTED_COLOR = "#0b7285"
REALIZED_COLOR = "#c92a2a"
ACCENT_COLOR = "#e67700"
NEUTRAL_COLOR = "#495057"
BACKGROUND_COLOR = "#f8f5ef"
PANEL_COLOR = "#fffdf8"
GRID_COLOR = "#d9d2c6"


def _apply_plot_style() -> None:
    plt.style.use("default")
    plt.rcParams.update(
        {
            "figure.facecolor": BACKGROUND_COLOR,
            "axes.facecolor": PANEL_COLOR,
            "axes.edgecolor": GRID_COLOR,
            "axes.labelcolor": NEUTRAL_COLOR,
            "axes.titleweight": "bold",
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRID_COLOR,
            "grid.alpha": 0.65,
            "grid.linestyle": "--",
            "xtick.color": NEUTRAL_COLOR,
            "ytick.color": NEUTRAL_COLOR,
            "text.color": NEUTRAL_COLOR,
            "legend.frameon": False,
        }
    )


def _resolve_setup_label(experiment_dir: Path) -> str:
    summary_path = experiment_dir / SETUP_SUMMARY_FILE_NAME
    if summary_path.exists():
        with summary_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        setup_id = str(payload.get("SetupID", "")).strip()
        if setup_id:
            return setup_id
    return experiment_dir.name


def load_experiment_artifacts(experiment_dir: str | Path) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    resolved_dir = Path(experiment_dir).resolve()
    predictions_path = resolved_dir / PREDICTIONS_FILE_NAME
    monthly_metrics_path = resolved_dir / MONTHLY_METRICS_FILE_NAME

    if not predictions_path.exists():
        raise FileNotFoundError(f"Missing predictions artifact: {predictions_path}")
    if not monthly_metrics_path.exists():
        raise FileNotFoundError(f"Missing monthly metrics artifact: {monthly_metrics_path}")

    predictions = pd.read_csv(predictions_path)
    monthly_metrics = pd.read_csv(monthly_metrics_path)
    setup_label = _resolve_setup_label(resolved_dir)
    return predictions, monthly_metrics, setup_label


def _prepare_split_predictions(predictions: pd.DataFrame, split_name: str) -> pd.DataFrame:
    required_columns = {
        "Date",
        "Split",
        "AssetID",
        "AssetName",
        "AssetGroup",
        "realized_risk",
        "PredictedRisk",
        "realized_rank",
        "PredictedRank",
    }
    missing = sorted(required_columns.difference(predictions.columns))
    if missing:
        raise ValueError(f"Predictions frame is missing required columns: {', '.join(missing)}")

    subset = predictions.loc[predictions["Split"].astype(str).eq(split_name)].copy()
    if subset.empty:
        raise ValueError(f"No prediction rows found for split {split_name}.")

    subset["Date"] = subset["Date"].astype(str)
    asset_counts = subset.groupby("Date")["AssetID"].transform("count").astype(float)
    denominator = np.where(asset_counts > 1.0, asset_counts - 1.0, 1.0)
    subset["RealizedRankPct"] = (pd.to_numeric(subset["realized_rank"], errors="coerce") - 1.0) / denominator
    if "PredictedRankPct" not in subset.columns:
        subset["PredictedRankPct"] = (pd.to_numeric(subset["PredictedRank"], errors="coerce") - 1.0) / denominator
    subset["RankGap"] = pd.to_numeric(subset["PredictedRank"], errors="coerce") - pd.to_numeric(
        subset["realized_rank"], errors="coerce"
    )
    subset["AbsoluteRankGap"] = subset["RankGap"].abs()
    subset["PredictionError"] = pd.to_numeric(subset["PredictedRisk"], errors="coerce") - pd.to_numeric(
        subset["realized_risk"], errors="coerce"
    )
    return subset.sort_values(["Date", "PredictedRank", "AssetID"]).reset_index(drop=True)


def _prepare_split_metrics(monthly_metrics: pd.DataFrame, split_name: str) -> pd.DataFrame:
    required_columns = {"date", "split", "active_assets", "spearman", "mse", "reward"}
    missing = sorted(required_columns.difference(monthly_metrics.columns))
    if missing:
        raise ValueError(f"Monthly metrics frame is missing required columns: {', '.join(missing)}")

    subset = monthly_metrics.loc[monthly_metrics["split"].astype(str).eq(split_name)].copy()
    if subset.empty:
        raise ValueError(f"No monthly metrics rows found for split {split_name}.")

    subset["date"] = pd.to_datetime(subset["date"], format=config.DATE_FORMAT_MONTHLY)
    numeric_columns = ["active_assets", "spearman", "mse", "reward"]
    subset[numeric_columns] = subset[numeric_columns].apply(pd.to_numeric, errors="coerce")
    return subset.sort_values("date").reset_index(drop=True)


def _save_figure(figure: plt.Figure, output_path: Path) -> None:
    figure.tight_layout()
    figure.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(figure)


def plot_risk_score_distribution(split_predictions: pd.DataFrame, output_path: str | Path, setup_label: str, split_name: str) -> Path:
    output_file = Path(output_path)
    ordered_groups = (
        split_predictions.groupby("AssetGroup", sort=False)["PredictedRisk"]
        .median()
        .sort_values()
        .index.tolist()
    )
    boxplot_data = [
        split_predictions.loc[split_predictions["AssetGroup"].eq(group_name), "PredictedRisk"].to_numpy()
        for group_name in ordered_groups
    ]

    figure, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    bins = np.linspace(0.0, 1.0, 21)

    axes[0].hist(
        split_predictions["realized_risk"],
        bins=bins,
        alpha=0.55,
        color=REALIZED_COLOR,
        edgecolor=PANEL_COLOR,
        label="Realized risk",
    )
    axes[0].hist(
        split_predictions["PredictedRisk"],
        bins=bins,
        alpha=0.7,
        color=PREDICTED_COLOR,
        edgecolor=PANEL_COLOR,
        label="Predicted risk score",
    )
    axes[0].axvline(split_predictions["PredictedRisk"].mean(), color=PREDICTED_COLOR, linestyle="--", linewidth=2)
    axes[0].axvline(split_predictions["realized_risk"].mean(), color=REALIZED_COLOR, linestyle="--", linewidth=2)
    axes[0].set_title(f"{split_name.title()} risk score distribution")
    axes[0].set_xlabel("Risk score")
    axes[0].set_ylabel("Asset-month count")
    axes[0].legend(loc="upper left")

    boxplot = axes[1].boxplot(
        boxplot_data,
        tick_labels=ordered_groups,
        patch_artist=True,
        medianprops={"color": PANEL_COLOR, "linewidth": 2},
        boxprops={"edgecolor": PANEL_COLOR},
        whiskerprops={"color": GRID_COLOR},
        capprops={"color": GRID_COLOR},
        flierprops={"markerfacecolor": ACCENT_COLOR, "markeredgecolor": ACCENT_COLOR, "markersize": 4, "alpha": 0.45},
    )
    for patch in boxplot["boxes"]:
        patch.set_facecolor(PREDICTED_COLOR)
        patch.set_alpha(0.88)
    axes[1].set_title("Predicted score by asset group")
    axes[1].set_xlabel("Asset group")
    axes[1].set_ylabel("Predicted risk score")
    axes[1].tick_params(axis="x", rotation=25)

    figure.suptitle(f"{setup_label} | {split_name.title()} score diagnostics", fontsize=14, fontweight="bold", y=1.02)
    _save_figure(figure, output_file)
    return output_file


def plot_rank_alignment(split_predictions: pd.DataFrame, output_path: str | Path, setup_label: str, split_name: str) -> Path:
    output_file = Path(output_path)
    mean_abs_rank_gap = float(split_predictions["AbsoluteRankGap"].mean())

    figure, axis = plt.subplots(figsize=(7.2, 6.5))
    scatter = axis.scatter(
        split_predictions["RealizedRankPct"],
        split_predictions["PredictedRankPct"],
        c=split_predictions["AbsoluteRankGap"],
        cmap="viridis",
        s=42,
        alpha=0.82,
        edgecolors="none",
    )
    axis.plot([0.0, 1.0], [0.0, 1.0], color=ACCENT_COLOR, linestyle="--", linewidth=2, label="Perfect rank alignment")
    axis.set_xlim(-0.02, 1.02)
    axis.set_ylim(-0.02, 1.02)
    axis.set_title(f"{split_name.title()} predicted rank vs realized rank")
    axis.set_xlabel("Realized rank percentile within month")
    axis.set_ylabel("Predicted rank percentile within month")
    axis.legend(loc="upper left")
    axis.text(
        0.04,
        0.96,
        f"Mean absolute rank gap: {mean_abs_rank_gap:.2f}",
        transform=axis.transAxes,
        va="top",
        ha="left",
        fontsize=10,
        bbox={"facecolor": PANEL_COLOR, "edgecolor": GRID_COLOR, "boxstyle": "round,pad=0.4"},
    )
    colorbar = figure.colorbar(scatter, ax=axis, shrink=0.9)
    colorbar.set_label("Absolute rank gap")
    figure.suptitle(f"{setup_label} | {split_name.title()} rank alignment", fontsize=14, fontweight="bold", y=1.02)
    _save_figure(figure, output_file)
    return output_file


def plot_monthly_performance(split_metrics: pd.DataFrame, output_path: str | Path, setup_label: str, split_name: str) -> Path:
    output_file = Path(output_path)
    reward_best_index = split_metrics["reward"].idxmax()
    reward_best_row = split_metrics.loc[reward_best_index]

    month_labels = split_metrics["date"].dt.strftime(config.MONTH_LABEL_FORMAT)
    x_positions = np.arange(len(split_metrics))

    figure, axis = plt.subplots(figsize=(13, 5.2))
    axis.plot(x_positions, split_metrics["reward"], color=PREDICTED_COLOR, marker="o", linewidth=2.4, label="Reward")
    axis.plot(x_positions, split_metrics["spearman"], color=ACCENT_COLOR, marker="D", linewidth=2.0, label="Spearman")
    axis.scatter(
        [split_metrics.index.get_loc(reward_best_index)],
        [reward_best_row["reward"]],
        color=REALIZED_COLOR,
        s=85,
        zorder=4,
        label=f"Best reward month: {reward_best_row['date'].strftime(config.DATE_FORMAT_MONTHLY)}",
    )
    axis.set_xticks(x_positions, month_labels, rotation=30, ha="right")
    axis.set_ylabel("Metric value")
    axis.set_xlabel("Decision month")
    axis.set_ylim(0.0, min(1.0, float(split_metrics[["reward", "spearman"]].max().max()) + 0.08))
    axis.set_title(f"{split_name.title()} month-by-month performance")
    axis.legend(loc="lower right")
    axis.annotate(
        f"{reward_best_row['reward']:.4f}",
        xy=(split_metrics.index.get_loc(reward_best_index), reward_best_row["reward"]),
        xytext=(8, 10),
        textcoords="offset points",
        fontsize=10,
        color=REALIZED_COLOR,
    )
    figure.suptitle(f"{setup_label} | {split_name.title()} monthly performance", fontsize=14, fontweight="bold", y=1.02)
    _save_figure(figure, output_file)
    return output_file


def plot_best_month_rank_comparison(
    best_month_predictions: pd.DataFrame,
    output_path: str | Path,
    setup_label: str,
    split_name: str,
    best_month_label: str,
    best_month_reward: float,
    best_month_spearman: float,
) -> Path:
    output_file = Path(output_path)
    frame = best_month_predictions.sort_values(["realized_rank", "PredictedRank", "AssetID"]).reset_index(drop=True)
    figure_height = max(8.0, 0.34 * len(frame))
    figure, axis = plt.subplots(figsize=(11.5, figure_height))

    y_positions = np.arange(len(frame))
    max_rank_gap = float(frame["AbsoluteRankGap"].max()) if not frame.empty else 1.0
    if math.isclose(max_rank_gap, 0.0):
        max_rank_gap = 1.0
    color_scale = plt.cm.YlOrRd(frame["AbsoluteRankGap"] / max_rank_gap)

    for y_position, realized_rank, predicted_rank, color in zip(
        y_positions, frame["realized_rank"], frame["PredictedRank"], color_scale, strict=False
    ):
        axis.plot([realized_rank, predicted_rank], [y_position, y_position], color=color, linewidth=2.2, alpha=0.95)

    axis.scatter(frame["realized_rank"], y_positions, color=REALIZED_COLOR, s=44, label="Realized rank", zorder=3)
    axis.scatter(frame["PredictedRank"], y_positions, color=PREDICTED_COLOR, s=44, marker="D", label="Predicted rank", zorder=3)
    axis.set_yticks(y_positions, frame["AssetID"].tolist())
    axis.invert_yaxis()
    axis.set_xlabel("Rank within month")
    axis.set_ylabel("Asset")
    axis.set_title(f"Rank shifts in best {split_name} month: {best_month_label}")
    axis.legend(loc="upper right")
    axis.text(
        0.02,
        1.01,
        f"Reward {best_month_reward:.4f} | Spearman {best_month_spearman:.4f}",
        transform=axis.transAxes,
        ha="left",
        va="bottom",
        fontsize=10,
    )
    figure.suptitle(f"{setup_label} | Best {split_name.title()} month rank comparison", fontsize=14, fontweight="bold", y=1.01)
    _save_figure(figure, output_file)
    return output_file


def plot_score_calibration(split_predictions: pd.DataFrame, output_path: str | Path, setup_label: str, split_name: str) -> Path:
    output_file = Path(output_path)
    frame = split_predictions.copy()
    frame["CalibrationBin"] = pd.qcut(frame["PredictedRisk"], q=10, duplicates="drop")
    calibration = (
        frame.groupby("CalibrationBin", observed=True)
        .agg(
            mean_predicted=("PredictedRisk", "mean"),
            mean_realized=("realized_risk", "mean"),
            rows=("AssetID", "count"),
        )
        .reset_index(drop=True)
    )
    calibration["bin_label"] = [f"Q{i}" for i in range(1, len(calibration) + 1)]

    figure, axis = plt.subplots(figsize=(9.5, 5.5))
    axis.plot(
        calibration["mean_predicted"],
        calibration["mean_realized"],
        marker="o",
        color=PREDICTED_COLOR,
        linewidth=2.4,
    )
    bounds = [
        float(min(calibration["mean_predicted"].min(), calibration["mean_realized"].min())),
        float(max(calibration["mean_predicted"].max(), calibration["mean_realized"].max())),
    ]
    padding = 0.02
    axis.plot(
        [bounds[0] - padding, bounds[1] + padding],
        [bounds[0] - padding, bounds[1] + padding],
        color=ACCENT_COLOR,
        linestyle="--",
        linewidth=1.8,
        label="Perfect calibration",
    )
    for _, row in calibration.iterrows():
        axis.annotate(row["bin_label"], (row["mean_predicted"], row["mean_realized"]), textcoords="offset points", xytext=(4, 4))
    axis.set_xlabel("Mean predicted risk score by score decile")
    axis.set_ylabel("Mean realized risk by score decile")
    axis.set_title(f"{split_name.title()} score calibration")
    axis.legend(loc="upper left")
    figure.suptitle(f"{setup_label} | {split_name.title()} calibration", fontsize=14, fontweight="bold", y=1.02)
    _save_figure(figure, output_file)
    return output_file


def build_split_diagnostic_summary(split_predictions: pd.DataFrame, split_metrics: pd.DataFrame) -> dict[str, Any]:
    best_reward_row = split_metrics.loc[split_metrics["reward"].idxmax()]
    worst_reward_row = split_metrics.loc[split_metrics["reward"].idxmin()]
    best_spearman_row = split_metrics.loc[split_metrics["spearman"].idxmax()]

    return {
        "split_name": str(split_metrics.iloc[0]["split"]),
        "row_count": int(len(split_predictions)),
        "month_count": int(len(split_metrics)),
        "mean_predicted_risk": float(split_predictions["PredictedRisk"].mean()),
        "std_predicted_risk": float(split_predictions["PredictedRisk"].std(ddof=0)),
        "mean_realized_risk": float(split_predictions["realized_risk"].mean()),
        "mean_absolute_rank_gap": float(split_predictions["AbsoluteRankGap"].mean()),
        "best_month_by_reward": {
            "date": best_reward_row["date"].strftime(config.DATE_FORMAT_MONTHLY),
            "reward": float(best_reward_row["reward"]),
            "spearman": float(best_reward_row["spearman"]),
            "mse": float(best_reward_row["mse"]),
        },
        "worst_month_by_reward": {
            "date": worst_reward_row["date"].strftime(config.DATE_FORMAT_MONTHLY),
            "reward": float(worst_reward_row["reward"]),
            "spearman": float(worst_reward_row["spearman"]),
            "mse": float(worst_reward_row["mse"]),
        },
        "best_month_by_spearman": {
            "date": best_spearman_row["date"].strftime(config.DATE_FORMAT_MONTHLY),
            "reward": float(best_spearman_row["reward"]),
            "spearman": float(best_spearman_row["spearman"]),
            "mse": float(best_spearman_row["mse"]),
        },
    }


def generate_split_diagnostic_pack(
    experiment_dir: str | Path,
    split_name: str = "test",
    output_dir: str | Path | None = None,
) -> Path:
    _apply_plot_style()
    predictions, monthly_metrics, setup_label = load_experiment_artifacts(experiment_dir)
    split_predictions = _prepare_split_predictions(predictions, split_name=split_name)
    split_metrics = _prepare_split_metrics(monthly_metrics, split_name=split_name)

    best_month_row = split_metrics.loc[split_metrics["reward"].idxmax()]
    best_month_label = best_month_row["date"].strftime(config.DATE_FORMAT_MONTHLY)
    best_month_predictions = split_predictions.loc[split_predictions["Date"].eq(best_month_label)].copy()

    resolved_output_dir = (
        Path(output_dir).resolve()
        if output_dir is not None
        else (Path(experiment_dir).resolve() / f"{split_name}_visualizations")
    )
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    written_files = {
        "risk_distribution": str(
            plot_risk_score_distribution(
                split_predictions,
                resolved_output_dir / RISK_DISTRIBUTION_FILE_NAME,
                setup_label=setup_label,
                split_name=split_name,
            ).resolve()
        ),
        "rank_alignment": str(
            plot_rank_alignment(
                split_predictions,
                resolved_output_dir / RANK_ALIGNMENT_FILE_NAME,
                setup_label=setup_label,
                split_name=split_name,
            ).resolve()
        ),
        "monthly_performance": str(
            plot_monthly_performance(
                split_metrics,
                resolved_output_dir / MONTHLY_PERFORMANCE_FILE_NAME,
                setup_label=setup_label,
                split_name=split_name,
            ).resolve()
        ),
        "best_month_rank_comparison": str(
            plot_best_month_rank_comparison(
                best_month_predictions,
                resolved_output_dir / BEST_MONTH_RANK_FILE_NAME,
                setup_label=setup_label,
                split_name=split_name,
                best_month_label=best_month_label,
                best_month_reward=float(best_month_row["reward"]),
                best_month_spearman=float(best_month_row["spearman"]),
            ).resolve()
        ),
        "score_calibration": str(
            plot_score_calibration(
                split_predictions,
                resolved_output_dir / CALIBRATION_FILE_NAME,
                setup_label=setup_label,
                split_name=split_name,
            ).resolve()
        ),
    }

    summary_payload = build_split_diagnostic_summary(split_predictions, split_metrics)
    summary_payload["experiment_dir"] = str(Path(experiment_dir).resolve())
    summary_payload["setup_label"] = setup_label
    summary_payload["output_dir"] = str(resolved_output_dir)
    summary_payload["plot_files"] = written_files

    summary_path = resolved_output_dir / SUMMARY_FILE_NAME
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary_payload, handle, indent=2, sort_keys=True)

    return resolved_output_dir


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate diagnostic plots from saved experiment artifacts.")
    parser.add_argument("--experiment-dir", required=True, help="Artifact directory containing ranked_predictions.csv.")
    parser.add_argument(
        "--split-name",
        default="test",
        choices=["train", "inner_validation", "validation", "test"],
        help="Split to visualize.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory. Defaults to <experiment-dir>/<split-name>_visualizations.",
    )
    return parser


def main() -> None:
    parser = _build_cli_parser()
    args = parser.parse_args()

    output_dir = generate_split_diagnostic_pack(
        experiment_dir=args.experiment_dir,
        split_name=args.split_name,
        output_dir=args.output_dir,
    )
    summary_path = output_dir / SUMMARY_FILE_NAME
    with summary_path.open("r", encoding="utf-8") as handle:
        summary = json.load(handle)

    print(f"Saved diagnostic plots to {output_dir}")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
