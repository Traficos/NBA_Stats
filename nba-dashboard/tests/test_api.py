from unittest.mock import patch
import pytest
from httpx import ASGITransport
from starlette.testclient import TestClient

from main import app, get_db
from database import get_connection, init_db, insert_games, insert_player_stats, insert_standings


@pytest.fixture
def db():
    import sqlite3
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app, raise_server_exceptions=True)


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
]

SAMPLE_STANDING = {
    "date": "2026-04-08", "conference": "East", "team": "Boston Celtics",
    "team_abbr": "BOS", "rank": 1, "wins": 58, "losses": 20,
    "win_pct": 0.744, "playoff_status": "playoff",
}


class TestGamesRoute:
    def test_get_games_with_date(self, client, db):
        insert_games(db, [SAMPLE_GAME])
        insert_player_stats(db, SAMPLE_PLAYERS)
        resp = client.get("/api/games", params={"date": "2026-04-08"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["date"] == "2026-04-08"
        assert len(data["games"]) == 1
        assert data["games"][0]["home_team"] == "LAL"
        assert len(data["games"][0]["top_players"]) == 1

    def test_get_games_empty(self, client, db):
        resp = client.get("/api/games", params={"date": "2099-01-01"})
        assert resp.status_code == 200
        assert resp.json()["games"] == []


class TestStandingsRoute:
    def test_get_standings_with_date(self, client, db):
        insert_standings(db, [SAMPLE_STANDING])
        resp = client.get("/api/standings", params={"date": "2026-04-08"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["east"]) == 1
        assert data["west"] == []

    def test_get_standings_latest(self, client, db):
        insert_standings(db, [SAMPLE_STANDING])
        resp = client.get("/api/standings")
        assert resp.status_code == 200
        assert len(resp.json()["east"]) == 1


class TestRefreshRoute:
    @patch("main.daily_collect")
    def test_refresh_calls_collect(self, mock_collect, client):
        mock_collect.return_value = {"status": "ok", "games_fetched": 5, "date": "2026-04-08"}
        resp = client.post("/api/refresh")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        mock_collect.assert_called_once()


class TestTikTokRoute:
    @patch("main.fetch_latest_tiktoks")
    def test_get_tiktok_renvoie_liste(self, mock_fetch, client):
        mock_fetch.return_value = [
            {
                "video_id": "7395123456789012345",
                "caption": "Test caption",
                "published": "2026-04-23T18:42:11+00:00",
                "thumbnail": "https://p16-sign.tiktokcdn.com/img.jpg",
                "url": "https://www.tiktok.com/@beyond_the_hoop/video/7395123456789012345",
            }
        ]

        resp = client.get("/api/tiktok")

        assert resp.status_code == 200
        data = resp.json()
        assert "videos" in data
        assert len(data["videos"]) == 1
        assert data["videos"][0]["video_id"] == "7395123456789012345"

    @patch("main.fetch_latest_tiktoks")
    def test_get_tiktok_liste_vide(self, mock_fetch, client):
        mock_fetch.return_value = []
        resp = client.get("/api/tiktok")
        assert resp.status_code == 200
        assert resp.json() == {"videos": []}
