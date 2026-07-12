from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Race(Base):
    __tablename__ = "races"

    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False)
    round = Column(Integer, nullable=False)
    circuit_key = Column(String, nullable=False)
    session_name = Column(String, nullable=False, default="Race")
    fetched_at = Column(DateTime, default=datetime.utcnow)

    laps = relationship("Lap", back_populates="race", cascade="all, delete-orphan")
    pit_stops = relationship("PitStop", back_populates="race", cascade="all, delete-orphan")


class Lap(Base):
    __tablename__ = "laps"

    id = Column(Integer, primary_key=True)
    race_id = Column(Integer, ForeignKey("races.id"), nullable=False)
    driver = Column(String(3), nullable=False)
    lap_number = Column(Integer, nullable=False)
    compound = Column(String)          # NULL acceptable for in/out laps
    lap_time_s = Column(Float)         # NULL for in/out laps
    stint_number = Column(Integer)
    is_valid = Column(Boolean)

    race = relationship("Race", back_populates="laps")


class PitStop(Base):
    __tablename__ = "pit_stops"

    id = Column(Integer, primary_key=True)
    race_id = Column(Integer, ForeignKey("races.id"), nullable=False)
    driver = Column(String(3), nullable=False)
    lap_number = Column(Integer, nullable=False)
    pit_duration_s = Column(Float)     # NULL if not recorded

    race = relationship("Race", back_populates="pit_stops")
