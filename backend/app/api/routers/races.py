"""Race discovery."""
import sys
from pathlib import Path

from fastapi import APIRouter, Depends

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.api import schemas, services
from app.api.deps import get_db

router = APIRouter(tags=["races"])


@router.get(
    "/races",
    summary="List cached races",
    description="Every race in the cache, with whether the engine can generate strategies for it.",
    response_model=list[schemas.RaceListItem],
)
def get_races(session=Depends(get_db)) -> list[schemas.RaceListItem]:
    return services.list_races(session)
