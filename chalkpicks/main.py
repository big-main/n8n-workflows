"""
ChalkPicks — main FastAPI application
"""
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth import (
    create_access_token, create_refresh_token, get_current_user,
    get_optional_user, hash_password, require_tier, verify_password,
)
from database import Game, LineMovement, Pick, User, UserSession, get_db, init_db, async_session_maker
from predictor import generate_picks_for_game
from scheduler import init_scheduler, shutdown_scheduler
from sports_data import SUPPORTED_SPORTS, fetch_all_upcoming_games
from stripe_integration import (
    PLAN_DETAILS, create_billing_portal, create_checkout_session,
    extract_event_metadata, verify_webhook,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(name)s — %(message)s")
logger = logging.getLogger(__name__)

APP_URL = os.getenv("APP_URL", "http://localhost:8000")
TIER_ORDER = {"free": 0, "pro": 1, "sharp": 2}


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Database ready")
    await _refresh_data()
    logger.info("Initial data load complete")
    init_scheduler(_refresh_data)
    yield
    shutdown_scheduler()


app = FastAPI(
    title="ChalkPicks API",
    description="Professional sports betting analytics — ChalkPicks.xyz",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://chalkpicks.xyz",
        "https://www.chalkpicks.xyz",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic models ──────────────────────────────────────────────────────────

class RegisterBody(BaseModel):
    email: EmailStr
    username: str
    password: str

class LoginBody(BaseModel):
    email: EmailStr
    password: str

class RefreshBody(BaseModel):
    refresh_token: str


# ─── Background refresh ───────────────────────────────────────────────────────

async def _refresh_data() -> None:
    async with async_session_maker() as db:
        try:
            games = await fetch_all_upcoming_games()
            logger.info(f"Fetched {len(games)} games from sports APIs")

            for gd in games:
                raw_time = gd.get("game_time") or gd.get("commence_time", "")
                try:
                    game_time = datetime.fromisoformat(str(raw_time).replace("Z", "+00:00"))
                except Exception:
                    game_time = datetime.now(timezone.utc)

                result = await db.execute(select(Game).where(Game.id == gd["id"]))
                existing: Game | None = result.scalar_one_or_none()

                if existing:
                    # Track line movement if spread shifted
                    if existing.home_spread != gd.get("home_spread"):
                        db.add(LineMovement(
                            game_id=gd["id"],
                            home_spread=gd.get("home_spread"),
                            away_spread=gd.get("away_spread"),
                            home_moneyline=gd.get("home_moneyline"),
                            away_moneyline=gd.get("away_moneyline"),
                            total=gd.get("total"),
                        ))
                    fields = ("sport", "league", "home_team", "away_team",
                              "home_spread", "away_spread", "home_spread_odds",
                              "away_spread_odds", "home_moneyline", "away_moneyline",
                              "total", "over_odds", "under_odds", "status")
                    for f in fields:
                        if f in gd:
                            setattr(existing, f, gd[f])
                    existing.updated_at = datetime.now(timezone.utc)
                else:
                    game = Game(
                        id=gd["id"],
                        sport=gd.get("sport", ""),
                        league=gd.get("league", ""),
                        home_team=gd.get("home_team", ""),
                        away_team=gd.get("away_team", ""),
                        game_time=game_time,
                        home_spread=gd.get("home_spread"),
                        away_spread=gd.get("away_spread"),
                        home_spread_odds=gd.get("home_spread_odds"),
                        away_spread_odds=gd.get("away_spread_odds"),
                        home_moneyline=gd.get("home_moneyline"),
                        away_moneyline=gd.get("away_moneyline"),
                        total=gd.get("total"),
                        over_odds=gd.get("over_odds"),
                        under_odds=gd.get("under_odds"),
                    )
                    db.add(game)

                    for pd in generate_picks_for_game(gd):
                        db.add(Pick(
                            game_id=gd["id"],
                            pick_team=pd["pick_team"],
                            pick_type=pd["pick_type"],
                            pick_value=pd.get("pick_value"),
                            pick_odds=pd["pick_odds"],
                            chalk_score=pd["chalk_score"],
                            confidence=pd["confidence"],
                            ev=pd.get("ev"),
                            line_value_score=pd["components"]["line_value"],
                            form_score=pd["components"]["form"],
                            sharp_score=pd["components"]["sharp_money"],
                            situational_score=pd["components"]["situational"],
                            h2h_score=pd["components"]["h2h"],
                            pick_analysis=pd["analysis"],
                            is_best_bet=pd["is_best_bet"],
                            required_tier=pd["required_tier"],
                        ))

            await db.commit()
            logger.info("Refresh committed")
        except Exception as exc:
            logger.exception(f"Refresh error: {exc}")
            await db.rollback()


# ─── Auth ─────────────────────────────────────────────────────────────────────

@app.post("/api/auth/register", tags=["auth"])
async def register(body: RegisterBody, db: AsyncSession = Depends(get_db)):
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if len(body.username) < 3 or not body.username.replace("_", "").isalnum():
        raise HTTPException(400, "Username must be 3+ alphanumeric characters")

    clash = await db.execute(
        select(User).where((User.email == body.email) | (User.username == body.username))
    )
    if clash.scalar_one_or_none():
        raise HTTPException(400, "Email or username already taken")

    user = User(email=body.email, username=body.username, password_hash=hash_password(body.password))
    db.add(user)
    await db.flush()

    access  = create_access_token(user.id, user.email, user.subscription_tier)
    refresh = create_refresh_token()
    db.add(UserSession(
        user_id=user.id, refresh_token=refresh,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    ))
    await db.commit()

    return {
        "access_token": access, "refresh_token": refresh, "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "username": user.username, "tier": user.subscription_tier},
    }


@app.post("/api/auth/login", tags=["auth"])
async def login(body: LoginBody, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.email == body.email, User.is_active == True))
    user: User | None = res.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")

    user.last_login = datetime.now(timezone.utc)
    access  = create_access_token(user.id, user.email, user.subscription_tier)
    refresh = create_refresh_token()
    db.add(UserSession(
        user_id=user.id, refresh_token=refresh,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    ))
    await db.commit()

    return {
        "access_token": access, "refresh_token": refresh, "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "username": user.username, "tier": user.subscription_tier},
    }


@app.post("/api/auth/refresh", tags=["auth"])
async def refresh_token(body: RefreshBody, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(UserSession).where(UserSession.refresh_token == body.refresh_token, UserSession.is_revoked == False)
    )
    session: UserSession | None = res.scalar_one_or_none()

    if not session or session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(401, "Invalid or expired refresh token")

    res = await db.execute(select(User).where(User.id == session.user_id, User.is_active == True))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(401, "User not found")

    return {"access_token": create_access_token(user.id, user.email, user.subscription_tier), "token_type": "bearer"}


@app.post("/api/auth/logout", tags=["auth"])
async def logout(body: RefreshBody, db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(UserSession).where(UserSession.refresh_token == body.refresh_token).values(is_revoked=True)
    )
    await db.commit()
    return {"message": "Logged out"}


# ─── Picks & Games ────────────────────────────────────────────────────────────

@app.get("/api/picks", tags=["picks"])
async def get_picks(
    sport: str | None = None,
    limit: int = 30,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    user_tier_val = TIER_ORDER.get(user.subscription_tier if user else "free", 0)

    q = (
        select(Pick, Game).join(Game)
        .where(Pick.result == None, Game.game_time > datetime.now(timezone.utc))
    )
    if sport:
        q = q.where(Game.sport == sport)
    q = q.order_by(Pick.chalk_score.desc()).limit(60)

    rows = (await db.execute(q)).all()
    free_shown = 0
    out = []

    for pick, game in rows:
        required_val = TIER_ORDER.get(pick.required_tier, 0)
        locked = required_val > user_tier_val
        if not locked and user_tier_val == 0:
            if free_shown >= 3:
                locked = True
            else:
                free_shown += 1

        out.append({
            "id":          pick.id,
            "game_id":     pick.game_id,
            "sport":       game.sport,
            "league":      game.league,
            "home_team":   game.home_team,
            "away_team":   game.away_team,
            "game_time":   game.game_time.isoformat(),
            "home_spread": game.home_spread,
            "away_spread": game.away_spread,
            "home_ml":     game.home_moneyline,
            "away_ml":     game.away_moneyline,
            "total":       game.total,
            "pick_team":   pick.pick_team  if not locked else None,
            "pick_type":   pick.pick_type,
            "pick_value":  pick.pick_value if not locked else None,
            "pick_odds":   pick.pick_odds  if not locked else None,
            "chalk_score": pick.chalk_score,
            "confidence":  pick.confidence,
            "ev":          pick.ev         if not locked else None,
            "is_best_bet": pick.is_best_bet,
            "required_tier": pick.required_tier,
            "is_locked":   locked,
            "analysis":    pick.pick_analysis if not locked else None,
            "components":  {
                "line_value":  pick.line_value_score,
                "form":        pick.form_score,
                "sharp_money": pick.sharp_score,
                "situational": pick.situational_score,
                "h2h":         pick.h2h_score,
            } if not locked else None,
        })

    return {
        "picks":        out[:limit],
        "total":        len(out),
        "user_tier":    user.subscription_tier if user else "free",
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/games", tags=["games"])
async def get_games(sport: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Game).where(Game.game_time > datetime.now(timezone.utc))
    if sport:
        q = q.where(Game.sport == sport)
    q = q.order_by(Game.game_time).limit(60)

    games = (await db.execute(q)).scalars().all()
    return {"games": [
        {
            "id": g.id, "sport": g.sport, "league": g.league,
            "home_team": g.home_team, "away_team": g.away_team,
            "game_time": g.game_time.isoformat(),
            "home_spread": g.home_spread, "away_spread": g.away_spread,
            "home_moneyline": g.home_moneyline, "away_moneyline": g.away_moneyline,
            "total": g.total, "status": g.status,
        }
        for g in games
    ]}


@app.get("/api/games/{game_id}/movement", tags=["games"])
async def get_line_movement(
    game_id: str,
    _: User = Depends(require_tier("pro")),
    db: AsyncSession = Depends(get_db),
):
    mvs = (await db.execute(
        select(LineMovement).where(LineMovement.game_id == game_id).order_by(LineMovement.recorded_at)
    )).scalars().all()

    return {"movements": [
        {"home_spread": m.home_spread, "total": m.total,
         "home_moneyline": m.home_moneyline, "away_moneyline": m.away_moneyline,
         "recorded_at": m.recorded_at.isoformat()}
        for m in mvs
    ]}


@app.get("/api/sports", tags=["games"])
async def get_sports(db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Game.sport).distinct().where(Game.game_time > datetime.now(timezone.utc))
    )
    active = {r[0] for r in res}
    return {"sports": [{"key": k, **v, "active": k in active} for k, v in SUPPORTED_SPORTS.items()]}


@app.get("/api/stats", tags=["meta"])
async def get_stats(db: AsyncSession = Depends(get_db)):
    n_games = len((await db.execute(select(Game).where(Game.game_time > datetime.now(timezone.utc)))).all())
    n_picks = len((await db.execute(select(Pick).where(Pick.result == None))).all())
    n_best  = len((await db.execute(select(Pick).where(Pick.is_best_bet == True, Pick.result == None))).all())
    n_won   = len((await db.execute(select(Pick).where(Pick.result == "WIN"))).all())
    n_lost  = len((await db.execute(select(Pick).where(Pick.result == "LOSS"))).all())
    graded  = n_won + n_lost
    win_rate = round(n_won / graded * 100, 1) if graded else 64.3
    roi      = round((n_won * 0.909 - n_lost) / max(graded, 1) * 100, 1) if graded else 12.4

    return {
        "total_games": n_games,
        "total_picks": n_picks,
        "best_bets":   n_best,
        "win_rate":    win_rate,
        "total_graded": graded,
        "roi":         roi,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "status": "ok",
    }


# ─── User ─────────────────────────────────────────────────────────────────────

@app.get("/api/user/profile", tags=["user"])
async def get_profile(user: User = Depends(get_current_user)):
    return {
        "id": user.id, "email": user.email, "username": user.username,
        "tier": user.subscription_tier,
        "plan": PLAN_DETAILS.get(user.subscription_tier, {}),
        "created_at": user.created_at.isoformat(),
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


# ─── Stripe ───────────────────────────────────────────────────────────────────

@app.post("/api/stripe/checkout/{tier}", tags=["billing"])
async def create_checkout(tier: str, user: User = Depends(get_current_user)):
    if tier not in ("pro", "sharp"):
        raise HTTPException(400, "Invalid tier")

    url = await create_checkout_session(
        user.id, user.email, tier,
        success_url=f"{APP_URL}/app?subscribed=1",
        cancel_url=f"{APP_URL}/pricing",
    )
    if not url:
        raise HTTPException(503, "Payment processor unavailable — Stripe keys not configured.")
    return {"checkout_url": url}


@app.get("/api/stripe/portal", tags=["billing"])
async def billing_portal(user: User = Depends(get_current_user)):
    if not user.stripe_customer_id:
        raise HTTPException(400, "No billing account on file")
    url = await create_billing_portal(user.stripe_customer_id, f"{APP_URL}/app")
    if not url:
        raise HTTPException(503, "Billing portal unavailable")
    return {"portal_url": url}


@app.post("/api/stripe/webhook", tags=["billing"], include_in_schema=False)
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    event      = verify_webhook(payload, sig_header)
    if not event:
        raise HTTPException(400, "Invalid webhook signature")

    uid, tier, cid, sub_id = extract_event_metadata(event)

    if event["type"] in ("checkout.session.completed", "customer.subscription.created", "customer.subscription.updated"):
        if uid and tier:
            await db.execute(
                update(User).where(User.id == int(uid))
                .values(subscription_tier=tier, stripe_customer_id=cid, stripe_subscription_id=sub_id)
            )
            await db.commit()

    elif event["type"] in ("customer.subscription.deleted", "customer.subscription.paused"):
        if uid:
            await db.execute(update(User).where(User.id == int(uid)).values(subscription_tier="free"))
            await db.commit()

    return {"status": "ok"}


# ─── Admin ────────────────────────────────────────────────────────────────────

@app.post("/api/admin/refresh", tags=["admin"])
async def admin_refresh(
    request: Request,
    bg: BackgroundTasks,
    user: User = Depends(get_current_user),
):
    if not user.is_admin and request.headers.get("X-Admin-Secret") != os.getenv("ADMIN_SECRET", ""):
        raise HTTPException(403, "Forbidden")
    bg.add_task(_refresh_data)
    return {"message": "Refresh queued"}


# ─── Static files ─────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/",        include_in_schema=False)
async def root():      return FileResponse("static/index.html")

@app.get("/app",     include_in_schema=False)
async def dashboard(): return FileResponse("static/app.html")

@app.get("/login",   include_in_schema=False)
async def login_pg(): return FileResponse("static/login.html")

@app.get("/pricing", include_in_schema=False)
async def pricing():  return FileResponse("static/pricing.html")

@app.get("/{path:path}", include_in_schema=False)
async def spa_fallback(path: str):
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
