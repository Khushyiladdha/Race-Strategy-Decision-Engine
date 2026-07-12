"""Strategy evaluation."""
import sys
from pathlib import Path

from fastapi import APIRouter, Depends

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.api import schemas, services
from app.api.deps import get_db

router = APIRouter(tags=["strategy"])


@router.post(
    "/strategy/evaluate",
    summary="Evaluate race strategies",
    description="Runs the deterministic engine and Monte Carlo robustness analysis for one circuit, "
                "returning the top-k robust strategy shapes with their cost breakdown and outcome "
                "distribution.",
    response_model=schemas.EvaluateResponse,
    responses={404: {"description": "Unknown circuit"}, 422: {"description": "Circuit cannot generate"}},
)
def evaluate(req: schemas.EvaluateRequest, session=Depends(get_db)) -> schemas.EvaluateResponse:
    return services.evaluate_circuit(session, req)
