"""Build a realistic sample_input_raw_ohlcv.json from the project's CSV data.

Reads the low_risk_dataset_final.csv, extracts raw OHLCV for a subset of assets
(5 assets — to demonstrate dynamic-N), and writes a sample_input JSON the
package can ingest end-to-end.

Run once to regenerate samples; commit the resulting JSON files.
"""

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

CSV_PATH = PROJECT_ROOT / 'low_risk_dataset_final.csv'

# 5-asset subset to demonstrate dynamic-N (LOW universe has 10 trained-on, we
# pick 5 to show the model handles smaller universes).
SAMPLE_ASSETS = ['Gold', 'TBills', 'Eastern_Tobacco', 'Commercial_Int_Bank', 'Edita_Food']
TARGET_MONTH = '2025-08'

# Use ~9 months of history (~190 trading days) ending the day before target_month
HISTORY_START = '2024-11-01'


def main():
    df = pd.read_csv(CSV_PATH, skipinitialspace=True)
    df.columns = df.columns.str.strip()
    df['Date'] = pd.to_datetime(df['Date'])
    df['Asset'] = df['Asset'].astype(str).str.strip()

    # Filter to our 5 assets + history range
    df = df[df['Asset'].isin(SAMPLE_ASSETS)]
    df = df[df['Date'] >= pd.Timestamp(HISTORY_START)]
    df = df[df['Date'] < pd.Timestamp(TARGET_MONTH + '-01')]
    df = df[df['is_active'] == 1].sort_values(['Asset', 'Date'])

    asset_data = []
    for asset in SAMPLE_ASSETS:
        g = df[df['Asset'] == asset].sort_values('Date')
        if len(g) == 0:
            print(f"  skipping {asset} — no data in range")
            continue
        asset_data.append({
            'asset': asset,
            'dates': g['Date'].dt.strftime('%Y-%m-%d').tolist(),
            'close': g['Close'].astype(float).round(4).tolist(),
            'open':  g['Open'].astype(float).round(4).tolist() if 'Open' in g.columns else None,
            'high':  g['High'].astype(float).round(4).tolist() if 'High' in g.columns else None,
            'low':   g['Low'].astype(float).round(4).tolist() if 'Low' in g.columns else None,
        })
        print(f"  {asset}: {len(g)} trading days from {g.Date.min().date()} to {g.Date.max().date()}")

    sample = {
        'tier': 'low',
        'target_month': TARGET_MONTH,
        'input_kind': 'raw_ohlcv',
        'asset_data': asset_data,
    }

    out_path = Path(__file__).parent / 'sample_input_raw_ohlcv.json'
    out_path.write_text(json.dumps(sample, indent=2))
    print(f"\nWrote {out_path} ({len(asset_data)} assets, target {TARGET_MONTH})")


if __name__ == '__main__':
    main()
