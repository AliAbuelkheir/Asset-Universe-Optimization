# Deployment

## Render form values

Use these values when creating the Render service:

| Field | Value |
| --- | --- |
| Service type | Web Service |
| Source | GitHub repository |
| Runtime | Docker |
| Root Directory | `portfolio-simulator` |
| Name | `portfolio-simulator` |
| Branch | the branch containing these deployment files |
| Dockerfile Path | `Dockerfile` |
| Docker Build Context Directory | leave blank |
| Docker Command | leave blank |
| Instance Type | Free |
| Health Check Path | `/api/health` |
| Auto-Deploy | Yes |

Environment variables:

| Key | Value |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `PYTHONUNBUFFERED` | `1` |

Do not set `VITE_API_BASE_URL` for the production build. The React app calls the same-origin FastAPI routes under `/api`.
Production and local development expose the same benchmark set: profile optimizer portfolio, full-universe optimizer benchmark, profile MVO benchmark, full-universe MVO benchmark, and EGX30. The opening-allocation and monthly-review simulator modes remain available in both environments.

## Runtime layout

Render builds from `portfolio-simulator`, so runtime artifacts live under `portfolio-simulator/model-artifacts`:

- `model-artifacts/ranked-risk-model/data/ready`
- `model-artifacts/ranked-risk-model/outputs/best_model`
- `model-artifacts/deployment`
- `model-artifacts/questionnaire-risk-tolerance`
- `model-artifacts/precomputed-simulations/simulation_store.sqlite`

The FastAPI service serves both `/api/*` and the built React app from `client/dist`.
The deployed API reads precomputed simulation decisions and monthly returns from
the SQLite store. It does not run the optimizer or MVO allocation path during
requests.

## Update workflow

1. Refresh runtime artifacts under `model-artifacts`.
2. Regenerate the simulation store:
   `cd portfolio-simulator/ml-service && python -m app.precompute.regenerate_simulation_store`
   The interpreter used for this step must have
   `ml-service/requirements-regenerate.txt` installed.
3. Run `npm.cmd run build`.
4. Run the configured project check script.
5. Commit and push, including the regenerated SQLite store.
6. Render auto-deploys the pushed branch.

Render Free web services spin down after idle time and use an ephemeral filesystem. Treat this as a thesis/demo deployment target, not production financial infrastructure.
