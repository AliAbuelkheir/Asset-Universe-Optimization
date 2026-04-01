"""Build the canonical cleaned market series and monthly asset panel."""

from __future__ import annotations

import sys
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from arch import arch_model
from pandas.tseries.offsets import CustomBusinessDay

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config


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


def annualized_volatility(returns: pd.Series) -> float:
    clean = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return float("nan")
    return float(clean.std(ddof=0) * np.sqrt(config.TRADING_DAYS_PER_YEAR))


def estimate_egarch_series(returns: pd.Series) -> pd.Series:
    clean = returns.replace([np.inf, -np.inf], np.nan).dropna().astype(float).round(config.EGARCH_RETURN_DECIMALS)
    if clean.empty:
        return pd.Series(np.nan, index=returns.index)
    if clean.nunique() <= 1 or len(clean) < 20:
        fallback = pd.Series(np.nan, index=returns.index)
        fallback.loc[clean.index] = annualized_volatility(clean)
        return fallback

    scaled = clean * 100.0
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = arch_model(
                scaled,
                mean="Zero",
                vol="EGARCH",
                p=1,
                o=0,
                q=1,
                dist="normal",
                rescale=False,
            )
            result = model.fit(disp="off", show_warning=False, update_freq=0)
        conditional_vol = pd.Series(result.conditional_volatility, index=clean.index) / 100.0
        egarch_series = pd.Series(np.nan, index=returns.index)
        egarch_series.loc[clean.index] = conditional_vol * np.sqrt(config.TRADING_DAYS_PER_YEAR)
        return egarch_series
    except Exception:
        fallback = pd.Series(np.nan, index=returns.index)
        fallback.loc[clean.index] = annualized_volatility(clean)
        return fallback


def compute_walk_forward_egarch_month_stats(frame: pd.DataFrame) -> dict[pd.Period, dict[str, float | int]]:
    work = frame[["Date", "Month", "ReturnFromPrice"]].dropna(subset=["ReturnFromPrice"]).copy()
    if work.empty:
        return {}

    work = work.sort_values("Date").reset_index(drop=True)
    month_stats: dict[pd.Period, dict[str, float | int]] = {}

    for month in sorted(work["Month"].unique()):
        cutoff_returns = work.loc[work["Month"] <= month, "ReturnFromPrice"]
        egarch_series = estimate_egarch_series(cutoff_returns)
        month_index = work.index[work["Month"] == month]
        month_values = egarch_series.loc[month_index].replace([np.inf, -np.inf], np.nan).dropna()
        if month_values.empty:
            month_stats[month] = {
                "sum": float("nan"),
                "count": 0,
                "mean": float("nan"),
            }
            continue

        month_stats[month] = {
            "sum": float(month_values.sum()),
            "count": int(month_values.shape[0]),
            "mean": float(month_values.mean()),
        }

    return month_stats


def aggregate_month_egarch_stats(
    month_stats: dict[pd.Period, dict[str, float | int]],
    months: list[pd.Period],
) -> float:
    total_sum = 0.0
    total_count = 0
    for month in months:
        stats = month_stats.get(month)
        if not stats:
            continue
        count = int(stats["count"])
        if count <= 0:
            continue
        total_sum += float(stats["sum"])
        total_count += count

    if total_count == 0:
        return float("nan")
    return float(total_sum / total_count)


def compute_downside_deviation(returns: pd.Series) -> float:
    clean = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return float("nan")
    downside = np.minimum(clean.to_numpy(), 0.0)
    return float(np.sqrt(np.mean(np.square(downside))) * np.sqrt(config.TRADING_DAYS_PER_YEAR))


def compute_max_drawdown(returns: pd.Series) -> float:
    clean = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return float("nan")
    growth = (1.0 + clean.clip(lower=-0.999999)).cumprod()
    peak = growth.cummax()
    drawdown = (growth / peak) - 1.0
    return float(abs(drawdown.min()))


def compute_trailing_volume(volume: pd.Series) -> float:
    clean = volume.replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return 0.0
    return float(clean.sum())


def rank_to_unit_interval(series: pd.Series) -> pd.Series:
    valid = series.dropna()
    if valid.empty:
        return pd.Series(np.nan, index=series.index)
    if len(valid) == 1:
        result = pd.Series(np.nan, index=series.index)
        result.loc[valid.index] = 0.5
        return result

    ranks = valid.rank(method="average")
    scaled = (ranks - 1.0) / (len(valid) - 1.0)
    result = pd.Series(np.nan, index=series.index)
    result.loc[valid.index] = scaled
    return result


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


