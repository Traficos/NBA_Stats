import logging
from datetime import date

import requests

logger = logging.getLogger(__name__)

NBA_HEADERS = {
    "Referer": "https://www.nba.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}
TIMEOUT = 20


def _nba_get(url: str, params: dict | None = None) -> dict:
    resp = requests.get(url, headers=NBA_HEADERS, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_games(game_date: str) -> tuple[list[dict], list[dict]]:
    """Fetch games and top players for a given date via ScoreboardV3."""
    data = _nba_get(
        "https://stats.nba.com/stats/scoreboardv3",
        params={"GameDate": game_date, "LeagueID": "00"},
    )
    sb_games = data.get("scoreboard", {}).get("games", [])

    games = []
    all_players = []

    for g in sb_games:
        # Only include finished games (gameStatus == 3)
        if g.get("gameStatus") != 3:
            continue

        home = g["homeTeam"]
        away = g["awayTeam"]
        gid = g["gameId"]

        home_periods = home.get("periods", [])
        away_periods = away.get("periods", [])

        game = {
            "game_id": gid,
            "game_date": game_date,
            "home_team": home["teamTricode"],
            "away_team": away["teamTricode"],
            "home_score": home["score"],
            "away_score": away["score"],
            "home_q1": home_periods[0]["score"] if len(home_periods) > 0 else 0,
            "home_q2": home_periods[1]["score"] if len(home_periods) > 1 else 0,
            "home_q3": home_periods[2]["score"] if len(home_periods) > 2 else 0,
            "home_q4": home_periods[3]["score"] if len(home_periods) > 3 else 0,
            "away_q1": away_periods[0]["score"] if len(away_periods) > 0 else 0,
            "away_q2": away_periods[1]["score"] if len(away_periods) > 1 else 0,
            "away_q3": away_periods[2]["score"] if len(away_periods) > 2 else 0,
            "away_q4": away_periods[3]["score"] if len(away_periods) > 3 else 0,
            "arena": g.get("arenaName", ""),
        }
        games.append(game)

        # Fetch box score for top 3 players via CDN (faster & more reliable)
        try:
            box_data = _nba_get(
                f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{gid}.json",
            )
            game_box = box_data.get("game", {})
            home_tri = home["teamTricode"]
            away_tri = away["teamTricode"]

            home_players = [(p, home_tri) for p in game_box.get("homeTeam", {}).get("players", [])]
            away_players = [(p, away_tri) for p in game_box.get("awayTeam", {}).get("players", [])]
            all_box = home_players + away_players

            # Sort by points descending, take top 3
            scored = [(p, t) for p, t in all_box if p.get("statistics", {}).get("points", 0) > 0]
            scored.sort(key=lambda x: x[0].get("statistics", {}).get("points", 0), reverse=True)

            for p, team_tri in scored[:3]:
                stats = p.get("statistics", {})
                all_players.append({
                    "game_id": gid,
                    "player_name": f"{p.get('firstName', '')} {p.get('familyName', '')}",
                    "team": team_tri,
                    "points": stats.get("points", 0),
                    "rebounds": stats.get("reboundsTotal", 0),
                    "assists": stats.get("assists", 0),
                })
        except Exception:
            logger.warning("Could not fetch box score for game %s", gid)

    return games, all_players


def _determine_playoff_status(rank: int) -> str:
    if rank <= 6:
        return "playoff"
    elif rank <= 10:
        return "playin"
    else:
        return "out"


def fetch_standings(standings_date: str) -> list[dict]:
    """Fetch current league standings via LeagueStandingsV3."""
    d = date.fromisoformat(standings_date)
    if d.month >= 10:
        season = f"{d.year}-{str(d.year + 1)[2:]}"
    else:
        season = f"{d.year - 1}-{str(d.year)[2:]}"

    data = _nba_get(
        "https://stats.nba.com/stats/leaguestandingsv3",
        params={"LeagueID": "00", "Season": season, "SeasonType": "Regular Season"},
    )

    result_sets = data.get("resultSets", [])
    if not result_sets:
        return []

    headers = result_sets[0]["headers"]
    rows = result_sets[0]["rowSet"]

    # Build column index map
    idx = {h: i for i, h in enumerate(headers)}

    standings = []
    for row in rows:
        conf = row[idx["Conference"]]
        rank = int(row[idx["PlayoffRank"]])
        standings.append({
            "date": standings_date,
            "conference": conf,
            "team": f"{row[idx['TeamCity']]} {row[idx['TeamName']]}",
            "team_abbr": str(row[idx["TeamSlug"]]).upper()[:3],
            "rank": rank,
            "wins": int(row[idx["WINS"]]),
            "losses": int(row[idx["LOSSES"]]),
            "win_pct": round(float(row[idx["WinPCT"]]), 3),
            "playoff_status": _determine_playoff_status(rank),
        })

    return standings
