from __future__ import annotations

import argparse
import math
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..data import RISK_BUCKETS, VALID_SPLITS, read_daily_market_index, read_monthly_returns, read_predictions, select_assets
from ..metrics import egx30_returns, equal_weights, index_monthly_returns, portfolio_monthly_returns
from ..mvo import run_mvo_allocation
from ..optimizer import run_weight_optimizer
from .store import (
    PRECOMPUTED_ROOT,
    RISK_LEVEL_ORDER,
    SIMULATION_STORE_PATH,
    STRATEGY_IDS,
    base_metadata,
    create_schema,
    current_source_artifacts,
    validate_store_connection,
)


def _validate_weights(
    *,
    strategy_id: str,
    target_month: str,
    requested_asset_ids: list[str],
    weights: dict[str, float],
) -> None:
    requested_set = {str(asset_id) for asset_id in requested_asset_ids}
    actual_set = {str(asset_id) for asset_id in weights}
    missing = sorted(requested_set.difference(actual_set))
    extra = sorted(actual_set.difference(requested_set))
    if missing or extra:
        raise ValueError(
            f"{strategy_id} weights for {target_month} do not match requested assets; "
            f"missing={missing}, extra={extra}."
        )
    values = [float(weights[str(asset_id)]) for asset_id in requested_asset_ids]
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError(f"{strategy_id} weights for {target_month} contain non-finite values.")
    if any(value < -1e-12 for value in values):
        raise ValueError(f"{strategy_id} weights for {target_month} contain negative values.")
    total = float(sum(values))
    if abs(total - 1.0) > 1e-4:
        raise ValueError(f"{strategy_id} weights for {target_month} must sum to 1.0; got {total:.8f}.")


