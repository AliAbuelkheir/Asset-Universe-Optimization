"""Input / output schemas for the deployment package.

Using dataclasses + simple checks instead of Pydantic to avoid an extra
dependency. The structure mirrors what a typical REST API would expect.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Literal


@dataclass
class AssetTimeSeries:
    """OHLCV history for one asset, daily resolution.

    Open/High/Low/Volume are optional — if missing, we fall back to Close.
    Length must be >= 123 trading days (63 for the model's lookback + 60 for
    the longest rolling feature window).
    """
    asset: str
    dates: list[str]                # ISO YYYY-MM-DD
    close: list[float]
    open: list[float] | None = None
    high: list[float] | None = None
    low: list[float] | None = None
    volume: list[float] | None = None

    def __post_init__(self):
        n = len(self.dates)
        if len(self.close) != n:
            raise ValueError(f"{self.asset}: close length {len(self.close)} != dates length {n}")
        for name in ('open', 'high', 'low', 'volume'):
            v = getattr(self, name)
            if v is not None and len(v) != n:
                raise ValueError(
                    f"{self.asset}: {name} length {len(v)} != dates length {n}"
                )


@dataclass
class ConstraintsOverride:
    """Optional overrides applied AFTER the model's default tier constraints."""
    max_weight: float | None = None
    min_weight: float | None = None


@dataclass
class InferenceRequest:
    """The full input the deployment API expects."""
    tier: Literal['low', 'medium', 'high']
    asset_data: list[AssetTimeSeries] | str | dict[str, Any]  # list of asset series, CSV path, or in-memory frames
    target_month: str                        # 'YYYY-MM'
    input_kind: Literal['raw_ohlcv', 'precomputed_features'] | None = None  # auto-detect if None
    constraints_override: ConstraintsOverride | None = None
    egx30_ohlcv: AssetTimeSeries | None = None  # optional EGX30 for rolling_beta_60

    def __post_init__(self):
        if self.tier not in ('low', 'medium', 'high'):
            raise ValueError(f"tier must be one of low/medium/high, got {self.tier!r}")
        if len(self.target_month) != 7 or self.target_month[4] != '-':
            raise ValueError(f"target_month must be 'YYYY-MM', got {self.target_month!r}")


@dataclass
class AssetWeight:
    asset: str
    weight: float


@dataclass
class InferenceResponse:
    """The full output the deployment API returns."""
    tier: str
    target_month: str
    decision_date: str
    lookback_window: int
    asset_weights: list[AssetWeight]    # sorted by weight descending
    cash_position: float                # always 0.0 (long-only, fully invested)
    sum_check: float                    # ~1.0 (sanity check)
    constraints_applied: dict           # what min/max/etc. were enforced
    model_version: str = 'setbased_seed42'
    package_version: str = '0.1.0'

    def to_dict(self) -> dict:
        return asdict(self)


# ── Convenience: build InferenceRequest from a dict (e.g. parsed JSON) ──

def request_from_dict(data: dict) -> InferenceRequest:
    """Build an InferenceRequest from a plain dict.

    Accepts the JSON-friendly form where asset_data is a list of dicts.
    """
    raw_asset_data = data.get('asset_data')
    if isinstance(raw_asset_data, list):
        asset_data = [AssetTimeSeries(**a) for a in raw_asset_data]
    else:
        asset_data = raw_asset_data  # CSV path

    egx = data.get('egx30_ohlcv')
    if isinstance(egx, dict):
        egx = AssetTimeSeries(**egx)

    co = data.get('constraints_override')
    if isinstance(co, dict):
        co = ConstraintsOverride(**co)

    return InferenceRequest(
        tier=data['tier'],
        asset_data=asset_data,
        target_month=data['target_month'],
        input_kind=data.get('input_kind'),
        constraints_override=co,
        egx30_ohlcv=egx,
    )
