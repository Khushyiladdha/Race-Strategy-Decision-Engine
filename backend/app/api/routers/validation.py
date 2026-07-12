"""Historical validation."""
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, Query

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.api import schemas, services
from app.api.deps import get_db

router = APIRouter(tags=["validation"])


@router.get(
    "/validation",
    summary="All-races validation",
    description="Aggregate metrics plus per-race predicted-vs-actual detail across every "
                "validated race. Served from the persisted report; pass refresh=true to recompute.",
    response_model=schemas.ValidationAllResponse,
)
def validation_all(
    refresh: bool = Query(default=False, description="Force a live recompute"),
    session=Depends(get_db),
) -> schemas.ValidationAllResponse:
    return services.get_validation_all(session, refresh=refresh)


@router.get(
    "/validation/{circuit_key}",
    summary="Single-race validation",
    description="Predicted-vs-actual detail for one circuit.",
    response_model=schemas.ValidationDetailOut,
    responses={404: {"description": "Unknown circuit"}, 422: {"description": "Circuit cannot generate"}},
)
def validation_one(
    circuit_key: str,
    refresh: bool = Query(default=False, description="Force a live recompute"),
    session=Depends(get_db),
) -> schemas.ValidationDetailOut:
    return services.get_validation_one(session, circuit_key, refresh=refresh)
