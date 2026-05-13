from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .data import available_months, risk_levels
from .paths import APP_ROOT
from .schemas import (
    FastSimulationRequest,
    HealthResponse,
    MonthOption,
    QuestionnaireSimulationRequest,
    RiskLevelDefinition,
    SimulationReport,
)
from .simulation import health, run_fast_simulation, run_questionnaire_simulation

docs_url = None if os.getenv("ENVIRONMENT") == "production" else "/docs"
redoc_url = None if os.getenv("ENVIRONMENT") == "production" else "/redoc"
openapi_url = None if os.getenv("ENVIRONMENT") == "production" else "/openapi.json"

app = FastAPI(
    title="Portfolio Simulator ML Service",
    version="0.1.0",
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)


@app.get("/api/health", response_model=HealthResponse)
def get_health() -> dict:
    return health()


@app.get("/api/months", response_model=list[MonthOption])
def get_months() -> list[dict]:
    return available_months()


@app.get("/api/risk-levels", response_model=list[RiskLevelDefinition])
def get_risk_levels() -> list[dict]:
    return risk_levels()


@app.post("/api/simulations/fast", response_model=SimulationReport)
def post_fast_simulation(request: FastSimulationRequest) -> dict:
    try:
        return run_fast_simulation(request.month, request.riskLevel, request.durationMonths)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/simulations/questionnaire", response_model=SimulationReport)
def post_questionnaire_simulation(request: QuestionnaireSimulationRequest) -> dict:
    try:
        return run_questionnaire_simulation(
            request.month,
            request.questionnaire.model_dump(by_alias=True),
            request.durationMonths,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


CLIENT_DIST = APP_ROOT / "client" / "dist"
if CLIENT_DIST.exists():
    assets_dir = CLIENT_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def serve_client(path: str) -> FileResponse:
        requested = CLIENT_DIST / path
        if path and requested.exists() and requested.is_file():
            return FileResponse(requested)
        return FileResponse(CLIENT_DIST / "index.html")
