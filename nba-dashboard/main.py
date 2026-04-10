import logging
from contextlib import asynccontextmanager
from datetime import date as date_cls, timedelta

from fastapi import FastAPI, Depends, Query
from fastapi.staticfiles import StaticFiles

from database import get_connection, init_db, get_games_by_date, get_standings_by_date, get_latest_standings_date
from ffbb_service import fetch_ffbb_data
from scheduler import create_scheduler, daily_collect
from youtube_service import fetch_latest_videos

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "nba.db"


def get_db():
    conn = get_connection(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection(DB_PATH)
    init_db(conn)
    conn.close()

    scheduler = create_scheduler(DB_PATH)
    scheduler.start()
    logger.info("Scheduler started — daily collection at 08:00")

    yield

    scheduler.shutdown()
    logger.info("Scheduler stopped")


app = FastAPI(title="NBA Daily Dashboard", lifespan=lifespan)


@app.get("/api/games")
def api_games(
    date: str = Query(default=None, description="Date au format YYYY-MM-DD"),
    db=Depends(get_db),
):
    if date is None:
        date = (date_cls.today() - timedelta(days=1)).isoformat()
    games = get_games_by_date(db, date)
    return {
        "date": date,
        "games": [
            {
                "game_id": g["game_id"],
                "home_team": g["home_team"],
                "away_team": g["away_team"],
                "home_score": g["home_score"],
                "away_score": g["away_score"],
                "quarters": {
                    "home": [g["home_q1"], g["home_q2"], g["home_q3"], g["home_q4"]],
                    "away": [g["away_q1"], g["away_q2"], g["away_q3"], g["away_q4"]],
                },
                "arena": g["arena"],
                "top_players": g["top_players"],
            }
            for g in games
        ],
    }


@app.get("/api/standings")
def api_standings(
    date: str = Query(default=None, description="Date au format YYYY-MM-DD"),
    db=Depends(get_db),
):
    if date is None:
        date = get_latest_standings_date(db)
        if date is None:
            return {"date": None, "east": [], "west": []}
    standings = get_standings_by_date(db, date)
    return {
        "date": date,
        "east": [
            {"rank": s["rank"], "team": s["team"], "team_abbr": s["team_abbr"],
             "wins": s["wins"], "losses": s["losses"], "win_pct": s["win_pct"],
             "playoff_status": s["playoff_status"]}
            for s in standings["east"]
        ],
        "west": [
            {"rank": s["rank"], "team": s["team"], "team_abbr": s["team_abbr"],
             "wins": s["wins"], "losses": s["losses"], "win_pct": s["win_pct"],
             "playoff_status": s["playoff_status"]}
            for s in standings["west"]
        ],
    }


@app.post("/api/refresh")
def api_refresh():
    result = daily_collect(DB_PATH)
    return result


@app.get("/api/ffbb")
def api_ffbb():
    return fetch_ffbb_data()


@app.get("/api/videos")
def api_videos():
    videos = fetch_latest_videos()
    return {"videos": videos}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
