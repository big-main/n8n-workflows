import asyncio
import logging
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

SUPPORTED_SPORTS: Dict[str, Dict] = {
    "americanfootball_nfl":   {"name": "NFL",               "icon": "🏈", "category": "football"},
    "americanfootball_ncaaf": {"name": "College Football",  "icon": "🏈", "category": "football"},
    "basketball_nba":         {"name": "NBA",               "icon": "🏀", "category": "basketball"},
    "basketball_ncaab":       {"name": "College Basketball","icon": "🏀", "category": "basketball"},
    "baseball_mlb":           {"name": "MLB",               "icon": "⚾", "category": "baseball"},
    "icehockey_nhl":          {"name": "NHL",               "icon": "🏒", "category": "hockey"},
    "soccer_usa_mls":         {"name": "MLS",               "icon": "⚽", "category": "soccer"},
}

# Map sport key -> ESPN API path for live scores
ESPN_SPORT_MAP: Dict[str, str] = {
    "americanfootball_nfl":   "football/nfl",
    "americanfootball_ncaaf": "football/college-football",
    "basketball_nba":         "basketball/nba",
    "basketball_ncaab":       "basketball/mens-college-basketball",
    "baseball_mlb":           "baseball/mlb",
    "icehockey_nhl":          "hockey/nhl",
    "soccer_usa_mls":         "soccer/usa.1",
}

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"

PREFERRED_BOOKS = ["draftkings", "fanduel", "betmgm", "betrivers", "pointsbet"]


# ─── Odds API ─────────────────────────────────────────────────────────────────

async def fetch_odds(sport: str) -> List[Dict]:
    if not ODDS_API_KEY:
        return _mock_odds(sport)

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                f"{ODDS_API_BASE}/sports/{sport}/odds",
                params={
                    "apiKey": ODDS_API_KEY,
                    "regions": "us",
                    "markets": "spreads,h2h,totals",
                    "oddsFormat": "american",
                    "dateFormat": "iso",
                },
            )
            resp.raise_for_status()
            remaining = resp.headers.get("x-requests-remaining", "?")
            logger.info(f"Odds API [{sport}] — requests remaining: {remaining}")
            return resp.json()
        except httpx.HTTPError as exc:
            logger.error(f"Odds API error ({sport}): {exc}")
            return _mock_odds(sport)


# ─── ESPN (live scores / game status) ─────────────────────────────────────────

