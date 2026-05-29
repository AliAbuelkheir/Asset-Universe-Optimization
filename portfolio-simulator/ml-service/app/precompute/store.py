from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data import DAILY_MARKET_PATH, MONTHLY_PANEL_PATH, PREDICTIONS_PATH, RISK_BUCKETS
from ..paths import APP_ROOT, MODEL_ARTIFACTS_ROOT

SCHEMA_VERSION = "1"
GENERATOR_VERSION = "4"

PRECOMPUTED_ROOT = MODEL_ARTIFACTS_ROOT / "precomputed-simulations"
SIMULATION_STORE_PATH = PRECOMPUTED_ROOT / "simulation_store.sqlite"

RISK_LEVEL_ORDER = ("low", "medium", "high")
STRATEGY_IDS = (
    "optimizedPortfolio",
    "profileEqualWeight",
    "optimizerFullUniverse",
    "fullUniverseEqualWeight",
    "mvoFilteredUniverse",
    "mvoFullUniverse",
    "egx30",
)
STRATEGY_LABELS = {
    "optimizedPortfolio": "Profile optimizer portfolio",
    "profileEqualWeight": "Profile equal weights",
    "optimizerFullUniverse": "Full-universe optimizer benchmark",
    "fullUniverseEqualWeight": "Full-universe equal weights",
    "mvoFilteredUniverse": "Profile MVO benchmark",
    "mvoFullUniverse": "Full-universe MVO benchmark",
    "egx30": "EGX30",
}
CANONICAL_TEXT_SUFFIXES = {".csv", ".json"}

DEPLOYMENT_ROOT = MODEL_ARTIFACTS_ROOT / "deployment"
OPTIMIZER_MODEL_ROOT = DEPLOYMENT_ROOT / "models"
MACRO_ROOT = DEPLOYMENT_ROOT / "data"
BEST_MODEL_ROOT = MODEL_ARTIFACTS_ROOT / "ranked-risk-model" / "outputs" / "best_model"

TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "store_metadata": ("key", "value"),
    "source_artifacts": ("artifact_key", "relative_path", "sha256", "size_bytes"),
    "reportable_months": ("month", "split", "active_universe_count"),
    "risk_buckets": ("risk_level", "label", "min_rank_pct", "max_rank_pct", "description"),
    "decision_snapshots": (
        "decision_month",
        "risk_level",
        "active_universe_count",
        "selected_asset_count",
        "selected_optimizer_weight_sum",
        "selected_optimizer_decision_date",
        "full_optimizer_weight_sum",
        "full_optimizer_decision_date",
        "selected_mvo_weight_sum",
        "selected_mvo_decision_date",
        "full_mvo_weight_sum",
        "full_mvo_decision_date",
    ),
    "decision_assets": (
        "decision_month",
        "risk_level",
        "asset_id",
        "asset_name",
        "asset_group",
        "active_order",
        "selected_order",
        "selected_by_filter",
        "equal_weight",
        "optimized_weight",
    ),
    "strategy_weights": ("decision_month", "risk_level", "strategy_id", "asset_id", "weight"),
    "strategy_monthly_returns": (
        "decision_month",
        "risk_level",
        "return_month",
        "strategy_id",
        "monthly_return",
    ),
}


class PrecomputedStoreError(RuntimeError):
    pass


class PrecomputedStoreValidationError(PrecomputedStoreError):
    pass


@dataclass(frozen=True)
class SourceArtifactSpec:
    artifact_key: str
    path: Path


@dataclass(frozen=True)
class StoreValidationStatus:
    available: bool
    error: str | None
    validated_at_utc: str | None
    path: Path


_VALIDATION_LOCK = threading.Lock()
_VALIDATION_STATUS_BY_PATH: dict[str, StoreValidationStatus] = {}


def stable_json_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def risk_bucket_hash() -> str:
    return stable_json_hash({key: RISK_BUCKETS[key] for key in RISK_LEVEL_ORDER})


def strategy_set_hash() -> str:
    return stable_json_hash(list(STRATEGY_IDS))


