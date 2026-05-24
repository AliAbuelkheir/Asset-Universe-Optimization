# Deployment

## Render form values

Use these values when creating the Render service:

| Field | Value |
| --- | --- |
| Service type | Web Service |
| Source | GitHub repository |
| Runtime | Docker |
| Root Directory | `portfolio-simulator-web` |
| Name | `portfolio-simulator-web` |
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
| `SIMULATOR_PROFILE` | `production` |
| `PYTHONUNBUFFERED` | `1` |

Do not set `VITE_API_BASE_URL` for the production build. The React app calls the same-origin FastAPI routes under `/api`.
`SIMULATOR_PROFILE=production` and local development expose the same benchmark set: Robin portfolio, profile equal-weight benchmark, full-universe benchmark, and EGX30. The opening-allocation and monthly-review simulator modes remain available in both production and local environments.

## Runtime layout

Render builds from `portfolio-simulator-web`, so runtime artifacts live under `portfolio-simulator-web/model-artifacts`:

- `model-artifacts/ppo-risk-model/data/ready`
- `model-artifacts/ppo-risk-model/outputs/best_model`
- `model-artifacts/deployment`
- `model-artifacts/questionnaire-risk-tolerance`

The FastAPI service serves both `/api/*` and the built React app from `client/dist`.

## Update workflow

1. Refresh runtime artifacts under `model-artifacts`.
2. Run `npm.cmd run build`.
3. Run the configured project check script.
4. Commit and push.
5. Render auto-deploys the pushed branch.

Render Free web services spin down after idle time and use an ephemeral filesystem. Treat this as a thesis/demo deployment target, not production financial infrastructure.
