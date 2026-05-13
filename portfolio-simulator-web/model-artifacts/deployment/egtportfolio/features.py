"""Compute the 18 technical RL_FEATURES from raw OHLCV.

Reproduces the feature engineering pipeline from `preprocess_dataset.py:compute_features`
exactly, so weights produced from "raw OHLCV → features → model" match weights
produced from "pre-computed feature CSV → model".

Input format expected:
    DataFrame indexed by Date with columns Open, High, Low, Close, Volume
    (one DataFrame per asset; see compute_features_for_universe for batched API).

Output:
    Same DataFrame with 18 additional feature columns matching `RL_FEATURES` in
    src/config.py — in the same order PPO was trained on:

      log_return, simple_return,
      rolling_vol_20, rolling_vol_60,
      rolling_sharpe_30, rolling_sharpe_60,
      rsi_14, macd, macd_signal, macd_histogram, bollinger_pct,
      adx_14, cci_14,
      rolling_beta_60, max_drawdown_60, daily_range,
      price_to_sma30, price_to_sma60
"""

from typing import Dict

import numpy as np
import pandas as pd

RL_FEATURE_NAMES = [
    'log_return', 'simple_return',
    'rolling_vol_20', 'rolling_vol_60',
    'rolling_sharpe_30', 'rolling_sharpe_60',
    'rsi_14',
    'macd', 'macd_signal', 'macd_histogram',
    'bollinger_pct',
    'adx_14', 'cci_14',
    'rolling_beta_60', 'max_drawdown_60', 'daily_range',
    'price_to_sma30', 'price_to_sma60',
]


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14):
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, min_periods=period).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1 / period, min_periods=period).mean()
                     / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm.ewm(alpha=1 / period, min_periods=period).mean()
                      / atr.replace(0, np.nan))
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    return dx.ewm(alpha=1 / period, min_periods=period).mean()


def compute_cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14):
    typical_price = (high + low + close) / 3.0
    sma_tp = typical_price.rolling(window=period).mean()
    mad = typical_price.rolling(window=period).apply(
        lambda x: np.mean(np.abs(x - x.mean())), raw=True
    )
    return (typical_price - sma_tp) / (0.015 * mad.replace(0, np.nan))


def compute_rolling_beta(asset_returns: pd.Series, market_returns: pd.Series,
                         window: int = 60) -> pd.Series:
    cov = asset_returns.rolling(window=window).cov(market_returns)
    var_market = market_returns.rolling(window=window).var()
    return cov / var_market.replace(0, np.nan)


def compute_rolling_max_drawdown(close: pd.Series, window: int = 60) -> pd.Series:
    def max_dd(prices):
        if len(prices) < 2:
            return 0.0
        cummax = np.maximum.accumulate(prices)
        drawdowns = (prices - cummax) / np.where(cummax == 0, np.nan, cummax)
        return np.nanmin(drawdowns) if len(drawdowns) > 0 else 0.0

    return close.rolling(window=window).apply(max_dd, raw=True)


