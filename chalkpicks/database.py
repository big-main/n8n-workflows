from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./chalkpicks.db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    subscription_tier = Column(String, default="free")  # free | pro | sharp
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, nullable=True)

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    refresh_token = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)

    user = relationship("User", back_populates="sessions")


class Game(Base):
    __tablename__ = "games"

    id = Column(String, primary_key=True, index=True)
    sport = Column(String, nullable=False, index=True)
    league = Column(String, nullable=False, index=True)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    game_time = Column(DateTime, nullable=False, index=True)

    home_spread = Column(Float, nullable=True)
    away_spread = Column(Float, nullable=True)
    home_spread_odds = Column(Integer, nullable=True)
    away_spread_odds = Column(Integer, nullable=True)
    home_moneyline = Column(Integer, nullable=True)
    away_moneyline = Column(Integer, nullable=True)
    total = Column(Float, nullable=True)
    over_odds = Column(Integer, nullable=True)
    under_odds = Column(Integer, nullable=True)

    home_public_pct = Column(Float, nullable=True)
    away_public_pct = Column(Float, nullable=True)
    over_public_pct = Column(Float, nullable=True)

    status = Column(String, default="scheduled")  # scheduled | live | final
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    picks = relationship("Pick", back_populates="game")
    line_movements = relationship("LineMovement", back_populates="game", cascade="all, delete-orphan")


class Pick(Base):
    __tablename__ = "picks"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String, ForeignKey("games.id"), nullable=False)

    pick_team = Column(String, nullable=False)
    pick_type = Column(String, nullable=False)   # spread | moneyline | total_over | total_under
    pick_value = Column(Float, nullable=True)     # spread number or total
    pick_odds = Column(Integer, nullable=False)

    chalk_score = Column(Float, nullable=False)  # 0–100
    confidence = Column(String, nullable=False)  # LOW | MEDIUM | HIGH | ELITE
    ev = Column(Float, nullable=True)            # expected value %

    line_value_score = Column(Float, nullable=True)
    form_score = Column(Float, nullable=True)
    sharp_score = Column(Float, nullable=True)
    situational_score = Column(Float, nullable=True)
    h2h_score = Column(Float, nullable=True)

    pick_analysis = Column(Text, nullable=True)
    is_best_bet = Column(Boolean, default=False)
    required_tier = Column(String, default="free")  # free | pro | sharp

    result = Column(String, nullable=True)       # WIN | LOSS | PUSH | null
    profit_loss = Column(Float, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    game = relationship("Game", back_populates="picks")


class LineMovement(Base):
    __tablename__ = "line_movements"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String, ForeignKey("games.id"), nullable=False)
    home_spread = Column(Float, nullable=True)
    away_spread = Column(Float, nullable=True)
    home_moneyline = Column(Integer, nullable=True)
    away_moneyline = Column(Integer, nullable=True)
    total = Column(Float, nullable=True)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    game = relationship("Game", back_populates="line_movements")


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
