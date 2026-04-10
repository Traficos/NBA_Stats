import sqlite3
from datetime import date, timedelta


def get_connection(db_path: str = "nba.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _migrate_player_stats_unique(conn: sqlite3.Connection) -> None:
    """Ajoute la contrainte UNIQUE(game_id, player_name) et supprime les doublons existants."""
    # Verifie si la contrainte existe deja en regardant le schema
    schema = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='player_stats'"
    ).fetchone()
    if schema and "UNIQUE(game_id, player_name)" in schema[0]:
        return
    if not schema:
        return  # La table n'existe pas encore, sera creee avec la contrainte

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS player_stats_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT NOT NULL REFERENCES games(game_id),
            player_name TEXT NOT NULL,
            team TEXT NOT NULL,
            points INTEGER NOT NULL,
            rebounds INTEGER NOT NULL,
            assists INTEGER NOT NULL,
            UNIQUE(game_id, player_name)
        );
        INSERT OR IGNORE INTO player_stats_new (game_id, player_name, team, points, rebounds, assists)
            SELECT game_id, player_name, team, points, rebounds, assists FROM player_stats;
        DROP TABLE player_stats;
        ALTER TABLE player_stats_new RENAME TO player_stats;
        CREATE INDEX IF NOT EXISTS idx_player_stats_game ON player_stats(game_id);
    """)


def init_db(conn: sqlite3.Connection) -> None:
    _migrate_player_stats_unique(conn)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT UNIQUE NOT NULL,
            game_date TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_score INTEGER NOT NULL,
            away_score INTEGER NOT NULL,
            home_q1 INTEGER, home_q2 INTEGER, home_q3 INTEGER, home_q4 INTEGER,
            away_q1 INTEGER, away_q2 INTEGER, away_q3 INTEGER, away_q4 INTEGER,
            arena TEXT,
            fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS player_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT NOT NULL REFERENCES games(game_id),
            player_name TEXT NOT NULL,
            team TEXT NOT NULL,
            points INTEGER NOT NULL,
            rebounds INTEGER NOT NULL,
            assists INTEGER NOT NULL,
            UNIQUE(game_id, player_name)
        );
        CREATE TABLE IF NOT EXISTS standings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            conference TEXT NOT NULL,
            team TEXT NOT NULL,
            team_abbr TEXT NOT NULL,
            rank INTEGER NOT NULL,
            wins INTEGER NOT NULL,
            losses INTEGER NOT NULL,
            win_pct REAL NOT NULL,
            playoff_status TEXT NOT NULL,
            UNIQUE(date, conference, team)
        );
        CREATE INDEX IF NOT EXISTS idx_games_date ON games(game_date);
        CREATE INDEX IF NOT EXISTS idx_player_stats_game ON player_stats(game_id);
        CREATE INDEX IF NOT EXISTS idx_standings_date ON standings(date);
    """)


def insert_games(conn: sqlite3.Connection, games: list[dict]) -> None:
    for g in games:
        conn.execute(
            """INSERT OR IGNORE INTO games
            (game_id, game_date, home_team, away_team, home_score, away_score,
             home_q1, home_q2, home_q3, home_q4,
             away_q1, away_q2, away_q3, away_q4, arena)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (g["game_id"], g["game_date"], g["home_team"], g["away_team"],
             g["home_score"], g["away_score"],
             g["home_q1"], g["home_q2"], g["home_q3"], g["home_q4"],
             g["away_q1"], g["away_q2"], g["away_q3"], g["away_q4"],
             g["arena"]),
        )
    conn.commit()


def insert_player_stats(conn: sqlite3.Connection, players: list[dict]) -> None:
    for p in players:
        conn.execute(
            """INSERT OR IGNORE INTO player_stats
            (game_id, player_name, team, points, rebounds, assists)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (p["game_id"], p["player_name"], p["team"],
             p["points"], p["rebounds"], p["assists"]),
        )
    conn.commit()


def insert_standings(conn: sqlite3.Connection, standings: list[dict]) -> None:
    for s in standings:
        conn.execute(
            """INSERT OR IGNORE INTO standings
            (date, conference, team, team_abbr, rank, wins, losses, win_pct, playoff_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (s["date"], s["conference"], s["team"], s["team_abbr"],
             s["rank"], s["wins"], s["losses"], s["win_pct"], s["playoff_status"]),
        )
    conn.commit()


def get_games_by_date(conn: sqlite3.Connection, game_date: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM games WHERE game_date = ? ORDER BY id", (game_date,)
    ).fetchall()
    games = []
    for row in rows:
        game = dict(row)
        player_rows = conn.execute(
            "SELECT player_name, team, points, rebounds, assists FROM player_stats WHERE game_id = ? ORDER BY points DESC",
            (game["game_id"],),
        ).fetchall()
        game["top_players"] = [dict(p) for p in player_rows]
        games.append(game)
    return games


def get_standings_by_date(conn: sqlite3.Connection, standings_date: str) -> dict:
    east = conn.execute(
        "SELECT * FROM standings WHERE date = ? AND conference = 'East' ORDER BY rank",
        (standings_date,),
    ).fetchall()
    west = conn.execute(
        "SELECT * FROM standings WHERE date = ? AND conference = 'West' ORDER BY rank",
        (standings_date,),
    ).fetchall()
    return {"east": [dict(r) for r in east], "west": [dict(r) for r in west]}


def get_latest_standings_date(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT MAX(date) as max_date FROM standings").fetchone()
    return row["max_date"] if row else None


def purge_old_data(conn: sqlite3.Connection, days: int = 30) -> None:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn.execute("DELETE FROM player_stats WHERE game_id IN (SELECT game_id FROM games WHERE game_date < ?)", (cutoff,))
    conn.execute("DELETE FROM games WHERE game_date < ?", (cutoff,))
    conn.execute("DELETE FROM standings WHERE date < ?", (cutoff,))
    conn.commit()