def compute_price_to_sma(closes: pd.Series, window: int) -> float:
    clean = closes.replace([np.inf, -np.inf], np.nan).dropna().astype(float)
    if len(clean) < window:
        return float("nan")
    last_close = float(clean.iloc[-1])
    sma = float(clean.tail(window).mean())
    if sma <= 0:
        return float("nan")
    return float((last_close / sma) - 1.0)


def compute_wilder_rsi(closes: pd.Series, periods: int) -> float:
    clean = closes.replace([np.inf, -np.inf], np.nan).dropna().astype(float)
    if len(clean) <= periods:
        return float("nan")

    deltas = clean.diff().dropna()
    gains = deltas.clip(lower=0.0)
    losses = -deltas.clip(upper=0.0)

    avg_gain = float(gains.iloc[:periods].mean())
    avg_loss = float(losses.iloc[:periods].mean())

    for idx in range(periods, len(deltas)):
        avg_gain = ((avg_gain * (periods - 1)) + float(gains.iloc[idx])) / periods
        avg_loss = ((avg_loss * (periods - 1)) + float(losses.iloc[idx])) / periods

    if avg_gain == 0.0 and avg_loss == 0.0:
        return 50.0
    if avg_loss == 0.0:
        return 100.0
    if avg_gain == 0.0:
        return 0.0

    relative_strength = avg_gain / avg_loss
    return float(100.0 - (100.0 / (1.0 + relative_strength)))


def compute_distance_to_high(last_close: float, high_prices: pd.Series) -> float:
    clean_highs = high_prices.replace([np.inf, -np.inf], np.nan).dropna()
    if clean_highs.empty or pd.isna(last_close):
        return float("nan")
    window_high = float(clean_highs.max())
    if window_high <= 0:
        return float("nan")
    return float((last_close / window_high) - 1.0)


def compute_atr_pct(observed_frame: pd.DataFrame, period: int) -> float:
    clean = observed_frame[["PriceForReturn", "HighPriceForRange", "LowPriceForRange"]].replace([np.inf, -np.inf], np.nan)
    clean = clean.dropna(subset=["PriceForReturn", "HighPriceForRange", "LowPriceForRange"]).copy()
    if len(clean) < period:
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

    atr = float(true_range.tail(period).mean())
    last_close = float(clean["PriceForReturn"].iloc[-1])
    if last_close <= 0:
        return float("nan")
    return float(atr / last_close)


