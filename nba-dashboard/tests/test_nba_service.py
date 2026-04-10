from unittest.mock import patch

from nba_service import fetch_games, fetch_standings


MOCK_SCOREBOARD = {
    "scoreboard": {
        "games": [
            {
                "gameId": "0022500100",
                "gameStatus": 3,
                "gameStatusText": "Final",
                "arenaName": "Crypto.com Arena",
                "homeTeam": {
                    "teamTricode": "LAL",
                    "score": 118,
                    "periods": [
                        {"period": 1, "score": 32},
                        {"period": 2, "score": 30},
                        {"period": 3, "score": 28},
                        {"period": 4, "score": 28},
                    ],
                },
                "awayTeam": {
                    "teamTricode": "BOS",
                    "score": 105,
                    "periods": [
                        {"period": 1, "score": 28},
                        {"period": 2, "score": 25},
                        {"period": 3, "score": 30},
                        {"period": 4, "score": 22},
                    ],
                },
            }
        ]
    }
}

MOCK_BOXSCORE = {
    "game": {
        "homeTeam": {
            "players": [
                {"firstName": "LeBron", "familyName": "James",
                 "statistics": {"points": 35, "reboundsTotal": 10, "assists": 8}},
                {"firstName": "Anthony", "familyName": "Davis",
                 "statistics": {"points": 28, "reboundsTotal": 12, "assists": 3}},
            ]
        },
        "awayTeam": {
            "players": [
                {"firstName": "Jayson", "familyName": "Tatum",
                 "statistics": {"points": 25, "reboundsTotal": 7, "assists": 5}},
                {"firstName": "Bench", "familyName": "Player",
                 "statistics": {"points": 5, "reboundsTotal": 2, "assists": 1}},
            ]
        },
    }
}

MOCK_STANDINGS = {
    "resultSets": [
        {
            "headers": ["LeagueID", "SeasonID", "TeamID", "TeamCity", "TeamName",
                        "TeamSlug", "Conference", "ConferenceRecord", "PlayoffRank",
                        "ClinchIndicator", "WINS", "LOSSES", "WinPCT"],
            "rowSet": [
                ["00", "22025", 1, "Boston", "Celtics", "celtics", "East", "36-14", 1, "x", 58, 20, 0.744],
                ["00", "22025", 2, "Milwaukee", "Bucks", "bucks", "East", "32-18", 2, "x", 54, 24, 0.692],
                ["00", "22025", 3, "Oklahoma City", "Thunder", "thunder", "West", "38-12", 1, "x", 60, 18, 0.769],
            ],
        }
    ]
}


class TestFetchGames:
    @patch("nba_service._nba_get")
    def test_returns_games_with_players(self, mock_get):
        mock_get.side_effect = [MOCK_SCOREBOARD, MOCK_BOXSCORE]

        games, players = fetch_games("2026-04-08")

        assert len(games) == 1
        assert games[0]["game_id"] == "0022500100"
        assert games[0]["home_team"] == "LAL"
        assert games[0]["home_score"] == 118
        assert games[0]["home_q1"] == 32
        assert games[0]["arena"] == "Crypto.com Arena"

        assert len(players) == 3
        assert players[0]["player_name"] == "LeBron James"
        assert players[0]["points"] == 35

    @patch("nba_service._nba_get")
    def test_no_games_returns_empty(self, mock_get):
        mock_get.return_value = {"scoreboard": {"games": []}}

        games, players = fetch_games("2026-07-15")
        assert games == []
        assert players == []


class TestFetchStandings:
    @patch("nba_service._nba_get")
    def test_returns_standings_by_conference(self, mock_get):
        mock_get.return_value = MOCK_STANDINGS

        standings = fetch_standings("2026-04-08")

        east = [s for s in standings if s["conference"] == "East"]
        west = [s for s in standings if s["conference"] == "West"]
        assert len(east) == 2
        assert len(west) == 1
        assert east[0]["team"] == "Boston Celtics"
        assert east[0]["wins"] == 58
        assert east[0]["playoff_status"] == "playoff"
        assert west[0]["team"] == "Oklahoma City Thunder"