def _insert_metadata(connection: sqlite3.Connection) -> None:
    metadata = {
        **base_metadata(),
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    connection.executemany(
        "INSERT INTO store_metadata(key, value) VALUES (?, ?)",
        sorted(metadata.items()),
    )


def _insert_source_artifacts(connection: sqlite3.Connection) -> None:
    rows = [
        (artifact_key, values["relative_path"], values["sha256"], values["size_bytes"])
        for artifact_key, values in sorted(current_source_artifacts().items())
    ]
    connection.executemany(
        """
        INSERT INTO source_artifacts(artifact_key, relative_path, sha256, size_bytes)
        VALUES (?, ?, ?, ?)
        """,
        rows,
    )


def _reportable_month_rows(predictions: Any, monthly_returns: Any) -> list[tuple[str, str, int]]:
    subset = predictions.loc[predictions["Split"].isin(VALID_SPLITS)].copy()
    monthly_return_months = set(monthly_returns["Date"].astype(str))
    subset = subset.loc[subset["Date"].astype(str).isin(monthly_return_months)].copy()
    rows: list[tuple[str, str, int]] = []
    for month, frame in subset.groupby("Date", sort=True):
        splits = sorted(set(frame["Split"].astype(str)))
        if len(splits) != 1:
            raise ValueError(f"Month {month} has multiple reportable splits: {splits}")
        rows.append((str(month), splits[0], int(frame["AssetID"].count())))
    if not rows:
        raise ValueError("No reportable validation/test months are available for precomputation.")
    return rows


def _insert_reportable_months(connection: sqlite3.Connection, month_rows: list[tuple[str, str, int]]) -> None:
    connection.executemany(
        """
        INSERT INTO reportable_months(month, split, active_universe_count)
        VALUES (?, ?, ?)
        """,
        month_rows,
    )


def _insert_risk_buckets(connection: sqlite3.Connection) -> None:
    rows = [
        (
            risk_level,
            str(RISK_BUCKETS[risk_level]["label"]),
            float(RISK_BUCKETS[risk_level]["minRankPct"]),
            float(RISK_BUCKETS[risk_level]["maxRankPct"]),
            str(RISK_BUCKETS[risk_level]["description"]),
        )
        for risk_level in RISK_LEVEL_ORDER
    ]
    connection.executemany(
        """
        INSERT INTO risk_buckets(risk_level, label, min_rank_pct, max_rank_pct, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_decision_assets(
    *,
    connection: sqlite3.Connection,
    month: str,
    risk_level: str,
    active_universe: Any,
    selected_asset_ids: list[str],
    selected_equal_weights: dict[str, float],
    selected_optimizer_weights: dict[str, float],
) -> None:
    selected_id_set = set(selected_asset_ids)
    selected_order = {asset_id: index for index, asset_id in enumerate(selected_asset_ids)}
    rows = []
    for active_order, row in enumerate(active_universe.itertuples(index=False)):
        asset_id = str(row.AssetID)
        selected = asset_id in selected_id_set
        rows.append(
            (
                month,
                risk_level,
                asset_id,
                str(row.AssetName),
                str(row.AssetGroup),
                active_order,
                selected_order.get(asset_id),
                1 if selected else 0,
                selected_equal_weights.get(asset_id) if selected else None,
                selected_optimizer_weights.get(asset_id) if selected else None,
            )
        )
    connection.executemany(
        """
        INSERT INTO decision_assets(
            decision_month,
            risk_level,
            asset_id,
            asset_name,
            asset_group,
            active_order,
            selected_order,
            selected_by_filter,
            equal_weight,
            optimized_weight
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_strategy_weights(
    *,
    connection: sqlite3.Connection,
    month: str,
    risk_level: str,
    weights_by_strategy: dict[str, dict[str, float]],
) -> None:
    rows = []
    for strategy_id in STRATEGY_IDS:
        for asset_id, weight in sorted(weights_by_strategy[strategy_id].items()):
            rows.append((month, risk_level, strategy_id, str(asset_id), float(weight)))
    connection.executemany(
        """
        INSERT INTO strategy_weights(decision_month, risk_level, strategy_id, asset_id, weight)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_strategy_returns(
    *,
    connection: sqlite3.Connection,
    month: str,
    risk_level: str,
    forward_months: list[str],
    monthly_return_index: dict[tuple[str, str], float],
    weights_by_strategy: dict[str, dict[str, float]],
) -> None:
    rows = []
    for strategy_id in STRATEGY_IDS:
        if strategy_id == "egx30":
            returns = egx30_returns(monthly_return_index, forward_months)
        else:
            returns = portfolio_monthly_returns(monthly_return_index, forward_months, weights_by_strategy[strategy_id])
        if len(returns) != len(forward_months):
            raise ValueError(f"{strategy_id} returned an unexpected number of monthly returns for {month}/{risk_level}.")
        for return_month, monthly_return in zip(forward_months, returns):
            if not math.isfinite(float(monthly_return)):
                raise ValueError(f"{strategy_id} return for {month}/{risk_level}/{return_month} is non-finite.")
            rows.append((month, risk_level, return_month, strategy_id, float(monthly_return)))
    connection.executemany(
        """
        INSERT INTO strategy_monthly_returns(
            decision_month,
            risk_level,
            return_month,
            strategy_id,
            monthly_return
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )


def generate_store(output_path: Path = SIMULATION_STORE_PATH) -> Path:
    predictions = read_predictions()
    monthly_returns = read_monthly_returns()
    monthly_return_index = index_monthly_returns(monthly_returns)
    daily_market = read_daily_market_index()
    month_rows = _reportable_month_rows(predictions, monthly_returns)
    reportable_months = [month for month, _split, _count in month_rows]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    if temp_path.exists():
        temp_path.unlink()

    connection = sqlite3.connect(temp_path)
    connection.row_factory = sqlite3.Row
    try:
        create_schema(connection)
        _insert_metadata(connection)
        _insert_source_artifacts(connection)
        _insert_reportable_months(connection, month_rows)
        _insert_risk_buckets(connection)

        for month in reportable_months:
            same_month_universe = predictions.loc[
                predictions["Date"].eq(month) & predictions["Split"].isin(VALID_SPLITS)
            ].copy()
            if same_month_universe.empty:
                raise ValueError(f"No reportable predictions found for month {month}")
            all_universe_asset_ids = same_month_universe["AssetID"].astype(str).tolist()
            forward_months = [candidate for candidate in reportable_months if candidate >= month]

            for risk_level in RISK_LEVEL_ORDER:
                selected = select_assets(month, risk_level, predictions=predictions)
                selected_asset_ids = selected["AssetID"].astype(str).tolist()
                selected_equal_weights = equal_weights(selected_asset_ids)
                full_universe_equal_weights = equal_weights(all_universe_asset_ids)

                optimized_selected = run_weight_optimizer(
                    tier=risk_level,
                    target_month=month,
                    asset_ids=selected_asset_ids,
                    daily_market=daily_market,
                )
                optimized_full = run_weight_optimizer(
                    tier=risk_level,
                    target_month=month,
                    asset_ids=all_universe_asset_ids,
                    daily_market=daily_market,
                )
                mvo_selected = run_mvo_allocation(
                    risk_level=risk_level,
                    target_month=month,
                    asset_ids=selected_asset_ids,
                    daily_market=daily_market,
                )
                mvo_full = run_mvo_allocation(
                    risk_level=risk_level,
                    target_month=month,
                    asset_ids=all_universe_asset_ids,
                    daily_market=daily_market,
                )

                weights_by_strategy = {
                    "optimizedPortfolio": optimized_selected.weights,
                    "profileEqualWeight": selected_equal_weights,
                    "optimizerFullUniverse": optimized_full.weights,
                    "fullUniverseEqualWeight": full_universe_equal_weights,
                    "mvoFilteredUniverse": mvo_selected.weights,
                    "mvoFullUniverse": mvo_full.weights,
                    "egx30": {"EGX30": 1.0},
                }
                _validate_weights(
                    strategy_id="optimizedPortfolio",
                    target_month=month,
                    requested_asset_ids=selected_asset_ids,
                    weights=optimized_selected.weights,
                )
                _validate_weights(
                    strategy_id="profileEqualWeight",
                    target_month=month,
                    requested_asset_ids=selected_asset_ids,
                    weights=selected_equal_weights,
                )
                _validate_weights(
                    strategy_id="optimizerFullUniverse",
                    target_month=month,
                    requested_asset_ids=all_universe_asset_ids,
                    weights=optimized_full.weights,
                )
                _validate_weights(
                    strategy_id="fullUniverseEqualWeight",
                    target_month=month,
                    requested_asset_ids=all_universe_asset_ids,
                    weights=full_universe_equal_weights,
                )
                _validate_weights(
                    strategy_id="mvoFilteredUniverse",
                    target_month=month,
                    requested_asset_ids=selected_asset_ids,
                    weights=mvo_selected.weights,
                )
                _validate_weights(
                    strategy_id="mvoFullUniverse",
                    target_month=month,
                    requested_asset_ids=all_universe_asset_ids,
                    weights=mvo_full.weights,
                )

                connection.execute(
                    """
                    INSERT INTO decision_snapshots(
                        decision_month,
                        risk_level,
                        active_universe_count,
                        selected_asset_count,
                        selected_optimizer_weight_sum,
                        selected_optimizer_decision_date,
                        full_optimizer_weight_sum,
                        full_optimizer_decision_date,
                        selected_mvo_weight_sum,
                        selected_mvo_decision_date,
                        full_mvo_weight_sum,
                        full_mvo_decision_date
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        month,
                        risk_level,
                        len(all_universe_asset_ids),
                        len(selected_asset_ids),
                        float(optimized_selected.sum_check),
                        str(optimized_selected.decision_date),
                        float(optimized_full.sum_check),
                        str(optimized_full.decision_date),
                        float(mvo_selected.sum_check),
                        str(mvo_selected.decision_date),
                        float(mvo_full.sum_check),
                        str(mvo_full.decision_date),
                    ),
                )
                _insert_decision_assets(
                    connection=connection,
                    month=month,
                    risk_level=risk_level,
                    active_universe=same_month_universe,
                    selected_asset_ids=selected_asset_ids,
                    selected_equal_weights=selected_equal_weights,
                    selected_optimizer_weights=optimized_selected.weights,
                )
                _insert_strategy_weights(
                    connection=connection,
                    month=month,
                    risk_level=risk_level,
                    weights_by_strategy=weights_by_strategy,
                )
                _insert_strategy_returns(
                    connection=connection,
                    month=month,
                    risk_level=risk_level,
                    forward_months=forward_months,
                    monthly_return_index=monthly_return_index,
                    weights_by_strategy=weights_by_strategy,
                )

        connection.commit()
        validate_store_connection(connection)
    except Exception:
        connection.close()
        if temp_path.exists():
            temp_path.unlink()
        raise
    else:
        connection.close()
        os.replace(temp_path, output_path)
        return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate the precomputed portfolio simulator SQLite store.")
    parser.add_argument(
        "--output",
        type=Path,
        default=SIMULATION_STORE_PATH,
        help=f"Output SQLite path. Defaults to {SIMULATION_STORE_PATH}",
    )
    args = parser.parse_args()
    output = generate_store(args.output)
    try:
        display = output.resolve().relative_to(PRECOMPUTED_ROOT.parent.resolve())
    except ValueError:
        display = output.resolve()
    print(f"Regenerated precomputed simulation store: {display}")


if __name__ == "__main__":
    main()
