"""Model insights — the fitted tyre-degradation curves per compound."""
import sys
from pathlib import Path

from fastapi import APIRouter, Depends

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.api import schemas, services
from app.api.deps import get_db

router = APIRouter(tags=["insights"])


@router.get(
    "/degradation/{circuit_key}",
    summary="Tyre degradation curves",
    description="The fitted deg(n) = a·n + b·n² per available compound, sampled for plotting — the "
    "engine's answer to 'how does the degradation model work?'.",
    response_model=schemas.DegradationResponse,
    responses={404: {"description": "Unknown circuit"}, 422: {"description": "Circuit cannot generate"}},
)
def degradation(circuit_key: str, session=Depends(get_db)) -> schemas.DegradationResponse:
    return services.get_degradation(session, circuit_key)
