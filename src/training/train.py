# train.py - Train the month-batched shared scorer
#
# Training should consume data/ready/monthly_asset_panel.csv, batch rows by
# month, exclude metadata and target fields from model input, and optimize the
# month-level reward defined in the repository docs.