def compute_features_one_asset(df: pd.DataFrame,
                               egx30_log_returns: pd.Series = None) -> pd.DataFrame:
    """Compute 18 features for a single asset.

    Input df: DataFrame indexed by Date with Open, High, Low, Close (Volume optional).
    egx30_log_returns: pd.Series indexed by Date with EGX30 log returns
        (required for rolling_beta_60; if None, beta is filled with 0 — matches
        training behavior for assets that predate EGX30 alignment).

    Returns: same df with 18 feature columns appended in RL_FEATURE_NAMES order.
    """
    df = df.copy().sort_index()
    close = df['Close']
    high = df['High'] if 'High' in df.columns else close
    low = df['Low'] if 'Low' in df.columns else close

    # Returns
    df['log_return'] = np.log(close / close.shift(1)).clip(-0.5, 0.5)
    df['simple_return'] = close.pct_change().clip(-0.5, 1.0)

    # Volatility (annualized)
    df['rolling_vol_20'] = (df['log_return'].rolling(20).std() * np.sqrt(252)).clip(0.0, 3.0)
    df['rolling_vol_60'] = (df['log_return'].rolling(60).std() * np.sqrt(252)).clip(0.0, 3.0)

    # Rolling Sharpe (annualized)
    rm30 = df['log_return'].rolling(30).mean()
    rs30 = df['log_return'].rolling(30).std()
    df['rolling_sharpe_30'] = ((rm30 / rs30.replace(0, np.nan)) * np.sqrt(252)).clip(-5.0, 5.0)
    rm60 = df['log_return'].rolling(60).mean()
    rs60 = df['log_return'].rolling(60).std()
    df['rolling_sharpe_60'] = ((rm60 / rs60.replace(0, np.nan)) * np.sqrt(252)).clip(-5.0, 5.0)

    # SMAs (intermediate; not output features)
    sma_30 = close.rolling(30).mean()
    sma_60 = close.rolling(60).mean()
    df['price_to_sma30'] = (close / sma_30.replace(0, np.nan)).clip(0.5, 2.0)
    df['price_to_sma60'] = (close / sma_60.replace(0, np.nan)).clip(0.5, 2.0)

    # RSI
    df['rsi_14'] = compute_rsi(close, period=14)

    # MACD family (normalized by close to make scale-invariant)
    macd_line, sig, hist = compute_macd(close)
    safe_close = close.replace(0, np.nan)
    df['macd'] = macd_line / safe_close
    df['macd_signal'] = sig / safe_close
    df['macd_histogram'] = hist / safe_close

    # Bollinger %B
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20
    bb_range = (bb_upper - bb_lower).replace(0, np.nan)
    df['bollinger_pct'] = ((close - bb_lower) / bb_range).clip(-2.0, 3.0)

    # ADX, CCI
    df['adx_14'] = compute_adx(high, low, close, period=14)
    df['cci_14'] = compute_cci(high, low, close, period=14).clip(-500.0, 500.0)

    # Rolling beta vs EGX30
    if egx30_log_returns is not None:
        aligned = egx30_log_returns.reindex(df.index)
        df['rolling_beta_60'] = compute_rolling_beta(
            df['log_return'], aligned, window=60
        ).clip(-3.0, 3.0)
    else:
        df['rolling_beta_60'] = 0.0  # neutral if no market data

    # Max drawdown
    df['max_drawdown_60'] = compute_rolling_max_drawdown(close, window=60)

    # Daily range
    df['daily_range'] = ((high - low) / safe_close).clip(0.0, None)

    # Final: fill any remaining NaN with neutral defaults
    # (matches training pipeline's cleanup_nan strategy)
    df[RL_FEATURE_NAMES] = df[RL_FEATURE_NAMES].ffill().bfill().fillna(0.0)
    return df


def compute_features_for_universe(
    ohlcv_by_asset: Dict[str, pd.DataFrame],
    egx30_ohlcv: pd.DataFrame = None,
) -> Dict[str, pd.DataFrame]:
    """Compute features for a whole universe at once.

    Args:
        ohlcv_by_asset: {asset_name: DataFrame indexed by Date with OHLCV columns}
        egx30_ohlcv: optional EGX30 DataFrame for rolling_beta_60 computation

    Returns:
        {asset_name: DataFrame with 18 feature columns}
    """
    egx30_log_returns = None
    if egx30_ohlcv is not None and 'Close' in egx30_ohlcv.columns:
        egx30_log_returns = np.log(
            egx30_ohlcv['Close'] / egx30_ohlcv['Close'].shift(1)
        ).clip(-0.5, 0.5)

    return {
        asset: compute_features_one_asset(df, egx30_log_returns)
        for asset, df in ohlcv_by_asset.items()
    }


def cross_sectional_zscore(tensor: np.ndarray, active_matrix: np.ndarray) -> np.ndarray:
    """Per-day cross-sectional z-score across active assets.

    Matches src/data_loader.py:_cross_sectional_zscore exactly so deployment-
    time normalization is identical to training-time normalization.
    """
    normalized = tensor.copy()
    n_dates, n_assets, n_features = tensor.shape
    for t in range(n_dates):
        active_mask = active_matrix[t] == 1
        if active_mask.sum() < 2:
            continue
        vals = tensor[t, active_mask, :]
        mean = vals.mean(axis=0, keepdims=True)
        std = vals.std(axis=0, keepdims=True) + 1e-8
        normalized[t, active_mask, :] = (vals - mean) / std
    return normalized
