"""
FastAPI application for the Race Strategy Decision Engine.

A thin HTTP layer over the Stage 0-4 engine. Ops routes (/health, /version) live at root;
everything else is namespaced under /api/v1 so a future schema change can ship as /api/v2.
"""
import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.api.services import CannotGenerate, UnknownCircuit
from app.api.version import API_VERSION
from app.api.routers import insights, ops, races, report, strategy, validation

# CORS origins are env-driven so the deployed Vercel domain can be allow-listed without a code change.
_DEFAULT_ORIGINS = (
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
)
_CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", _DEFAULT_ORIGINS).split(",") if o.strip()]

app = FastAPI(
    title="Race Strategy Decision Engine",
    version=API_VERSION,
    description=(
        "HTTP API over an F1 pit-strategy engine: exhaustive strategy generation, Monte Carlo "
        "robustness analysis, and historical validation against real 2023 race data."
    ),
    openapi_tags=[
        {"name": "ops", "description": "Liveness and version."},
        {"name": "races", "description": "Discover cached races."},
        {"name": "strategy", "description": "Evaluate and rank strategies."},
        {"name": "validation", "description": "Predicted vs. actual, per race."},
        {"name": "report", "description": "Structured strategy report + PDF."},
        {"name": "insights", "description": "Model internals — degradation curves."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(UnknownCircuit)
async def _unknown_circuit(request: Request, exc: UnknownCircuit) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(CannotGenerate)
async def _cannot_generate(request: Request, exc: CannotGenerate) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# Ops at root; functional routes under /api/v1.
app.include_router(ops.router)
app.include_router(races.router, prefix="/api/v1")
app.include_router(strategy.router, prefix="/api/v1")
app.include_router(validation.router, prefix="/api/v1")
app.include_router(report.router, prefix="/api/v1")
app.include_router(insights.router, prefix="/api/v1")
