import sqlite3
from datetime import date, datetime, timedelta

import pytest

from database import (
    get_connection,
    init_db,
    insert_games,
    insert_player_stats,
    insert_standings,
    get_games_by_date,
    get_standings_by_date,
    purge_old_data,
)


@pytest.fixture
def db():
    conn = get_connection(":memory:")
    init_db(conn)
    yield conn
    conn.close()


class TestSchema:
    def test_games_table_exists(self, db):
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games'")
        assert cursor.fetchone() is not None

    def test_player_stats_table_exists(self, db):
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='player_stats'")
        assert cursor.fetchone() is not None

    def test_standings_table_exists(self, db):
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='standings'")
        assert cursor.fetchone() is not None


SAMPLE_GAME = {
    "game_id": "0022500100", "game_date": "2026-04-08",
    "home_team": "LAL", "away_team": "BOS",
    "home_score": 118, "away_score": 105,
    "home_q1": 32, "home_q2": 30, "home_q3": 28, "home_q4": 28,
    "away_q1": 28, "away_q2": 25, "away_q3": 30, "away_q4": 22,
    "arena": "Crypto.com Arena",
}

SAMPLE_PLAYERS = [
    {"game_id": "0022500100", "player_name": "LeBron James", "team": "LAL", "points": 35, "rebounds": 10, "assists": 8},
    {"game_id": "0022500100", "player_name": "Anthony Davis", "team": "LAL", "points": 28, "rebounds": 12, "assists": 3},
    {"game_id": "0022500100", "player_name": "Jayson Tatum", "team": "BOS", "points": 25, "rebounds": 7, "assists": 5},
]

SAMPLE_STANDING = {
    "date": "2026-04-08", "conference": "East", "team": "Boston Celtics",
    "team_abbr": "BOS", "rank": 1, "wins": 58, "losses": 20,
    "win_pct": 0.744, "playoff_status": "playoff",
}


class TestInsertAndQuery:
    def test_insert_and_get_games(self, db):
        insert_games(db, [SAMPLE_GAME])
        games = get_games_by_date(db, "2026-04-08")
        assert len(games) == 1
        assert games[0]["home_team"] == "LAL"
        assert games[0]["home_score"] == 118

    def test_insert_duplicate_game_is_ignored(self, db):
        insert_games(db, [SAMPLE_GAME])
        insert_games(db, [SAMPLE_GAME])
        games = get_games_by_date(db, "2026-04-08")
        assert len(games) == 1

    def test_insert_and_get_player_stats(self, db):
        insert_games(db, [SAMPLE_GAME])
        insert_player_stats(db, SAMPLE_PLAYERS)
        games = get_games_by_date(db, "2026-04-08")
        assert len(games[0]["top_players"]) == 3
        assert games[0]["top_players"][0]["player_name"] == "LeBron James"

    def test_insert_and_get_standings(self, db):
        insert_standings(db, [SAMPLE_STANDING])
        standings = get_standings_by_date(db, "2026-04-08")
        assert len(standings["east"]) == 1
        assert standings["east"][0]["team"] == "Boston Celtics"
        assert standings["west"] == []

    def test_get_games_no_results(self, db):
        games = get_games_by_date(db, "2099-01-01")
        assert games == []

    def test_get_standings_no_results(self, db):
        standings = get_standings_by_date(db, "2099-01-01")
        assert standings["east"] == []
        assert standings["west"] == []


class TestPurge:
    def test_purge_old_data(self, db):
        old_game = {**SAMPLE_GAME, "game_id": "old001", "game_date": "2026-02-01"}
        insert_games(db, [old_game, SAMPLE_GAME])
        old_standing = {**SAMPLE_STANDING, "date": "2026-02-01"}
        insert_standings(db, [old_standing, SAMPLE_STANDING])
        purge_old_data(db, days=30)
        games = get_games_by_date(db, "2026-02-01")
        assert games == []
        recent = get_games_by_date(db, "2026-04-08")
        assert len(recent) == 1
        standings = get_standings_by_date(db, "2026-02-01")
        assert standings["east"] == []