def compute_beta_to_benchmark(asset_returns: pd.DataFrame, benchmark_returns: pd.DataFrame) -> float:
    merged = asset_returns.merge(benchmark_returns, on="Date", how="inner")
    clean = merged[["ReturnFromPrice", "BenchmarkReturn"]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(clean) < 2:
        return float("nan")

    asset_values = clean["ReturnFromPrice"].to_numpy(dtype=float)
    benchmark_values = clean["BenchmarkReturn"].to_numpy(dtype=float)
    benchmark_centered = benchmark_values - benchmark_values.mean()
    benchmark_variance = float(np.mean(np.square(benchmark_centered)))
    if benchmark_variance <= 0:
        return float("nan")

    covariance = float(np.mean((asset_values - asset_values.mean()) * benchmark_centered))
    return float(covariance / benchmark_variance)


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


def compute_macro_features(usd_daily: pd.DataFrame, cpi_monthly: pd.DataFrame) -> dict[pd.Period, dict[str, float]]:
    cpi_lookup = cpi_monthly.set_index("Month")["HeadlineMoM"]
    macro_features: dict[pd.Period, dict[str, float]] = {}

    start = pd.Period(config.TRAIN_START, freq="M")
    end = min(
        usd_daily["Month"].max(),
        cpi_monthly["Month"].max() + 1,
        pd.Period(config.TEST_END, freq="M"),
    )

    for month in pd.period_range(start=start, end=end, freq="M"):
        feature_months = [month - offset for offset in range(config.WINDOW_MONTHS, 0, -1)]
        usd_window = usd_daily.loc[usd_daily["Month"].isin(feature_months), "ReturnFromPrice"].dropna()
        cpi_window = cpi_lookup.reindex(feature_months)
        if usd_window.empty or cpi_window.isna().any():
            continue

        macro_features[month] = {
            "usd_vol": annualized_volatility(usd_window),
            "cpi_trajectory": float(np.prod(1.0 + cpi_window.to_numpy()) - 1.0),
        }
    return macro_features


def compute_monthly_panel(
    daily_assets: dict[str, pd.DataFrame],
    macro_features: dict[pd.Period, dict[str, float]],
    egarch_month_stats_by_asset: dict[str, dict[pd.Period, dict[str, float | int]]] | None = None,
) -> pd.DataFrame:
    if "EGX30" not in daily_assets:
        raise RuntimeError("EGX30 daily series is required to compute beta_to_egx30.")

    records: list[dict[str, object]] = []
    decision_months = sorted(macro_features)
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

        for month in decision_months:
            required_feature_months = [month - offset for offset in range(config.WINDOW_MONTHS, 0, -1)]
            required_months = required_feature_months + [month]
            if not all(required_month in observed_months for required_month in required_months):
                continue

            feature_window = frame.loc[frame["Month"].isin(required_feature_months)].copy()
            observed_feature_window = feature_window.loc[feature_window["IsObserved"] == 1].copy()
            benchmark_window = benchmark.loc[benchmark["Month"].isin(required_feature_months), ["Date", "BenchmarkReturn"]]
            feature_returns = feature_window["ReturnFromPrice"].dropna()
            target_returns = frame.loc[frame["Month"] == month, "ReturnFromPrice"].dropna()
            feature_egarch = aggregate_month_egarch_stats(asset_month_egarch, required_feature_months)

            observed_closes = observed_feature_window["PriceForReturn"].dropna()
            atr_pct_20 = compute_atr_pct(observed_feature_window, config.ATR_PERIOD)
            beta_to_egx30 = compute_beta_to_benchmark(
                feature_window[["Date", "ReturnFromPrice"]],
                benchmark_window,
            )
            price_to_sma20 = compute_price_to_sma(observed_closes, config.SMA_PERIOD)
            rsi_14 = compute_wilder_rsi(observed_closes, config.RSI_PERIOD)
            last_close = float(observed_closes.iloc[-1]) if not observed_closes.empty else float("nan")
            distance_to_3m_high = compute_distance_to_high(last_close, observed_feature_window["HighPriceForRange"])

            if (
                feature_returns.empty
                or target_returns.empty
                or pd.isna(feature_egarch)
                or pd.isna(atr_pct_20)
                or pd.isna(beta_to_egx30)
                or pd.isna(price_to_sma20)
                or pd.isna(rsi_14)
                or pd.isna(distance_to_3m_high)
            ):
                continue

            records.append(
                {
                    "Date": month.strftime(config.DATE_FORMAT_MONTHLY),
                    "AssetID": asset_id,
                    "AssetName": asset_name,
                    "AssetGroup": asset_group,
                    "egarch_vol_raw": feature_egarch,
                    "downside_dev_raw": compute_downside_deviation(feature_returns),
                    "max_drawdown_raw": compute_max_drawdown(feature_returns),
                    "volume_raw": compute_trailing_volume(feature_window["Volume"]),
                    "atr_pct_20_raw": atr_pct_20,
                    "beta_to_egx30_raw": beta_to_egx30,
                    "price_to_sma20_raw": price_to_sma20,
                    "rsi_14_raw": rsi_14,
                    "distance_to_3m_high_raw": distance_to_3m_high,
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
        month_frame["egarch_vol"] = rank_to_unit_interval(month_frame["egarch_vol_raw"])
        month_frame["downside_dev"] = rank_to_unit_interval(month_frame["downside_dev_raw"])
        month_frame["max_drawdown"] = rank_to_unit_interval(month_frame["max_drawdown_raw"])
        month_frame["volume"] = rank_to_unit_interval(month_frame["volume_raw"])
        month_frame["atr_pct_20"] = rank_to_unit_interval(month_frame["atr_pct_20_raw"])
        month_frame["beta_to_egx30"] = rank_to_unit_interval(month_frame["beta_to_egx30_raw"])
        month_frame["price_to_sma20"] = rank_to_unit_interval(month_frame["price_to_sma20_raw"])
        month_frame["rsi_14"] = rank_to_unit_interval(month_frame["rsi_14_raw"])
        month_frame["distance_to_3m_high"] = rank_to_unit_interval(month_frame["distance_to_3m_high_raw"])
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


def main() -> None:
    raw_dir = ROOT / config.RAW_DATA_DIR
    ready_dir = ROOT / config.READY_DATA_DIR
    ready_dir.mkdir(parents=True, exist_ok=True)

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
    macro_features = compute_macro_features(usd_daily, cpi_monthly)
    monthly_panel = compute_monthly_panel(daily_frames, macro_features)
    daily_market_series = format_daily_market_series(export_frames)

    daily_output = ready_dir / config.DAILY_MARKET_SERIES_NAME
    panel_output = ready_dir / config.MONTHLY_PANEL_NAME
    daily_market_series.to_csv(daily_output, index=False)
    monthly_panel.to_csv(panel_output, index=False)

    print(f"Wrote {daily_output.relative_to(ROOT)} with {len(daily_market_series):,} rows")
    print(f"Wrote {panel_output.relative_to(ROOT)} with {len(monthly_panel):,} rows")
    print(
        "Panel month range:",
        monthly_panel["Date"].min(),
        "to",
        monthly_panel["Date"].max(),
    )
    print_qa_summary(qa_rows)


if __name__ == "__main__":
    main()
