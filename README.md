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

The simulator supports direct risk-level selection and a questionnaire path gated by the checked risk-tolerance artifact contract under `portfolio-simulator-web/model-artifacts/questionnaire-risk-tolerance/contract.json`. The allocation stage uses the bundled external optimizer artifacts when they pass runtime checks; results are historical diagnostics, not performance guarantees.

```powershell
cd portfolio-simulator-web
..\ppo-risk-model\.venv\Scripts\python.exe -m pip install -r ml-service\requirements-dev.txt
npm.cmd install
npm.cmd run dev
```

Then open the Vite client URL shown by the terminal, usually `http://localhost:5173`.