async def fetch_espn_scoreboard(sport_key: str) -> Dict:
    path = ESPN_SPORT_MAP.get(sport_key)
    if not path:
        return {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{ESPN_BASE}/{path}/scoreboard")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            logger.error(f"ESPN error ({sport_key}): {exc}")
            return {}


# ─── Normalization ─────────────────────────────────────────────────────────────

def parse_game(raw: Dict, sport: str) -> Dict:
    """Normalize one Odds-API game object into a flat dict our DB understands."""
    game: Dict[str, Any] = {
        "id":          raw.get("id"),
        "sport":       sport,
        "league":      SUPPORTED_SPORTS.get(sport, {}).get("name", sport),
        "home_team":   raw.get("home_team"),
        "away_team":   raw.get("away_team"),
        "game_time":   raw.get("commence_time"),
        "home_spread": None, "away_spread": None,
        "home_spread_odds": None, "away_spread_odds": None,
        "home_moneyline": None, "away_moneyline": None,
        "total": None, "over_odds": None, "under_odds": None,
    }

    bookmakers = raw.get("bookmakers", [])
    book = next(
        (b for p in PREFERRED_BOOKS for b in bookmakers if b.get("key") == p),
        bookmakers[0] if bookmakers else None,
    )
    if not book:
        return game

    for market in book.get("markets", []):
        key = market.get("key")
        outcomes = market.get("outcomes", [])

        if key == "spreads":
            for o in outcomes:
                if o["name"] == game["home_team"]:
                    game["home_spread"] = o.get("point")
                    game["home_spread_odds"] = o.get("price")
                else:
                    game["away_spread"] = o.get("point")
                    game["away_spread_odds"] = o.get("price")

        elif key == "h2h":
            for o in outcomes:
                if o["name"] == game["home_team"]:
                    game["home_moneyline"] = o.get("price")
                else:
                    game["away_moneyline"] = o.get("price")

        elif key == "totals":
            for o in outcomes:
                if o["name"] == "Over":
                    game["total"] = o.get("point")
                    game["over_odds"] = o.get("price")
                elif o["name"] == "Under":
                    game["under_odds"] = o.get("price")

    return game


# ─── Aggregate fetch ──────────────────────────────────────────────────────────

async def fetch_all_upcoming_games() -> List[Dict]:
    """Fetch + parse games across every supported sport concurrently."""
    async def _fetch(sport_key: str) -> List[Dict]:
        raw_list = await fetch_odds(sport_key)
        return [g for g in (parse_game(r, sport_key) for r in raw_list) if g.get("id")]

    results = await asyncio.gather(*(_fetch(s) for s in SUPPORTED_SPORTS), return_exceptions=True)
    games: List[Dict] = []
    for r in results:
        if isinstance(r, list):
            games.extend(r)
    return games


# ─── Mock data (no API key) ────────────────────────────────────────────────────

_MOCK_TEAMS: Dict[str, List[tuple]] = {
    "americanfootball_nfl": [
        ("Kansas City Chiefs",  "Buffalo Bills"),
        ("San Francisco 49ers", "Philadelphia Eagles"),
        ("Dallas Cowboys",      "New York Giants"),
        ("Baltimore Ravens",    "Cincinnati Bengals"),
        ("Miami Dolphins",      "New England Patriots"),
        ("Los Angeles Rams",    "Seattle Seahawks"),
    ],
    "basketball_nba": [
        ("Boston Celtics",      "Miami Heat"),
        ("Golden State Warriors","Los Angeles Lakers"),
        ("Milwaukee Bucks",     "Chicago Bulls"),
        ("Phoenix Suns",        "Denver Nuggets"),
        ("Memphis Grizzlies",   "New Orleans Pelicans"),
        ("Brooklyn Nets",       "Philadelphia 76ers"),
    ],
    "baseball_mlb": [
        ("New York Yankees",    "Boston Red Sox"),
        ("Los Angeles Dodgers", "San Francisco Giants"),
        ("Atlanta Braves",      "New York Mets"),
        ("Houston Astros",      "Texas Rangers"),
    ],
    "icehockey_nhl": [
        ("Colorado Avalanche",  "Vegas Golden Knights"),
        ("Toronto Maple Leafs", "Montreal Canadiens"),
        ("Tampa Bay Lightning", "Florida Panthers"),
        ("Boston Bruins",       "New York Rangers"),
    ],
    "basketball_ncaab": [
        ("Duke Blue Devils",    "North Carolina Tar Heels"),
        ("Kansas Jayhawks",     "Kentucky Wildcats"),
        ("Gonzaga Bulldogs",    "Arizona Wildcats"),
    ],
    "americanfootball_ncaaf": [
        ("Alabama Crimson Tide","Georgia Bulldogs"),
        ("Ohio State Buckeyes", "Michigan Wolverines"),
        ("Clemson Tigers",      "Florida State Seminoles"),
    ],
    "soccer_usa_mls": [
        ("LA Galaxy",           "LAFC"),
        ("Atlanta United",      "Inter Miami CF"),
    ],
}

_TOTAL_RANGES = {
    "americanfootball_nfl":   (41.0, 55.0),
    "americanfootball_ncaaf": (44.0, 65.0),
    "basketball_nba":         (210.0, 240.0),
    "basketball_ncaab":       (130.0, 155.0),
    "baseball_mlb":           (7.0,   10.0),
    "icehockey_nhl":          (5.5,   7.0),
    "soccer_usa_mls":         (2.5,   3.5),
}


def _mock_odds(sport: str) -> List[Dict]:
    rng = random.Random(sport + datetime.now(timezone.utc).strftime("%Y%m%d"))
    teams = _MOCK_TEAMS.get(sport, [("Home Team", "Away Team")])
    lo, hi = _TOTAL_RANGES.get(sport, (7.0, 10.0))

    games = []
    for i, (home, away) in enumerate(teams):
        spread_choices = [-7, -6.5, -6, -5.5, -5, -4.5, -4, -3.5, -3, -2.5, -2, -1.5, -1, -0.5]
        spread = rng.choice(spread_choices)
        total  = round(rng.uniform(lo, hi) * 2) / 2  # round to nearest 0.5
        hours  = rng.randint(4, 72)
        game_time = datetime.now(timezone.utc) + timedelta(hours=hours)

        juice_choices = [-108, -110, -112, -115]
        games.append({
            "id": f"mock_{sport}_{i}_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            "sport_key": sport,
            "home_team": home,
            "away_team": away,
            "commence_time": game_time.isoformat(),
            "bookmakers": [{
                "key": "draftkings",
                "title": "DraftKings",
                "markets": [
                    {
                        "key": "spreads",
                        "outcomes": [
                            {"name": home, "price": rng.choice(juice_choices), "point": spread},
                            {"name": away, "price": rng.choice(juice_choices), "point": -spread},
                        ],
                    },
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": home, "price": -130 if spread <= -3 else (-115 if spread < 0 else +105)},
                            {"name": away, "price": +110  if spread <= -3 else (+100 if spread < 0 else -125)},
                        ],
                    },
                    {
                        "key": "totals",
                        "outcomes": [
                            {"name": "Over",  "price": rng.choice(juice_choices), "point": total},
                            {"name": "Under", "price": rng.choice(juice_choices), "point": total},
                        ],
                    },
                ],
            }],
        })
    return games
