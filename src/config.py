"""Shared constants for the monthly asset-panel data pipeline."""

# === Repository Paths ===
RAW_DATA_DIR = "rawData"
READY_DATA_DIR = "data/ready"
DAILY_MARKET_SERIES_NAME = "daily_market_series.csv"
MONTHLY_PANEL_NAME = "monthly_asset_panel.csv"

# === Data Splits ===
WARMUP_START = "2010-08"
WARMUP_END = "2010-10"
TRAIN_START = "2010-11"
TRAIN_END = "2022-12"
VAL_START = "2023-01"
VAL_END = "2025-02"
TEST_START = "2025-03"
TEST_END = "2026-02"

# === Rolling Windows ===
WINDOW_MONTHS = 3
MIN_ASSETS_PER_MONTH = 3
MAX_FORWARD_FILL_DAYS = 5
EGARCH_RETURN_DECIMALS = 12

# === Parsing And Calendar ===
DATE_FORMAT_RAW = "%m/%d/%Y"
DATE_FORMAT_DAILY = "%Y-%m-%d"
DATE_FORMAT_MONTHLY = "%Y-%m"
MONTH_LABEL_FORMAT = "%b %Y"
EGX_WEEKMASK = "Sun Mon Tue Wed Thu"

RAW_MARKET_COLUMNS_KEEP = ["Date", "Price", "Open", "High", "Low", "Vol.", "Change %"]
VOL_SUFFIX_MULTIPLIERS = {
    "K": 1_000.0,
    "M": 1_000_000.0,
    "B": 1_000_000_000.0,
}

# === Canonical Output Columns ===
PANEL_METADATA_COLUMNS = [
    "Date",
    "AssetID",
    "AssetName",
    "AssetGroup",
]

MODEL_FEATURE_COLUMNS = [
    "egarch_vol",
    "downside_dev",
    "max_drawdown",
    "volume",
    "atr_pct_20",
    "beta_to_egx30",
    "price_to_sma20",
    "rsi_14",
    "distance_to_3m_high",
    "usd_vol",
    "cpi_trajectory",
]

TARGET_COMPONENT_COLUMNS = [
    "realized_vol",
    "realized_downside_dev",
    "realized_max_drawdown",
]

TARGET_COLUMNS = TARGET_COMPONENT_COLUMNS + [
    "realized_risk",
    "realized_rank",
]

DAILY_MARKET_COLUMNS = [
    "Date",
    "AssetID",
    "AssetName",
    "AssetGroup",
    "QuotedValue",
    "OpenQuotedValue",
    "HighQuotedValue",
    "LowQuotedValue",
    "PriceForReturn",
    "OpenPriceForRange",
    "HighPriceForRange",
    "LowPriceForRange",
    "Volume",
    "ChangePctRaw",
    "ReturnFromPrice",
    "IsObserved",
]

# === Reward Weights ===
ALPHA = 0.7
BETA = 0.3

# === Realized Risk Component Weights ===
W_REALIZED_VOL = 1 / 3
W_DOWNSIDE_DEV = 1 / 3
W_MAX_DRAWDOWN = 1 / 3

# === Daily Technical Lookbacks ===
SMA_PERIOD = 20
RSI_PERIOD = 14
ATR_PERIOD = 20

# === Financial Conventions ===
TRADING_DAYS_PER_YEAR = 252
MONEY_MARKET_MATURITY_DAYS = 91
BONDS_MATURITY_DAYS = 365 * 5

# === Base Scored Assets ===
BASE_ASSET_IDS = [
    "MoneyMarket",
    "Bonds",
    "EGX30",
    "REIT",
    "Gold",
]
