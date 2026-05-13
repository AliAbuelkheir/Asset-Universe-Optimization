"""Load macro features (inflation + interest rates) from bundled Excel files.

The deployment package bundles current Egyptian inflation and monthly interest
rate data in `deployment/data/`. To update macro values, replace those Excel
files with fresh exports from the central bank.
"""

from pathlib import Path

import numpy as np
import pandas as pd


def load_macro_features(data_dir: Path) -> pd.DataFrame:
    """Read inflation + interest rate Excel files, return monthly DataFrame.

    Returns:
        DataFrame indexed by month-start Timestamp with columns:
          headline_inflation_mom, core_inflation_mom,
          deposit_rate_short, lending_rate_corporate
    """
    inf_path = data_dir / 'Inflations Historical.xlsx'
    int_path = data_dir / 'Monthly Interest Rates Historical.xlsx'

    if not inf_path.exists():
        raise FileNotFoundError(
            f"Inflation data not found at {inf_path}. "
            "The deployment package needs the bundled Excel files."
        )
    if not int_path.exists():
        raise FileNotFoundError(
            f"Interest rate data not found at {int_path}. "
            "The deployment package needs the bundled Excel files."
        )

    # Inflation
    inf_df = pd.read_excel(
        inf_path, sheet_name='Inflation Rates', skiprows=1,
        usecols='A:E', nrows=194,
    )
    inf_df.columns = ['Date', 'headline_inflation_mom', 'core_inflation_mom',
                      'regulated_inflation_mom', 'fruit_veg_inflation_mom']
    inf_df['Date'] = pd.to_datetime(
        inf_df['Date'].astype(str).str.strip(), format='%b %Y'
    )
    for col in inf_df.columns[1:]:
        inf_df[col] = inf_df[col].astype(str).str.replace('%', '').astype(float) / 100.0
    inf_df = inf_df.sort_values('Date').set_index('Date')
    inf_df = inf_df[['headline_inflation_mom', 'core_inflation_mom']]

    # Interest rates
    int_df = pd.read_excel(
        int_path, sheet_name='Monthly Rates', skiprows=2,
        usecols='A:E', nrows=188,
    )
    int_df.columns = ['Date', 'deposit_rate_short', 'deposit_rate_medium',
                      'deposit_rate_long', 'lending_rate_corporate']
    int_df['Date'] = pd.to_datetime(
        int_df['Date'].astype(str).str.strip().str.replace(' - ', ' '),
        format='%b %Y',
    )
    for col in int_df.columns[1:]:
        int_df[col] = int_df[col].astype(str).str.replace('%', '').astype(float) / 100.0
    int_df = int_df.sort_values('Date').set_index('Date')
    int_df = int_df[['deposit_rate_short', 'lending_rate_corporate']]

    macro = inf_df.join(int_df, how='outer').ffill().bfill()
    return macro


def build_macro_tensor(
    data_dir: Path,
    dates: np.ndarray | list,
    n_assets: int,
    feature_names: list = None,
) -> np.ndarray:
    """Build macro tensor (T, N, n_macro) by broadcasting monthly values daily.

    The macro values are the same for all assets on a given day (broadcast).
    For dates that fall mid-month, we use the most recent prior monthly value.
    """
    macro_monthly = load_macro_features(data_dir)
    if feature_names is None:
        feature_names = list(macro_monthly.columns)

    n_macro = len(feature_names)
    macro_tensor = np.zeros((len(dates), n_assets, n_macro), dtype=np.float32)

    for t, date in enumerate(dates):
        month_key = pd.Timestamp(date).to_period('M').to_timestamp()
        if month_key in macro_monthly.index:
            row = macro_monthly.loc[month_key, feature_names].values.astype(np.float32)
        else:
            prior = macro_monthly.index[macro_monthly.index <= pd.Timestamp(date)]
            if len(prior) > 0:
                row = macro_monthly.loc[prior[-1], feature_names].values.astype(np.float32)
            else:
                row = np.zeros(n_macro, dtype=np.float32)
        macro_tensor[t, :, :] = row[np.newaxis, :]

    return np.nan_to_num(macro_tensor, nan=0.0, posinf=0.0, neginf=0.0)


def latest_macro_date(data_dir: Path) -> pd.Timestamp:
    """Return the most recent month covered by the bundled macro data.

    Used to warn the developer if macro data is stale (> 6 months old).
    """
    macro = load_macro_features(data_dir)
    return macro.index.max()
