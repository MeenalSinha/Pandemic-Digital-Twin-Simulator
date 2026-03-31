"""
Database Layer — Pandemic Digital Twin Simulator

Uses SQLAlchemy Core with aiosqlite for async SQLite in development
and asyncpg/PostgreSQL in production (set DATABASE_URL env var).

Stores:
  - simulation_runs    : every executed simulation with parameters + results
  - agent_analyses     : outputs from multi-agent pipeline
  - region_snapshots   : daily disease statistics per region
  - scenario_comparisons: what-if analysis results

Tables are created on startup if they don't exist (schema migration free).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column, DateTime, Float, Integer, String, Text,
    create_engine, text, MetaData, Table, insert, select
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

logger = logging.getLogger(__name__)

# ── Engine configuration ───────────────────────────────────────────────────────
# Dev: SQLite (no setup required)  |  Prod: postgresql+asyncpg://...
_RAW_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./pandemic_twin.db")

# asyncpg needs postgresql+asyncpg://  not postgres://
DATABASE_URL = _RAW_URL.replace("postgresql://", "postgresql+asyncpg://").replace(
    "postgres://", "postgresql+asyncpg://"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# ── ORM Models ────────────────────────────────────────────────────────────────

class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id:          Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_id:   Mapped[str]      = mapped_column(String(32), nullable=False, index=True)
    intervention:Mapped[str]      = mapped_column(String(64), nullable=False)
    days:        Mapped[int]      = mapped_column(Integer, nullable=False)
    r0:          Mapped[float]    = mapped_column(Float, nullable=False)
    basic_r0:    Mapped[float]    = mapped_column(Float, nullable=False)
    peak_infected:  Mapped[int]   = mapped_column(Integer, nullable=False)
    peak_day:    Mapped[int]      = mapped_column(Integer, nullable=False)
    total_infected: Mapped[int]   = mapped_column(Integer, nullable=False)
    total_deceased: Mapped[int]   = mapped_column(Integer, nullable=False)
    parameters:  Mapped[str]      = mapped_column(Text, nullable=False)   # JSON
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentAnalysis(Base):
    __tablename__ = "agent_analyses"

    id:           Mapped[int]     = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_id:    Mapped[str]     = mapped_column(String(32), nullable=False, index=True)
    severity:     Mapped[str]     = mapped_column(String(16), nullable=False)
    urgency:      Mapped[str]     = mapped_column(String(16), nullable=False)
    recommendation: Mapped[str]   = mapped_column(String(128), nullable=False)
    confidence:   Mapped[float]   = mapped_column(Float, nullable=False)
    synthesis:    Mapped[str]     = mapped_column(Text, nullable=False)   # JSON
    created_at:   Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RegionSnapshot(Base):
    __tablename__ = "region_snapshots"

    id:            Mapped[int]    = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_id:     Mapped[str]    = mapped_column(String(32), nullable=False, index=True)
    active_cases:  Mapped[int]    = mapped_column(Integer, nullable=False)
    total_cases:   Mapped[int]    = mapped_column(Integer, nullable=False)
    total_deaths:  Mapped[int]    = mapped_column(Integer, nullable=False)
    r_number:      Mapped[float]  = mapped_column(Float, nullable=False)
    vacc_coverage: Mapped[float]  = mapped_column(Float, nullable=False)
    weather_temp:  Mapped[float]  = mapped_column(Float, nullable=True)
    data_source:   Mapped[str]    = mapped_column(String(64), nullable=False)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScenarioComparison(Base):
    __tablename__ = "scenario_comparisons"

    id:            Mapped[int]    = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_id:     Mapped[str]    = mapped_column(String(32), nullable=False, index=True)
    best_scenario: Mapped[str]    = mapped_column(String(64), nullable=False)
    reduction_pct: Mapped[float]  = mapped_column(Float, nullable=False)
    lives_saved:   Mapped[int]    = mapped_column(Integer, nullable=False)
    comparisons:   Mapped[str]    = mapped_column(Text, nullable=False)   # JSON
    created_at:    Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── Database service ──────────────────────────────────────────────────────────

class DatabaseService:
    """
    Async database service. Call init_db() once on startup.
    All write operations are fire-and-forget with error logging —
    DB unavailability must never break the simulation API.
    """

    @staticmethod
    async def init_db() -> None:
        """Create all tables if they don't exist."""
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database initialised: %s", DATABASE_URL.split("://")[0])
        except Exception as e:
            logger.error("Database init failed (non-fatal): %s", e)

    @staticmethod
    async def save_simulation(region_id: str, intervention: str, days: int,
                               sim_result: Dict, params: Dict) -> Optional[int]:
        try:
            async with AsyncSessionLocal() as session:
                row = SimulationRun(
                    region_id=region_id,
                    intervention=intervention,
                    days=days,
                    r0=sim_result.get("r0", 0),
                    basic_r0=sim_result.get("basic_r0", 0),
                    peak_infected=sim_result.get("peak_infected", 0),
                    peak_day=sim_result.get("peak_day", 0),
                    total_infected=sim_result.get("total_infected", 0),
                    total_deceased=sim_result.get("total_deceased", 0),
                    parameters=json.dumps(params),
                )
                session.add(row)
                await session.commit()
                await session.refresh(row)
                return row.id
        except Exception as e:
            logger.warning("save_simulation failed (non-fatal): %s", e)
            return None

    @staticmethod
    async def save_agent_analysis(region_id: str, synthesis: Dict) -> Optional[int]:
        try:
            async with AsyncSessionLocal() as session:
                row = AgentAnalysis(
                    region_id=region_id,
                    severity=synthesis.get("overall_severity", "UNKNOWN"),
                    urgency=synthesis.get("urgency", "UNKNOWN"),
                    recommendation=synthesis.get("primary_recommendation", ""),
                    confidence=synthesis.get("confidence_summary", {}).get("overall", 0.0),
                    synthesis=json.dumps(synthesis),
                )
                session.add(row)
                await session.commit()
                await session.refresh(row)
                return row.id
        except Exception as e:
            logger.warning("save_agent_analysis failed (non-fatal): %s", e)
            return None

    @staticmethod
    async def save_region_snapshot(region_id: str, stats: Dict,
                                    weather: Dict) -> Optional[int]:
        try:
            async with AsyncSessionLocal() as session:
                row = RegionSnapshot(
                    region_id=region_id,
                    active_cases=stats.get("active_cases", 0),
                    total_cases=stats.get("total_cases", 0),
                    total_deaths=stats.get("total_deaths", 0),
                    r_number=stats.get("reproduction_number", 1.0),
                    vacc_coverage=stats.get("vaccination_coverage", 0.0),
                    weather_temp=weather.get("temperature"),
                    data_source=stats.get("source", "unknown"),
                )
                session.add(row)
                await session.commit()
                await session.refresh(row)
                return row.id
        except Exception as e:
            logger.warning("save_region_snapshot failed (non-fatal): %s", e)
            return None

    @staticmethod
    async def save_scenario_comparison(region_id: str, best_scenario: str,
                                        reduction_pct: float, lives_saved: int,
                                        comparisons: List[Dict]) -> Optional[int]:
        try:
            async with AsyncSessionLocal() as session:
                row = ScenarioComparison(
                    region_id=region_id,
                    best_scenario=best_scenario,
                    reduction_pct=reduction_pct,
                    lives_saved=lives_saved,
                    comparisons=json.dumps(comparisons),
                )
                session.add(row)
                await session.commit()
                await session.refresh(row)
                return row.id
        except Exception as e:
            logger.warning("save_scenario_comparison failed (non-fatal): %s", e)
            return None

    @staticmethod
    async def get_recent_simulations(region_id: str, limit: int = 10) -> List[Dict]:
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(SimulationRun)
                    .where(SimulationRun.region_id == region_id)
                    .order_by(SimulationRun.created_at.desc())
                    .limit(limit)
                )
                rows = result.scalars().all()
                return [
                    {
                        "id": r.id,
                        "intervention": r.intervention,
                        "r0": r.r0,
                        "peak_infected": r.peak_infected,
                        "peak_day": r.peak_day,
                        "total_infected": r.total_infected,
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.warning("get_recent_simulations failed: %s", e)
            return []

    @staticmethod
    async def get_simulation_history_summary(region_id: str) -> Dict:
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(SimulationRun)
                    .where(SimulationRun.region_id == region_id)
                    .order_by(SimulationRun.created_at.desc())
                    .limit(50)
                )
                rows = result.scalars().all()
                if not rows:
                    return {"total_simulations": 0, "interventions_tested": []}
                return {
                    "total_simulations": len(rows),
                    "interventions_tested": list({r.intervention for r in rows}),
                    "latest_r0": rows[0].r0,
                    "latest_intervention": rows[0].intervention,
                    "latest_run": rows[0].created_at.isoformat(),
                }
        except Exception as e:
            logger.warning("get_simulation_history_summary failed: %s", e)
            return {"total_simulations": 0}


db = DatabaseService()
