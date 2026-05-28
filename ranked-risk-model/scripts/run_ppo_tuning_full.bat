@echo off
setlocal

cd /d "%~dp0.."

echo Starting full Optuna PPO tuning run.
echo This should only be used after the framework and feature set are locked.

".venv\Scripts\python.exe" -m src.training.tune_ppo --execute --n-trials 80 --total-timesteps 32768

pause