def source_artifact_specs() -> list[SourceArtifactSpec]:
    specs = [
        SourceArtifactSpec("ranked_predictions", PREDICTIONS_PATH),
        SourceArtifactSpec("daily_market_series", DAILY_MARKET_PATH),
        SourceArtifactSpec("monthly_asset_panel", MONTHLY_PANEL_PATH),
        SourceArtifactSpec("best_model_zip", BEST_MODEL_ROOT / "best_model.zip"),
        SourceArtifactSpec("final_model_zip", BEST_MODEL_ROOT / "final_model.zip"),
        SourceArtifactSpec("best_model_manifest", BEST_MODEL_ROOT / "best_model_manifest.json"),
    ]
    for tier in RISK_LEVEL_ORDER:
        specs.extend(
            [
                SourceArtifactSpec(f"optimizer_model_{tier}", OPTIMIZER_MODEL_ROOT / f"ppo_{tier}_seed42_setbased.zip"),
                SourceArtifactSpec(f"optimizer_vecnorm_{tier}", OPTIMIZER_MODEL_ROOT / f"vecnorm_{tier}_seed42_setbased.pkl"),
            ]
        )
    specs.extend(
        [
            SourceArtifactSpec("macro_inflation", MACRO_ROOT / "Inflations Historical.xlsx"),
            SourceArtifactSpec("macro_interest_rates", MACRO_ROOT / "Monthly Interest Rates Historical.xlsx"),
        ]
    )
    return specs


def _canonical_artifact_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix.lower() in CANONICAL_TEXT_SUFFIXES:
        return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return data


def file_sha256(path: Path) -> str:
    return hashlib.sha256(_canonical_artifact_bytes(path)).hexdigest()


def file_fingerprint_size(path: Path) -> int:
    return len(_canonical_artifact_bytes(path))


