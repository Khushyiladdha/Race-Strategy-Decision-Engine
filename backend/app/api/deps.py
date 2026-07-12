"""FastAPI dependencies."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.session import SessionLocal


def get_db():
    """Yield a DB session, guaranteeing close even on error."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
