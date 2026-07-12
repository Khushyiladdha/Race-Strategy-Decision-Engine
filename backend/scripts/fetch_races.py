"""
Stage 0 — pull FastF1 race sessions and persist to Postgres.

Usage:
    python scripts/fetch_races.py            # fetch all configured races
    python scripts/fetch_races.py --verify   # print summary table, no fetch
"""
import argparse
import sys
import time
from pathlib import Path

import fastf1
import pandas as pd

# allow `from db.xxx` regardless of cwd
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.models import Race, Lap, PitStop
from db.session import SessionLocal, init_db

CACHE_DIR = Path(__file__).parent.parent / "data" / "fastf1_cache"

RACES = [
    {"year": 2023, "round": 1,  "circuit_key": "bahrain"},    # clean 1-stop baseline
    {"year": 2023, "round": 3,  "circuit_key": "australian"}, # red flag + SC, multi-stop
    {"year": 2023, "round": 7,  "circuit_key": "spanish"},    # classic 1-vs-2 stop
    {"year": 2023, "round": 15, "circuit_key": "singapore"},  # low-deg anomaly
    {"year": 2023, "round": 16, "circuit_key": "japanese"},   # SC lap 1 + strategy variety
    {"year": 2023, "round": 9,  "circuit_key": "austrian"},   # VSC + normal race split
]


def _timedelta_to_seconds(td) -> float | None:
    if pd.isna(td):
        return None
    try:
        return td.total_seconds()
    except AttributeError:
        return None


def fetch_race(year: int, round_: int, circuit_key: str, session: object) -> None:
    print(f"\n-> {year} {circuit_key.title()} GP (round {round_})")

    ff1_session = fastf1.get_session(year, round_, "R")
    ff1_session.load(telemetry=False, weather=False, messages=False)

    laps_df = ff1_session.laps
    if laps_df.empty:
        print("  WARNING: no lap data returned — skipping")
        return

    # upsert Race row
    race = session.query(Race).filter_by(year=year, round=round_).first()
    if race is None:
        race = Race(year=year, round=round_, circuit_key=circuit_key)
        session.add(race)
        session.flush()
        print(f"  created race id={race.id}")
    else:
        # re-fetch: drop existing children and re-insert
        session.query(Lap).filter_by(race_id=race.id).delete()
        session.query(PitStop).filter_by(race_id=race.id).delete()
        print(f"  refreshing race id={race.id}")

    # build Lap rows
    lap_rows = []
    for _, row in laps_df.iterrows():
        lap_rows.append(Lap(
            race_id=race.id,
            driver=str(row.get("Driver", ""))[:3],
            lap_number=int(row["LapNumber"]) if not pd.isna(row["LapNumber"]) else 0,
            compound=str(row["Compound"]) if not pd.isna(row.get("Compound")) else None,
            lap_time_s=_timedelta_to_seconds(row.get("LapTime")),
            stint_number=int(row["Stint"]) if not pd.isna(row.get("Stint")) else None,
            is_valid=bool(row.get("IsAccurate", False)),
        ))

    session.bulk_save_objects(lap_rows)

    # build PitStop rows from laps flagged as pit laps
    pit_laps = laps_df[laps_df["PitOutTime"].notna() | laps_df["PitInTime"].notna()]
    pit_rows = []
    seen = set()
    for _, row in pit_laps.iterrows():
        driver = str(row.get("Driver", ""))[:3]
        lap_num = int(row["LapNumber"]) if not pd.isna(row["LapNumber"]) else 0
        key = (driver, lap_num)
        if key in seen:
            continue
        seen.add(key)

        duration = None
        if not pd.isna(row.get("PitInTime")) and not pd.isna(row.get("PitOutTime")):
            try:
                duration = (row["PitOutTime"] - row["PitInTime"]).total_seconds()
                if duration < 0 or duration > 120:  # sanity: ignore nonsense values
                    duration = None
            except Exception:
                duration = None

        pit_rows.append(PitStop(
            race_id=race.id,
            driver=driver,
            lap_number=lap_num,
            pit_duration_s=duration,
        ))

    session.bulk_save_objects(pit_rows)
    session.commit()
    print(f"  {len(lap_rows)} laps, {len(pit_rows)} pit events committed")


def verify(session: object) -> None:
    print("\n=== Stage 0 Verification ===\n")
    races = session.query(Race).order_by(Race.year, Race.round).all()
    if not races:
        print("No races in DB. Run without --verify first.")
        return

    for race in races:
        lap_count = session.query(Lap).filter_by(race_id=race.id).count()
        pit_count = session.query(PitStop).filter_by(race_id=race.id).count()
        compounds = (
            session.query(Lap.compound)
            .filter(Lap.race_id == race.id, Lap.compound.isnot(None))
            .distinct()
            .all()
        )
        compound_list = sorted({c[0] for c in compounds})
        flag = "OK" if lap_count >= 500 and len(compound_list) >= 2 else "WARN"
        print(
            f"[{flag}] {race.year} {race.circuit_key.title():12} "
            f"laps={lap_count:5}  pits={pit_count:3}  compounds={compound_list}"
        )

    # load-speed check on first race
    first = races[0]
    t0 = time.perf_counter()
    _ = (
        session.query(Lap)
        .filter_by(race_id=first.id)
        .all()
    )
    elapsed = time.perf_counter() - t0
    speed_flag = "OK" if elapsed < 1.0 else "SLOW"
    print(f"\n[{speed_flag}] Full lap query for race id={first.id}: {elapsed:.3f}s")

    # print sample rows for first race
    print(f"\nSample laps — {first.year} {first.circuit_key.title()}:")
    print(f"{'lap':>4}  {'driver':<6}  {'compound':<8}  {'lap_time_s':>10}  {'pit?'}")
    print("-" * 48)
    sample = (
        session.query(Lap)
        .filter(Lap.race_id == first.id, Lap.lap_time_s.isnot(None))
        .order_by(Lap.lap_number)
        .limit(10)
        .all()
    )
    pit_lap_numbers = {
        ps.lap_number
        for ps in session.query(PitStop).filter_by(race_id=first.id).all()
    }
    for lap in sample:
        is_pit = "YES" if lap.lap_number in pit_lap_numbers else ""
        print(
            f"{lap.lap_number:>4}  {lap.driver:<6}  "
            f"{(lap.compound or 'N/A'):<8}  {lap.lap_time_s:>10.3f}  {is_pit}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", help="Print summary only")
    args = parser.parse_args()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))

    init_db()
    session = SessionLocal()

    try:
        if args.verify:
            verify(session)
        else:
            failed = []
            for race_cfg in RACES:
                try:
                    fetch_race(
                        year=race_cfg["year"],
                        round_=race_cfg["round"],
                        circuit_key=race_cfg["circuit_key"],
                        session=session,
                    )
                except Exception as e:
                    print(f"  FAILED ({race_cfg['circuit_key']} {race_cfg['year']}): {e} — skipping")
                    failed.append(race_cfg["circuit_key"])
            if failed:
                print(f"\nCompleted with failures: {failed}. Run --verify to see what loaded.")
            else:
                print("\nAll races fetched. Run with --verify to confirm.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
