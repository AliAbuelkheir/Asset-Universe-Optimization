from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .core import available_months, health, risk_levels, run_fast_simulation

app = FastAPI(title="Portfolio Simulator ML Service", version="0.1.0")


class FastSimulationRequest(BaseModel):
    month: str
    riskLevel: str
    durationMonths: int | None = None


@app.get("/health")
def get_health() -> dict:
    return health()


@app.get("/months")
def get_months() -> list[dict]:
    return available_months()


@app.get("/risk-levels")
def get_risk_levels() -> list[dict]:
    return risk_levels()


@app.post("/simulations/fast")
def post_fast_simulation(request: FastSimulationRequest) -> dict:
    try:
        return run_fast_simulation(request.month, request.riskLevel, request.durationMonths)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/simulations/questionnaire")
def post_questionnaire_simulation() -> dict:
    raise HTTPException(
        status_code=501,
        detail="Questionnaire inference is disabled until the risk-tolerance model contract is received.",
    )
