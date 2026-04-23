"""Shared constants for the monthly asset-panel data pipeline."""

# === Repository Paths ===
RAW_DATA_DIR = "rawData"
READY_DATA_DIR = "data/ready"
DAILY_MARKET_SERIES_NAME = "daily_market_series.csv"
MONTHLY_PANEL_NAME = "monthly_asset_panel.csv"

# === Monthly State And Decision Splits ===
HISTORY_START = "2010-08"
PANEL_STATE_START = "2010-10"
TRAIN_START = "2011-01"
TRAIN_END = "2022-12"
VAL_START = "2023-01"
VAL_END = "2025-02"
TEST_START = "2025-03"
TEST_END = "2026-01"

# === Rolling Windows ===
WINDOW_MONTHS = 3
MIN_ASSETS_PER_MONTH = 3
MAX_FORWARD_FILL_DAYS = 5
EGARCH_RETURN_DECIMALS = 12
MAX_MONTHLY_OBS = 23
DAILY_STRIP_CHANNELS = 4
DAILY_STRIP_CHANNEL_NAMES = [
    "close_rel",
    "ReturnFromPrice",
    "log1p(Volume)",
    "volume_observed",
]

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

# === Framework-Phase PPO Config ===
FRAMEWORK_PHASE_NAME = "framework_selection"
FEATURE_PHASE_NAME = "feature_comparison"
ACTION_DISTRIBUTION_NAME = "masked_sigmoid_gaussian"
POLICY_SEMANTICS_VERSION = "bounded_v2"
DEFAULT_COMPARISON_PROTOCOL_ID = "repaired_inner12_outer26_v1"
LEGACY_COMPARISON_PROTOCOL_ID = "legacy_train_validation_test_v1"
DEFAULT_OBJECTIVE_PROFILE_ID = "risk_v1_equal_333"
DEFAULT_REWARD_PROFILE_ID = "reward_v1_rank70_mse30"
DEFAULT_TRAINING_METHOD_ID = "random_iid"
DEFAULT_INPUT_FEATURE_SET_ID = "canonical_11"
FRAMEWORK_PPO_LEARNING_RATE = 1e-4
FRAMEWORK_PPO_N_STEPS = 256
FRAMEWORK_PPO_BATCH_SIZE = 256
FRAMEWORK_PPO_N_EPOCHS = 10
FRAMEWORK_PPO_GAMMA = 1.0
FRAMEWORK_PPO_GAE_LAMBDA = 1.0
FRAMEWORK_PPO_CLIP_RANGE = 0.2
FRAMEWORK_PPO_ENT_COEF = 0.01
FRAMEWORK_PPO_VF_COEF = 0.5
FRAMEWORK_PPO_MAX_GRAD_NORM = 0.5
FRAMEWORK_PPO_EVAL_FREQUENCY = 512
DEFAULT_FEATURE_PROFILE_ID = "full_current_v1"
FEATURE_PROFILE_OUTPUT_DIR = "outputs/feature_profiles"
FEATURE_CANDIDATE_OUTPUT_DIR = "outputs/feature_candidates"
FEATURE_PHASE_BASE_FRAMEWORK_ID = "pit_3m_flat_context"
FEATURE_PHASE_TOTAL_TIMESTEPS = 8192

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
