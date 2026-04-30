"""Build the canonical cleaned market series and monthly asset panel."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.tseries.offsets import CustomBusinessDay

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config
from src.data_processing.calculations import (
    aggregate_month_egarch_stats,
    annualized_volatility,
    compute_atr_pct,
    compute_beta_to_benchmark,
    compute_compounded_return,
    compute_distance_to_high,
    compute_downside_beta_to_benchmark,
    compute_downside_deviation,
    compute_ewm_downside_deviation,
    compute_log_mean_volume,
    compute_max_drawdown,
    compute_price_to_ema,
    compute_price_to_sma,
    compute_trailing_volume,
    compute_walk_forward_egarch_month_stats,
    compute_wilder_rsi,
    rank_to_unit_interval,
    trailing_months,
)
from src.feature_profiles import FeatureProfile, get_feature_profile


@dataclass(frozen=True)
class AssetSpec:
    asset_id: str
    asset_name: str
    asset_group: str
    file_name: str
    series_kind: str
    maturity_days: int | None = None


STOCK_FILE_MAP = {
    "COMI.CA": "CommercialIntBank.csv",
    "TMGH.CA": "TMGHolding.csv",
    "EAST.CA": "EasternCompany.csv",
    "FWRY.CA": "Fawry.csv",
    "ETEL.CA": "TelecomEgypt.csv",
    "EFIH.CA": "EFinance.csv",
    "ABUK.CA": "AbuQirFertilizers.csv",
    "HRHO.CA": "EFGHolding.csv",
    "ADIB.CA": "AbuDhabiIslamicBank.csv",
    "EFID.CA": "EditaFood.csv",
    "VLMR.CA": "ValmoreHolding.csv",
    "BTFH.CA": "BeltoneHolding.csv",
    "ORAS.CA": "OrascomConstruction.csv",
    "CCAP.CA": "QalaaHoldings.csv",
    "EGAL.CA": "EgyptAluminum.csv",
    "GBCO.CA": "GBCorp.csv",
    "PHDC.CA": "PalmHills.csv",
    "MCQE.CA": "MisrCementQena.csv",
    "AMOC.CA": "AlexandriaMineralOils.csv",
    "ISPH.CA": "IbnsinaPharma.csv",
    "ORHD.CA": "OrascomDevelopment.csv",
    "JUFO.CA": "JuhaynaFood.csv",
    "HELI.CA": "HeliopolisHousing.csv",
    "VLMRA.CA": "ValmoreHoldingA.csv",
    "ORWE.CA": "OrientalWeavers.csv",
    "RAYA.CA": "RayaHolding.csv",
    "RMDA.CA": "Rameda.csv",
    "EMFD.CA": "EmaarMisr.csv",
    "OIH.CA": "OrascomInvestment.csv",
    "ARCC.CA": "ArabianCement.csv",
    "EGCH.CA": "Kima.csv",
}

SCORING_ASSETS = [
    AssetSpec(
        asset_id="MoneyMarket",
        asset_name="91-Day T-Bills",
        asset_group="MoneyMarket",
        file_name="MoneyMarket.csv",
        series_kind="yield",
        maturity_days=config.MONEY_MARKET_MATURITY_DAYS,
    ),
    AssetSpec(
        asset_id="Bonds",
        asset_name="5-Year Government Bonds",
        asset_group="Bonds",
        file_name="Bonds.csv",
        series_kind="yield",
        maturity_days=config.BONDS_MATURITY_DAYS,
    ),
    AssetSpec(
        asset_id="EGX30",
        asset_name="EGX30 Index",
        asset_group="EquityIndex",
        file_name="EGX30.csv",
        series_kind="price",
    ),
    AssetSpec(
        asset_id="REIT",
        asset_name="REIT Index",
        asset_group="REIT",
        file_name="REIT.csv",
        series_kind="price",
    ),
    AssetSpec(
        asset_id="Gold",
        asset_name="24K Gold (EGP)",
        asset_group="Gold",
        file_name="Gold.csv",
        series_kind="price",
    ),
]

USD_SPEC = AssetSpec(
    asset_id="USD",
    asset_name="USD/EGP",
    asset_group="Macro",
    file_name="USD.csv",
    series_kind="price",
)

EGX_BUSINESS_DAY = CustomBusinessDay(weekmask=config.EGX_WEEKMASK)


def build_stock_specs(raw_dir: Path) -> list[AssetSpec]:
    starts_path = raw_dir / "Stocks_Starting_Years.csv"
    starts_df = pd.read_csv(starts_path)
    specs: list[AssetSpec] = []
    for _, row in starts_df.iterrows():
        asset_id = str(row["Reuters Code"]).strip()
        file_name = STOCK_FILE_MAP[asset_id]
        specs.append(
            AssetSpec(
                asset_id=asset_id,
                asset_name=str(row["Company Name"]).strip(),
                asset_group="Equity",
                file_name=file_name,
                series_kind="price",
            )
        )
    return specs


def parse_numeric(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.strip()
        .replace({"": np.nan, "-": np.nan, "nan": np.nan})
        .str.replace(",", "", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def parse_percent(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.strip()
        .replace({"": np.nan, "-": np.nan, "nan": np.nan})
        .str.replace("%", "", regex=False)
        .str.replace(",", "", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce") / 100.0


def parse_volume(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.strip().replace({"": np.nan, "-": np.nan, "nan": np.nan})
    suffix = cleaned.str.extract(r"([KMB])$", expand=False)
    base = pd.to_numeric(cleaned.str.replace(r"[KMB]$", "", regex=True), errors="coerce")
    multiplier = suffix.map(config.VOL_SUFFIX_MULTIPLIERS).fillna(1.0)
    return base * multiplier


def load_market_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, usecols=lambda column: column in config.RAW_MARKET_COLUMNS_KEEP)
    for column in config.RAW_MARKET_COLUMNS_KEEP:
        if column not in frame.columns:
            frame[column] = np.nan

    frame["Date"] = pd.to_datetime(frame["Date"], format=config.DATE_FORMAT_RAW, errors="coerce")
    frame = frame.loc[frame["Date"].notna()].copy()
    frame["QuotedValue"] = parse_numeric(frame["Price"])
    frame["OpenQuotedValue"] = parse_numeric(frame["Open"])
    frame["HighQuotedValue"] = parse_numeric(frame["High"])
    frame["LowQuotedValue"] = parse_numeric(frame["Low"])
    frame["Volume"] = parse_volume(frame["Vol."])
    frame["ChangePctRaw"] = parse_percent(frame["Change %"])
    frame = frame[
        [
            "Date",
            "QuotedValue",
            "OpenQuotedValue",
            "HighQuotedValue",
            "LowQuotedValue",
            "Volume",
            "ChangePctRaw",
        ]
    ]
    frame = frame.dropna(subset=["QuotedValue"])
    frame = frame.drop_duplicates(subset=["Date"], keep="last").sort_values("Date").reset_index(drop=True)
    return frame


def convert_yield_to_price_proxy(quoted: pd.Series, maturity_days: int) -> pd.Series:
    yield_decimal = quoted / 100.0
    maturity_years = maturity_days / 365.0
    return 100.0 / (1.0 + (yield_decimal * maturity_years))


def convert_quote_series_to_price_space(
    quoted: pd.Series,
    series_kind: str,
    maturity_days: int | None,
) -> pd.Series:
    converted = convert_yield_to_price_proxy(quoted, maturity_days or 0) if series_kind == "yield" else quoted.astype(float)
    return converted.where(converted > 0)


def add_price_space_fields(frame: pd.DataFrame, spec: AssetSpec) -> pd.DataFrame:
    enriched = frame.copy()
    close_price = convert_quote_series_to_price_space(enriched["QuotedValue"], spec.series_kind, spec.maturity_days)
    open_price = convert_quote_series_to_price_space(enriched["OpenQuotedValue"], spec.series_kind, spec.maturity_days)
    high_price = convert_quote_series_to_price_space(enriched["HighQuotedValue"], spec.series_kind, spec.maturity_days)
    low_price = convert_quote_series_to_price_space(enriched["LowQuotedValue"], spec.series_kind, spec.maturity_days)

    enriched["PriceForReturn"] = close_price
    enriched["OpenPriceForRange"] = open_price

    price_candidates = pd.concat([close_price, open_price, high_price, low_price], axis=1)
    enriched["HighPriceForRange"] = price_candidates.max(axis=1, skipna=True)
    enriched["LowPriceForRange"] = price_candidates.min(axis=1, skipna=True)
    return enriched


def align_to_egx_calendar(frame: pd.DataFrame) -> pd.DataFrame:
    observed = frame.copy()
    observed["IsObserved"] = 1
    observed = observed.set_index("Date").sort_index()

    full_index = pd.date_range(observed.index.min(), observed.index.max(), freq=EGX_BUSINESS_DAY)
    aligned = observed.reindex(full_index)
    aligned.index.name = "Date"
    aligned["IsObserved"] = aligned["IsObserved"].fillna(0).astype(int)
    aligned["QuotedValue"] = aligned["QuotedValue"].ffill(limit=config.MAX_FORWARD_FILL_DAYS)
    aligned["PriceForReturn"] = aligned["PriceForReturn"].ffill(limit=config.MAX_FORWARD_FILL_DAYS)
    aligned["ReturnFromPrice"] = aligned["PriceForReturn"].pct_change(fill_method=None)
    aligned["ReturnFromPrice"] = aligned["ReturnFromPrice"].replace([np.inf, -np.inf], np.nan)
    return aligned.reset_index()


def prepare_asset_series(raw_dir: Path, spec: AssetSpec) -> tuple[pd.DataFrame, dict[str, float | int | str]]:
    raw_frame = load_market_csv(raw_dir / spec.file_name)
    raw_frame = add_price_space_fields(raw_frame, spec)
    raw_frame = raw_frame.dropna(subset=["PriceForReturn"]).reset_index(drop=True)

    aligned = align_to_egx_calendar(raw_frame)
    aligned["AssetID"] = spec.asset_id
    aligned["AssetName"] = spec.asset_name
    aligned["AssetGroup"] = spec.asset_group

    compare = aligned.dropna(subset=["ReturnFromPrice", "ChangePctRaw"]).copy()
    diff_abs = (compare["ReturnFromPrice"] - compare["ChangePctRaw"]).abs().replace([np.inf, -np.inf], np.nan).dropna()
    qa = {
        "AssetID": spec.asset_id,
        "ComparedRows": int(diff_abs.shape[0]),
        "MismatchRows": int((diff_abs > 5e-4).sum()),
        "MaxAbsDiff": float(diff_abs.max()) if not diff_abs.empty else float("nan"),
    }

    aligned["Month"] = aligned["Date"].dt.to_period("M")
    return aligned, qa


def prepare_usd_series(raw_dir: Path) -> tuple[pd.DataFrame, dict[str, float | int | str]]:
    usd_1 = load_market_csv(raw_dir / "USD_1.csv")
    usd_2 = load_market_csv(raw_dir / "USD_2.csv")
    combined = pd.concat([usd_1, usd_2], ignore_index=True)
    combined = combined.drop_duplicates(subset=["Date"], keep="last").sort_values("Date").reset_index(drop=True)
    combined = add_price_space_fields(combined, USD_SPEC)
    combined = combined.dropna(subset=["PriceForReturn"]).reset_index(drop=True)

    aligned = align_to_egx_calendar(combined)
    aligned["AssetID"] = USD_SPEC.asset_id
    aligned["AssetName"] = USD_SPEC.asset_name
    aligned["AssetGroup"] = USD_SPEC.asset_group
    aligned["Month"] = aligned["Date"].dt.to_period("M")

    compare = aligned.dropna(subset=["ReturnFromPrice", "ChangePctRaw"]).copy()
    diff_abs = (compare["ReturnFromPrice"] - compare["ChangePctRaw"]).abs().replace([np.inf, -np.inf], np.nan).dropna()
    qa = {
        "AssetID": USD_SPEC.asset_id,
        "ComparedRows": int(diff_abs.shape[0]),
        "MismatchRows": int((diff_abs > 5e-4).sum()),
        "MaxAbsDiff": float(diff_abs.max()) if not diff_abs.empty else float("nan"),
    }
    return aligned, qa


def load_cpi_series(raw_dir: Path) -> pd.DataFrame:
    cpi = pd.read_csv(raw_dir / "CPI.csv", skiprows=1)
    cpi["Date"] = pd.to_datetime(cpi["Date"], format=config.MONTH_LABEL_FORMAT, errors="coerce")
    cpi = cpi.loc[cpi["Date"].notna()].copy()
    cpi["HeadlineMoM"] = parse_percent(cpi["Headline (m/m)"])
    cpi = cpi[["Date", "HeadlineMoM"]].dropna(subset=["HeadlineMoM"])
    cpi = cpi.drop_duplicates(subset=["Date"], keep="last").sort_values("Date").reset_index(drop=True)
    cpi["Month"] = cpi["Date"].dt.to_period("M")
    return cpi


def compute_macro_features(
    usd_daily: pd.DataFrame,
    cpi_monthly: pd.DataFrame,
    feature_profile: FeatureProfile | None = None,
) -> dict[pd.Period, dict[str, float]]:
    profile = feature_profile or get_feature_profile(config.DEFAULT_FEATURE_PROFILE_ID)
    cpi_lookup = cpi_monthly.set_index("Month")["HeadlineMoM"]
    macro_features: dict[pd.Period, dict[str, float]] = {}

    start = pd.Period(config.PANEL_STATE_START, freq="M")
    end = min(
        usd_daily["Month"].max(),
        cpi_monthly["Month"].max(),
        pd.Period(config.TEST_END, freq="M"),
    )

    for month in pd.period_range(start=start, end=end, freq="M"):
        usd_feature_months = trailing_months(month, profile.usd_window_months)
        cpi_feature_months = trailing_months(month, profile.cpi_window_months)
        usd_window = usd_daily.loc[usd_daily["Month"].isin(usd_feature_months), "ReturnFromPrice"].dropna()
        cpi_window = cpi_lookup.reindex(cpi_feature_months)
        if usd_window.empty:
            continue
        if profile.cpi_mode == "last_mom":
            last_cpi = cpi_lookup.get(month)
            if pd.isna(last_cpi):
                continue
            cpi_value = float(last_cpi)
        elif cpi_window.isna().any():
            continue
        else:
            cpi_value = float(np.prod(1.0 + cpi_window.to_numpy()) - 1.0)

        if profile.usd_mode == "volatility":
            usd_value = annualized_volatility(usd_window)
        elif profile.usd_mode == "return_trajectory":
            usd_value = compute_compounded_return(usd_window)
        else:
            raise ValueError(f"Unsupported usd_mode: {profile.usd_mode}")

        macro_features[month] = {
            "usd_vol": usd_value,
            "cpi_trajectory": cpi_value,
        }
    return macro_features


def _compute_price_to_sma_available(closes: pd.Series, window: int) -> float:
    clean = closes.replace([np.inf, -np.inf], np.nan).dropna().astype(float)
    if clean.empty:
        return float("nan")
    last_close = float(clean.iloc[-1])
    sma = float(clean.tail(min(window, len(clean))).mean())
    if sma <= 0:
        return float("nan")
    return float((last_close / sma) - 1.0)


def _compute_atr_pct_available(observed_frame: pd.DataFrame, period: int) -> float:
    clean = observed_frame[["PriceForReturn", "HighPriceForRange", "LowPriceForRange"]].replace([np.inf, -np.inf], np.nan)
    clean = clean.dropna(subset=["PriceForReturn", "HighPriceForRange", "LowPriceForRange"]).copy()
    if clean.empty:
        return float("nan")

    prev_close = clean["PriceForReturn"].shift(1)
    true_range = pd.concat(
        [
            clean["HighPriceForRange"] - clean["LowPriceForRange"],
            (clean["HighPriceForRange"] - prev_close).abs(),
            (clean["LowPriceForRange"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1, skipna=True)

    atr = float(true_range.tail(min(period, len(true_range))).mean())
    last_close = float(clean["PriceForReturn"].iloc[-1])
    if last_close <= 0:
        return float("nan")
    return float(atr / last_close)


def _compute_wilder_rsi_available(closes: pd.Series, periods: int) -> float:
    clean = closes.replace([np.inf, -np.inf], np.nan).dropna().astype(float)
    if len(clean) < 2:
        return float("nan")
    capped_period = min(periods, len(clean) - 1)
    return compute_wilder_rsi(clean, capped_period)


def compute_monthly_panel(
    daily_assets: dict[str, pd.DataFrame],
    macro_features: dict[pd.Period, dict[str, float]],
    feature_profile: FeatureProfile | None = None,
    egarch_month_stats_by_asset: dict[str, dict[pd.Period, dict[str, float | int]]] | None = None,
) -> pd.DataFrame:
    if "EGX30" not in daily_assets:
        raise RuntimeError("EGX30 daily series is required to compute beta_to_egx30.")

    if egarch_month_stats_by_asset is None and feature_profile is not None and not isinstance(feature_profile, FeatureProfile):
        egarch_month_stats_by_asset = feature_profile
        feature_profile = None

    profile = feature_profile or get_feature_profile(config.DEFAULT_FEATURE_PROFILE_ID)
    records: list[dict[str, object]] = []
    state_months = sorted(macro_features)
    benchmark = daily_assets["EGX30"][["Date", "Month", "ReturnFromPrice"]].rename(
        columns={"ReturnFromPrice": "BenchmarkReturn"}
    )

    for asset_id, frame in daily_assets.items():
        observed_months = set(frame.loc[frame["IsObserved"] == 1, "Month"].unique())
        asset_name = frame["AssetName"].iloc[0]
        asset_group = frame["AssetGroup"].iloc[0]
        asset_month_egarch = (
            egarch_month_stats_by_asset[asset_id]
            if egarch_month_stats_by_asset and asset_id in egarch_month_stats_by_asset
            else compute_walk_forward_egarch_month_stats(frame)
        )

        for month in state_months:
            required_feature_months = trailing_months(month, profile.row_feature_window_months)
            if not all(required_month in observed_months for required_month in required_feature_months):
                continue

            full_feature_window = frame.loc[frame["Month"].isin(required_feature_months)].copy()
            feature_returns = full_feature_window["ReturnFromPrice"].dropna()
            target_returns = frame.loc[frame["Month"] == month, "ReturnFromPrice"].dropna()
            if target_returns.empty:
                continue

            downside_months = trailing_months(month, profile.downside_window_months)
            max_drawdown_months = trailing_months(month, profile.max_drawdown_window_months)
            volume_months = trailing_months(month, profile.volume_window_months)
            beta_months = trailing_months(month, profile.beta_window_months)
            distance_months = trailing_months(month, profile.distance_high_window_months)

            observed_feature_window = full_feature_window.loc[full_feature_window["IsObserved"] == 1].copy()
            downside_window = frame.loc[frame["Month"].isin(downside_months), "ReturnFromPrice"].dropna()
            max_drawdown_window = frame.loc[frame["Month"].isin(max_drawdown_months), "ReturnFromPrice"].dropna()
            volume_window = frame.loc[frame["Month"].isin(volume_months), "Volume"]
            beta_asset_window = frame.loc[frame["Month"].isin(beta_months), ["Date", "ReturnFromPrice"]]
            beta_benchmark_window = benchmark.loc[benchmark["Month"].isin(beta_months), ["Date", "BenchmarkReturn"]]
            distance_window = observed_feature_window.loc[observed_feature_window["Month"].isin(distance_months)].copy()

            if profile.egarch_mode == "aggregate_mean_3m":
                feature_egarch = aggregate_month_egarch_stats(asset_month_egarch, required_feature_months)
            elif profile.egarch_mode == "last_value_3m":
                feature_egarch = float(asset_month_egarch.get(month, {}).get("last", float("nan")))
            elif profile.egarch_mode == "realized_vol_proxy":
                feature_egarch = annualized_volatility(feature_returns)
            else:
                raise ValueError(f"Unsupported egarch_mode: {profile.egarch_mode}")

            if profile.downside_mode == "standard":
                downside_dev = compute_downside_deviation(downside_window)
            elif profile.downside_mode == "ewm":
                downside_dev = compute_ewm_downside_deviation(downside_window, alpha=profile.downside_ewm_alpha)
            else:
                raise ValueError(f"Unsupported downside_mode: {profile.downside_mode}")

            max_drawdown = compute_max_drawdown(max_drawdown_window)

            if profile.volume_mode == "sum":
                volume_value = compute_trailing_volume(volume_window)
            elif profile.volume_mode == "mean_log":
                volume_value = compute_log_mean_volume(volume_window)
            else:
                raise ValueError(f"Unsupported volume_mode: {profile.volume_mode}")

            observed_closes = observed_feature_window["PriceForReturn"].dropna()
            if profile.technical_min_periods_mode == "available":
                atr_pct = _compute_atr_pct_available(observed_feature_window, profile.atr_period)
            elif profile.technical_min_periods_mode == "full":
                atr_pct = compute_atr_pct(observed_feature_window, profile.atr_period)
            else:
                raise ValueError(f"Unsupported technical_min_periods_mode: {profile.technical_min_periods_mode}")

            if profile.beta_mode == "standard":
                beta_to_egx30 = compute_beta_to_benchmark(beta_asset_window, beta_benchmark_window)
            elif profile.beta_mode == "downside":
                beta_to_egx30 = compute_downside_beta_to_benchmark(beta_asset_window, beta_benchmark_window)
            else:
                raise ValueError(f"Unsupported beta_mode: {profile.beta_mode}")

            if profile.ma_mode == "sma":
                if profile.technical_min_periods_mode == "available":
                    price_to_ma = _compute_price_to_sma_available(observed_closes, profile.ma_period)
                else:
                    price_to_ma = compute_price_to_sma(observed_closes, profile.ma_period)
            elif profile.ma_mode == "ema":
                price_to_ma = compute_price_to_ema(observed_closes, profile.ma_period)
            else:
                raise ValueError(f"Unsupported ma_mode: {profile.ma_mode}")

            if profile.technical_min_periods_mode == "available":
                rsi_value = _compute_wilder_rsi_available(observed_closes, profile.rsi_period)
            else:
                rsi_value = compute_wilder_rsi(observed_closes, profile.rsi_period)
            last_close = float(observed_closes.iloc[-1]) if not observed_closes.empty else float("nan")
            distance_to_high = compute_distance_to_high(last_close, distance_window["HighPriceForRange"])

            feature_values = {
                "egarch_vol": feature_egarch,
                "downside_dev": downside_dev,
                "max_drawdown": max_drawdown,
                "volume": volume_value,
                "atr_pct_20": atr_pct,
                "beta_to_egx30": beta_to_egx30,
                "price_to_sma20": price_to_ma,
                "rsi_14": rsi_value,
                "distance_to_3m_high": distance_to_high,
                "usd_vol": macro_features[month]["usd_vol"],
                "cpi_trajectory": macro_features[month]["cpi_trajectory"],
            }

            if feature_returns.empty:
                continue
            if any(pd.isna(feature_values[feature_name]) for feature_name in profile.active_features):
                continue

            records.append(
                {
                    "Date": month.strftime(config.DATE_FORMAT_MONTHLY),
                    "AssetID": asset_id,
                    "AssetName": asset_name,
                    "AssetGroup": asset_group,
                    "egarch_vol_raw": feature_egarch,
                    "downside_dev_raw": downside_dev,
                    "max_drawdown_raw": max_drawdown,
                    "volume_raw": volume_value,
                    "atr_pct_20_raw": atr_pct,
                    "beta_to_egx30_raw": beta_to_egx30,
                    "price_to_sma20_raw": price_to_ma,
                    "rsi_14_raw": rsi_value,
                    "distance_to_3m_high_raw": distance_to_high,
                    "usd_vol": macro_features[month]["usd_vol"],
                    "cpi_trajectory": macro_features[month]["cpi_trajectory"],
                    "realized_vol_raw": annualized_volatility(target_returns),
                    "realized_downside_dev_raw": compute_downside_deviation(target_returns),
                    "realized_max_drawdown_raw": compute_max_drawdown(target_returns),
                }
            )

    panel = pd.DataFrame.from_records(records)
    if panel.empty:
        raise RuntimeError("No monthly asset rows were built. Check raw-data cleanup and window coverage.")

    normalized_frames: list[pd.DataFrame] = []
    for _, group in panel.groupby("Date", sort=True):
        if len(group) < config.MIN_ASSETS_PER_MONTH:
            continue
        month_frame = group.copy()
        normalized_feature_map = {
            "egarch_vol": "egarch_vol_raw",
            "downside_dev": "downside_dev_raw",
            "max_drawdown": "max_drawdown_raw",
            "volume": "volume_raw",
            "atr_pct_20": "atr_pct_20_raw",
            "beta_to_egx30": "beta_to_egx30_raw",
            "price_to_sma20": "price_to_sma20_raw",
            "rsi_14": "rsi_14_raw",
            "distance_to_3m_high": "distance_to_3m_high_raw",
        }
        for feature_name, raw_column in normalized_feature_map.items():
            if feature_name in profile.active_features:
                month_frame[feature_name] = rank_to_unit_interval(month_frame[raw_column])
            else:
                month_frame[feature_name] = float(profile.neutral_fill_value)
        if "usd_vol" not in profile.active_features:
            month_frame["usd_vol"] = float(profile.neutral_fill_value)
        if "cpi_trajectory" not in profile.active_features:
            month_frame["cpi_trajectory"] = float(profile.neutral_fill_value)
        month_frame["realized_vol"] = rank_to_unit_interval(month_frame["realized_vol_raw"])
        month_frame["realized_downside_dev"] = rank_to_unit_interval(month_frame["realized_downside_dev_raw"])
        month_frame["realized_max_drawdown"] = rank_to_unit_interval(month_frame["realized_max_drawdown_raw"])
        month_frame["realized_risk"] = (
            (config.W_REALIZED_VOL * month_frame["realized_vol"])
            + (config.W_DOWNSIDE_DEV * month_frame["realized_downside_dev"])
            + (config.W_MAX_DRAWDOWN * month_frame["realized_max_drawdown"])
        )
        month_frame["realized_rank"] = month_frame["realized_risk"].rank(method="average", ascending=True)
        normalized_frames.append(month_frame)

    if not normalized_frames:
        raise RuntimeError("All monthly groups were filtered out by the minimum-asset rule.")

    final_panel = pd.concat(normalized_frames, ignore_index=True)
    final_panel = final_panel.sort_values(["Date", "AssetID"]).reset_index(drop=True)
    final_panel = final_panel[
        config.PANEL_METADATA_COLUMNS
        + config.MODEL_FEATURE_COLUMNS
        + config.TARGET_COLUMNS
    ]
    return final_panel


def format_daily_market_series(frames: list[pd.DataFrame]) -> pd.DataFrame:
    daily = pd.concat(frames, ignore_index=True)
    daily = daily[config.DAILY_MARKET_COLUMNS].copy()
    daily["Date"] = pd.to_datetime(daily["Date"]).dt.strftime(config.DATE_FORMAT_DAILY)
    daily = daily.sort_values(["Date", "AssetID"]).reset_index(drop=True)
    return daily


def print_qa_summary(qa_rows: list[dict[str, float | int | str]]) -> None:
    qa = pd.DataFrame(qa_rows).sort_values(["MismatchRows", "MaxAbsDiff"], ascending=[False, False])
    compared = int(qa["ComparedRows"].sum())
    mismatches = int(qa["MismatchRows"].sum())
    print("Return QA summary")
    print(f"Compared rows: {compared}")
    print(f"Mismatch rows (> 0.0005 abs diff): {mismatches}")
    print("Largest mismatch counts:")
    print(qa.head(10).to_string(index=False))


def resolve_output_dir(feature_profile_id: str, output_dir: str | Path | None = None) -> Path:
    if output_dir is not None:
        return Path(output_dir)
    if feature_profile_id == config.DEFAULT_FEATURE_PROFILE_ID:
        return ROOT / config.READY_DATA_DIR
    return ROOT / config.FEATURE_PROFILE_OUTPUT_DIR / feature_profile_id


def build_outputs(feature_profile_id: str = config.DEFAULT_FEATURE_PROFILE_ID, output_dir: str | Path | None = None) -> tuple[Path, Path]:
    raw_dir = ROOT / config.RAW_DATA_DIR
    profile = get_feature_profile(feature_profile_id)
    resolved_output_dir = resolve_output_dir(feature_profile_id, output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    stock_specs = build_stock_specs(raw_dir)
    scoring_specs = SCORING_ASSETS + stock_specs

    daily_frames: dict[str, pd.DataFrame] = {}
    export_frames: list[pd.DataFrame] = []
    qa_rows: list[dict[str, float | int | str]] = []

    for spec in scoring_specs:
        prepared, qa = prepare_asset_series(raw_dir, spec)
        daily_frames[spec.asset_id] = prepared
        export_frames.append(prepared)
        qa_rows.append(qa)

    usd_daily, usd_qa = prepare_usd_series(raw_dir)
    export_frames.append(usd_daily)
    qa_rows.append(usd_qa)

    cpi_monthly = load_cpi_series(raw_dir)
    macro_features = compute_macro_features(usd_daily, cpi_monthly, feature_profile=profile)
    monthly_panel = compute_monthly_panel(daily_frames, macro_features, feature_profile=profile)
    daily_market_series = format_daily_market_series(export_frames)

    daily_output = resolved_output_dir / config.DAILY_MARKET_SERIES_NAME
    panel_output = resolved_output_dir / config.MONTHLY_PANEL_NAME
    daily_market_series.to_csv(daily_output, index=False)
    monthly_panel.to_csv(panel_output, index=False)
    with (resolved_output_dir / "feature_profile_metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "feature_profile_id": profile.feature_profile_id,
                "description": profile.description,
                "parameters": profile.parameter_values(),
            },
            handle,
            indent=2,
            sort_keys=True,
        )

    try:
        daily_label: Path | str = daily_output.relative_to(ROOT)
    except ValueError:
        daily_label = str(daily_output)
    try:
        panel_label: Path | str = panel_output.relative_to(ROOT)
    except ValueError:
        panel_label = str(panel_output)
    print(f"Wrote {daily_label} with {len(daily_market_series):,} rows")
    print(f"Wrote {panel_label} with {len(monthly_panel):,} rows")
    print(f"Feature profile: {profile.feature_profile_id}")
    print(
        "Panel month range:",
        monthly_panel["Date"].min(),
        "to",
        monthly_panel["Date"].max(),
    )
    print_qa_summary(qa_rows)
    return daily_output, panel_output


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the canonical or feature-profile monthly asset panel.")
    parser.add_argument(
        "--feature-profile-id",
        default=config.DEFAULT_FEATURE_PROFILE_ID,
        help="Feature profile to build. Base profile writes to data/ready by default; non-base profiles write to outputs/feature_profiles/<id>/ unless --output-dir is set.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory for the generated daily market series and monthly panel.",
    )
    return parser


def main(argv: list[str] | None = None) -> tuple[Path, Path]:
    parser = _build_cli_parser()
    args = parser.parse_args(argv or [])
    return build_outputs(feature_profile_id=args.feature_profile_id, output_dir=args.output_dir)


if __name__ == "__main__":
    main(sys.argv[1:])
