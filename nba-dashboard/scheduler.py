import logging
from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from database import get_connection, init_db, insert_games, insert_player_stats, insert_standings, purge_old_data
from nba_service import fetch_games, fetch_standings

logger = logging.getLogger(__name__)


def daily_collect(db_path: str = "nba.db") -> dict:
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    logger.info("Collecting NBA data for %s", yesterday)

    conn = get_connection(db_path)
    init_db(conn)

    try:
        games, players = fetch_games(yesterday)
        insert_games(conn, games)
        insert_player_stats(conn, players)

        standings = fetch_standings(yesterday)
        insert_standings(conn, standings)

        purge_old_data(conn)

        logger.info("Collected %d games for %s", len(games), yesterday)
        return {"status": "ok", "games_fetched": len(games), "date": yesterday}
    except Exception:
        logger.exception("Failed to collect NBA data")
        return {"status": "error", "games_fetched": 0, "date": yesterday}
    finally:
        conn.close()


def create_scheduler(db_path: str = "nba.db") -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        daily_collect,
        trigger=CronTrigger(hour=8, minute=0),
        kwargs={"db_path": db_path},
        id="daily_nba_collect",
        replace_existing=True,
    )
    return scheduler
