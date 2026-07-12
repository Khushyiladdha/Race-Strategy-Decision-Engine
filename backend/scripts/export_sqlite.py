"""
Snapshot the cached races from Postgres into a committed SQLite file, so the deployed backend
(Railway — a single container with no database) runs self-contained via
    DATABASE_URL=sqlite:///data/race_data.db

Local dev still uses Postgres. Re-run this after fetching new races.

Usage:
    python scripts/export_sqlite.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base, Lap, PitStop, Race
from db.session import SessionLocal  # source = whatever DATABASE_URL points at (Postgres by default)

TARGET = Path(__file__).parent.parent / "data" / "race_data.db"


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if TARGET.exists():
        TARGET.unlink()

    target_engine = create_engine(f"sqlite:///{TARGET.as_posix()}")
    Base.metadata.create_all(target_engine)
    TargetSession = sessionmaker(bind=target_engine)

    src, tgt = SessionLocal(), TargetSession()
    try:
        for r in src.query(Race).order_by(Race.id).all():
            tgt.add(Race(id=r.id, year=r.year, round=r.round, circuit_key=r.circuit_key,
                         session_name=r.session_name, fetched_at=r.fetched_at))
        tgt.flush()
        for lp in src.query(Lap).order_by(Lap.id).all():
            tgt.add(Lap(id=lp.id, race_id=lp.race_id, driver=lp.driver, lap_number=lp.lap_number,
                        compound=lp.compound, lap_time_s=lp.lap_time_s,
                        stint_number=lp.stint_number, is_valid=lp.is_valid))
        for p in src.query(PitStop).order_by(PitStop.id).all():
            tgt.add(PitStop(id=p.id, race_id=p.race_id, driver=p.driver,
                            lap_number=p.lap_number, pit_duration_s=p.pit_duration_s))
        tgt.commit()

        print(f"races={tgt.query(Race).count()} laps={tgt.query(Lap).count()} "
              f"pitstops={tgt.query(PitStop).count()}")
        print(f"wrote {TARGET}")
    finally:
        src.close()
        tgt.close()


if __name__ == "__main__":
    main()
