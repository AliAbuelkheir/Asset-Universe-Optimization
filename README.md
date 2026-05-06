# Bachelor Thesis Portfolio Simulator

This repository is now organized as a small monorepo:

- `ppo-risk-model/` contains the existing PPO ranked-risk research project, data pipeline, tests, documentation, and promoted model artifacts.
- `portfolio-simulator-web/` contains the stateless MERN-compatible simulation app.
- `thesis/` remains unchanged as the thesis source and PDF workspace.

## Run The PPO Project

```powershell
cd ppo-risk-model
.\.venv\Scripts\python.exe src\data_processing\validate_model_dataset.py
.\.venv\Scripts\python.exe -m pytest tests
```

## Run The Web Simulator

The first app version supports fast mode with direct risk-level selection. The questionnaire route is intentionally disabled until the risk-tolerance model contract is received. The optimizer uses a deterministic equal-weight mock adapter until the external PPO optimizer files are provided.

```powershell
cd portfolio-simulator-web
..\ppo-risk-model\.venv\Scripts\python.exe -m pip install -r ml-service\requirements.txt
npm.cmd install
npm.cmd run dev
```

Then open the Vite client URL shown by the terminal, usually `http://localhost:5173`.