def relative_artifact_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(APP_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def current_source_artifacts() -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    for spec in source_artifact_specs():
        if not spec.path.exists():
            raise PrecomputedStoreValidationError(f"Missing source artifact for precomputed store: {spec.path}")
        artifacts[spec.artifact_key] = {
            "relative_path": relative_artifact_path(spec.path),
            "sha256": file_sha256(spec.path),
            "size_bytes": file_fingerprint_size(spec.path),
        }
    return artifacts


def _store_path(path: Path | None = None) -> Path:
    return path if path is not None else SIMULATION_STORE_PATH


def _resolved_store_path(path: Path | None = None) -> Path:
    return _store_path(path).resolve()


def connect_store(path: Path | None = None) -> sqlite3.Connection:
    resolved_path = _resolved_store_path(path)
    if not resolved_path.exists():
        raise FileNotFoundError(
            f"Missing precomputed simulation store at {resolved_path}. "
            "Regenerate it with: cd portfolio-simulator/ml-service && "
            "python -m app.precompute.regenerate_simulation_store"
        )
    connection = sqlite3.connect(resolved_path)
    connection.row_factory = sqlite3.Row
    return connection


def connect_validated_store(path: Path | None = None) -> sqlite3.Connection:
    connection = connect_store(path)
    try:
        validate_store_connection(connection)
    except Exception:
        connection.close()
        raise
    return connection


def validate_precomputed_store(path: Path | None = None, *, force: bool = False) -> StoreValidationStatus:
    resolved_path = _resolved_store_path(path)
    cache_key = str(resolved_path)
    with _VALIDATION_LOCK:
        cached_status = _VALIDATION_STATUS_BY_PATH.get(cache_key)
        if cached_status is not None and not force:
            return cached_status

        try:
            with connect_validated_store(resolved_path) as _connection:
                status = StoreValidationStatus(
                    available=True,
                    error=None,
                    validated_at_utc=datetime.now(timezone.utc).isoformat(),
                    path=resolved_path,
                )
        except (FileNotFoundError, PrecomputedStoreError, sqlite3.DatabaseError) as exc:
            status = StoreValidationStatus(
                available=False,
                error=str(exc),
                validated_at_utc=datetime.now(timezone.utc).isoformat(),
                path=resolved_path,
            )
        _VALIDATION_STATUS_BY_PATH[cache_key] = status
        return status


def connect_runtime_store(path: Path | None = None) -> sqlite3.Connection:
    status = validate_precomputed_store(path)
    if not status.available:
        raise PrecomputedStoreValidationError(status.error or "Precomputed simulation store is unavailable.")
    return connect_store(status.path)


def precomputed_store_available(path: Path | None = None) -> bool:
    return validate_precomputed_store(path).available


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {str(row["name"]) for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}


def _validate_schema(connection: sqlite3.Connection) -> None:
    tables = {
        str(row["name"])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    missing_tables = sorted(set(TABLE_COLUMNS).difference(tables))
    if missing_tables:
        raise PrecomputedStoreValidationError(f"Precomputed store is missing table(s): {missing_tables}")
    for table_name, expected_columns in TABLE_COLUMNS.items():
        actual_columns = _table_columns(connection, table_name)
        missing_columns = sorted(set(expected_columns).difference(actual_columns))
        if missing_columns:
            raise PrecomputedStoreValidationError(
                f"Precomputed store table {table_name} is missing column(s): {missing_columns}"
            )


def _metadata(connection: sqlite3.Connection) -> dict[str, str]:
    return {
        str(row["key"]): str(row["value"])
        for row in connection.execute("SELECT key, value FROM store_metadata").fetchall()
    }


def _validate_metadata(connection: sqlite3.Connection) -> None:
    metadata = _metadata(connection)
    required = {
        "schema_version",
        "generated_at_utc",
        "generator_version",
        "python_version",
        "risk_bucket_hash",
        "strategy_set_hash",
    }
    missing = sorted(required.difference(metadata))
    if missing:
        raise PrecomputedStoreValidationError(f"Precomputed store metadata is missing key(s): {missing}")
    if metadata["schema_version"] != SCHEMA_VERSION:
        raise PrecomputedStoreValidationError(
            f"Precomputed store schema version {metadata['schema_version']} does not match runtime {SCHEMA_VERSION}."
        )
    if metadata["generator_version"] != GENERATOR_VERSION:
        raise PrecomputedStoreValidationError(
            f"Precomputed store generator version {metadata['generator_version']} does not match runtime "
            f"{GENERATOR_VERSION}."
        )
    if metadata["risk_bucket_hash"] != risk_bucket_hash():
        raise PrecomputedStoreValidationError("Precomputed store risk bucket hash does not match runtime config.")
    if metadata["strategy_set_hash"] != strategy_set_hash():
        raise PrecomputedStoreValidationError("Precomputed store strategy set hash does not match runtime config.")


def _validate_source_artifacts(connection: sqlite3.Connection) -> None:
    expected = current_source_artifacts()
    stored = {
        str(row["artifact_key"]): {
            "relative_path": str(row["relative_path"]),
            "sha256": str(row["sha256"]),
            "size_bytes": int(row["size_bytes"]),
        }
        for row in connection.execute(
            "SELECT artifact_key, relative_path, sha256, size_bytes FROM source_artifacts"
        ).fetchall()
    }
    expected_keys = set(expected)
    stored_keys = set(stored)
    if expected_keys != stored_keys:
        missing = sorted(expected_keys.difference(stored_keys))
        extra = sorted(stored_keys.difference(expected_keys))
        raise PrecomputedStoreValidationError(
            f"Precomputed store source artifact keys do not match runtime artifacts; missing={missing}, extra={extra}."
        )
    mismatched = [
        key
        for key in sorted(expected_keys)
        if stored[key]["sha256"] != expected[key]["sha256"]
        or stored[key]["size_bytes"] != expected[key]["size_bytes"]
        or stored[key]["relative_path"] != expected[key]["relative_path"]
    ]
    if mismatched:
        raise PrecomputedStoreValidationError(
            f"Precomputed store is stale for source artifact(s): {', '.join(mismatched)}"
        )


def _query_scalar(connection: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> int:
    row = connection.execute(query, params).fetchone()
    return int(row[0]) if row is not None else 0


def _validate_coverage(connection: sqlite3.Connection) -> None:
    months = [str(row["month"]) for row in connection.execute("SELECT month FROM reportable_months ORDER BY month")]
    if not months:
        raise PrecomputedStoreValidationError("Precomputed store does not contain reportable months.")
    risk_levels = [
        str(row["risk_level"])
        for row in connection.execute("SELECT risk_level FROM risk_buckets ORDER BY risk_level").fetchall()
    ]
    if sorted(risk_levels) != sorted(RISK_LEVEL_ORDER):
        raise PrecomputedStoreValidationError(f"Precomputed store risk levels are invalid: {risk_levels}")

    for month in months:
        forward_months = [candidate for candidate in months if candidate >= month]
        for risk_level in RISK_LEVEL_ORDER:
            snapshot_count = _query_scalar(
                connection,
                "SELECT COUNT(*) FROM decision_snapshots WHERE decision_month = ? AND risk_level = ?",
                (month, risk_level),
            )
            if snapshot_count != 1:
                raise PrecomputedStoreValidationError(
                    f"Precomputed store missing decision snapshot for {month}/{risk_level}."
                )
            asset_count = _query_scalar(
                connection,
                "SELECT COUNT(*) FROM decision_assets WHERE decision_month = ? AND risk_level = ?",
                (month, risk_level),
            )
            if asset_count <= 0:
                raise PrecomputedStoreValidationError(f"Precomputed store missing decision assets for {month}/{risk_level}.")
            for strategy_id in STRATEGY_IDS:
                weight_count = _query_scalar(
                    connection,
                    """
                    SELECT COUNT(*) FROM strategy_weights
                    WHERE decision_month = ? AND risk_level = ? AND strategy_id = ?
                    """,
                    (month, risk_level, strategy_id),
                )
                if weight_count <= 0:
                    raise PrecomputedStoreValidationError(
                        f"Precomputed store missing {strategy_id} weights for {month}/{risk_level}."
                    )
                return_count = _query_scalar(
                    connection,
                    """
                    SELECT COUNT(*) FROM strategy_monthly_returns
                    WHERE decision_month = ? AND risk_level = ? AND strategy_id = ?
                    """,
                    (month, risk_level, strategy_id),
                )
                if return_count != len(forward_months):
                    raise PrecomputedStoreValidationError(
                        f"Precomputed store has {return_count} {strategy_id} returns for {month}/{risk_level}; "
                        f"expected {len(forward_months)}."
                    )


def validate_store_connection(connection: sqlite3.Connection) -> None:
    _validate_schema(connection)
    _validate_metadata(connection)
    _validate_source_artifacts(connection)
    _validate_coverage(connection)


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE store_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE source_artifacts (
            artifact_key TEXT PRIMARY KEY,
            relative_path TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            size_bytes INTEGER NOT NULL
        );

        CREATE TABLE reportable_months (
            month TEXT PRIMARY KEY,
            split TEXT NOT NULL,
            active_universe_count INTEGER NOT NULL
        );

        CREATE TABLE risk_buckets (
            risk_level TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            min_rank_pct REAL NOT NULL,
            max_rank_pct REAL NOT NULL,
            description TEXT NOT NULL
        );

        CREATE TABLE decision_snapshots (
            decision_month TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            active_universe_count INTEGER NOT NULL,
            selected_asset_count INTEGER NOT NULL,
            selected_optimizer_weight_sum REAL NOT NULL,
            selected_optimizer_decision_date TEXT NOT NULL,
            full_optimizer_weight_sum REAL NOT NULL,
            full_optimizer_decision_date TEXT NOT NULL,
            selected_mvo_weight_sum REAL NOT NULL,
            selected_mvo_decision_date TEXT NOT NULL,
            full_mvo_weight_sum REAL NOT NULL,
            full_mvo_decision_date TEXT NOT NULL,
            PRIMARY KEY (decision_month, risk_level),
            FOREIGN KEY (decision_month) REFERENCES reportable_months(month),
            FOREIGN KEY (risk_level) REFERENCES risk_buckets(risk_level)
        );

        CREATE TABLE decision_assets (
            decision_month TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            asset_id TEXT NOT NULL,
            asset_name TEXT NOT NULL,
            asset_group TEXT NOT NULL,
            active_order INTEGER NOT NULL,
            selected_order INTEGER,
            selected_by_filter INTEGER NOT NULL,
            equal_weight REAL,
            optimized_weight REAL,
            PRIMARY KEY (decision_month, risk_level, asset_id),
            FOREIGN KEY (decision_month, risk_level) REFERENCES decision_snapshots(decision_month, risk_level)
        );

        CREATE TABLE strategy_weights (
            decision_month TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            strategy_id TEXT NOT NULL,
            asset_id TEXT NOT NULL,
            weight REAL NOT NULL,
            PRIMARY KEY (decision_month, risk_level, strategy_id, asset_id),
            FOREIGN KEY (decision_month, risk_level) REFERENCES decision_snapshots(decision_month, risk_level)
        );

        CREATE TABLE strategy_monthly_returns (
            decision_month TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            return_month TEXT NOT NULL,
            strategy_id TEXT NOT NULL,
            monthly_return REAL NOT NULL,
            PRIMARY KEY (decision_month, risk_level, return_month, strategy_id),
            FOREIGN KEY (decision_month, risk_level) REFERENCES decision_snapshots(decision_month, risk_level),
            FOREIGN KEY (return_month) REFERENCES reportable_months(month)
        );

        CREATE INDEX idx_decision_assets_decision
            ON decision_assets(decision_month, risk_level);
        CREATE INDEX idx_returns_decision
            ON strategy_monthly_returns(decision_month, risk_level);
        CREATE INDEX idx_returns_return_strategy
            ON strategy_monthly_returns(return_month, risk_level, strategy_id);
        CREATE INDEX idx_weights_risk_strategy
            ON strategy_weights(risk_level, strategy_id);
        """
    )


def base_metadata() -> dict[str, str]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "python_version": sys.version.split()[0],
        "risk_bucket_hash": risk_bucket_hash(),
        "strategy_set_hash": strategy_set_hash(),
    }
