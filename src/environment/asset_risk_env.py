# asset_risk_env.py - Custom Gymnasium environment for month-level risk scoring
#
# One environment step equals one month.
# The environment should read data/ready/monthly_asset_panel.csv, filter one
# month at a time, drop metadata and target columns from the model input, apply
# a shared scorer across the active asset rows, and compute one reward for the
# full month.
