"""Reusable numeric calculations for the monthly asset-panel pipeline."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from arch import arch_model

from src import config


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
                "last": float("nan"),
            }
            continue

        month_stats[month] = {
            "sum": float(month_values.sum()),
            "count": int(month_values.shape[0]),
            "mean": float(month_values.mean()),
            "last": float(month_values.iloc[-1]),
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


def trailing_months(month: pd.Period, window_months: int) -> list[pd.Period]:
    return [month - offset for offset in range(window_months - 1, -1, -1)]


def compute_compounded_return(returns: pd.Series) -> float:
    clean = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return float("nan")
    return float(np.prod(1.0 + clean.to_numpy(dtype=float)) - 1.0)


def compute_downside_deviation(returns: pd.Series) -> float:
    clean = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return float("nan")
    downside = np.minimum(clean.to_numpy(), 0.0)
    return float(np.sqrt(np.mean(np.square(downside))) * np.sqrt(config.TRADING_DAYS_PER_YEAR))


def compute_ewm_downside_deviation(returns: pd.Series, alpha: float) -> float:
    clean = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return float("nan")
    downside = pd.Series(np.minimum(clean.to_numpy(dtype=float), 0.0), index=clean.index)
    weighted = downside.pow(2).ewm(alpha=alpha, adjust=False).mean()
    return float(np.sqrt(float(weighted.iloc[-1])) * np.sqrt(config.TRADING_DAYS_PER_YEAR))


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


def compute_log_mean_volume(volume: pd.Series) -> float:
    clean = volume.replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return 0.0
    return float(np.log1p(clean.to_numpy(dtype=float)).mean())


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


def compute_price_to_sma(closes: pd.Series, window: int) -> float:
    clean = closes.replace([np.inf, -np.inf], np.nan).dropna().astype(float)
    if len(clean) < window:
        return float("nan")
    last_close = float(clean.iloc[-1])
    sma = float(clean.tail(window).mean())
    if sma <= 0:
        return float("nan")
    return float((last_close / sma) - 1.0)


def compute_price_to_ema(closes: pd.Series, window: int) -> float:
    clean = closes.replace([np.inf, -np.inf], np.nan).dropna().astype(float)
    if len(clean) < window:
        return float("nan")
    last_close = float(clean.iloc[-1])
    ema = float(clean.ewm(span=window, adjust=False).mean().iloc[-1])
    if ema <= 0:
        return float("nan")
    return float((last_close / ema) - 1.0)


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


def compute_downside_beta_to_benchmark(asset_returns: pd.DataFrame, benchmark_returns: pd.DataFrame) -> float:
    merged = asset_returns.merge(benchmark_returns, on="Date", how="inner")
    merged = merged.loc[merged["BenchmarkReturn"] < 0.0].copy()
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
