"""Operational routes: liveness and version. Kept at root, where probes look."""
import sys
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.api import schemas, services
from app.api.deps import get_db
from app.api.version import API_VERSION, ENGINE_VERSION

router = APIRouter(tags=["ops"])


@router.get(
    "/health",
    summary="Liveness probe",
    description="Returns service status plus a live database connectivity check.",
    response_model=schemas.HealthResponse,
)
def health(session=Depends(get_db)) -> schemas.HealthResponse:
    try:
        session.execute(text("SELECT 1"))
        db_state = "connected"
    except Exception:
        db_state = "error"
    return schemas.HealthResponse(status="ok", version=API_VERSION, database=db_state)


@router.get(
    "/version",
    summary="Version metadata",
    description="Engine/API versions and the timestamp of the last generated validation report.",
    response_model=schemas.VersionResponse,
)
def version() -> schemas.VersionResponse:
    return schemas.VersionResponse(
        engine_version=ENGINE_VERSION,
        api_version=API_VERSION,
        validation_report=services.validation_report_mtime(),
    )
