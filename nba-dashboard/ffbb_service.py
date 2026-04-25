import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

CLUB_PATH = "/ligues/pdl/comites/0044/clubs/pdl0044217"
FFBB_BASE = f"https://competitions.ffbb.com{CLUB_PATH}"
DEFAULT_TEAM_ID = "200000005259984"
FFBB_TIMEOUT = 15

CACHE_TTL_TEAMS = 86400      # 24h pour la liste des equipes
CACHE_TTL_TEAM = 3600        # 1h pour les details d'une equipe
_teams_cache = {"teams": [], "fetched_at": 0}
_team_cache: dict[str, dict] = {}  # team_id -> {data, fetched_at}


def _decode_next_chunks(html: str) -> str:
    """Concatene et decode les chunks Next.js d'une page."""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.DOTALL)
    decoded = ""
    for chunk in chunks:
        try:
            decoded += chunk.encode("utf-8").decode("unicode_escape")
        except Exception:
            decoded += chunk
    return decoded


def fetch_ffbb_teams() -> list[dict]:
    """Liste toutes les equipes engagees du club. Cache 24h."""
    now = time.time()
    if _teams_cache["teams"] and (now - _teams_cache["fetched_at"]) < CACHE_TTL_TEAMS:
        return _teams_cache["teams"]

    try:
        resp = requests.get(FFBB_BASE, timeout=FFBB_TIMEOUT)
        decoded = _decode_next_chunks(resp.text)
    except requests.RequestException:
        logger.warning("Erreur reseau FFBB liste equipes")
        return []

    pattern = re.compile(
        r'\{"id":"(\d{15})","numeroEquipe":"([^"]*)","categorie":"([^"]*)",'
        r'"competition":"([^"]*)","organisateur":"[^"]*","competitionId":"[^"]*","label":"([^"]+)"'
    )

    seen = {}
    for tid, numero, categorie, competition, label in pattern.findall(decoded):
        if tid in seen:
            continue
        seen[tid] = {
            "team_id": tid,
            "numero": numero,
            "categorie": categorie,
            "competition": competition,
            "label": label,
        }

    teams = list(seen.values())
    teams.sort(key=lambda t: (t["categorie"], t["label"], t["numero"]))

    _teams_cache["teams"] = teams
    _teams_cache["fetched_at"] = now
    return teams


def _scrape_standings(team_id: str) -> list[dict]:
    url = f"{FFBB_BASE}/equipes/{team_id}/classement"
    resp = requests.get(url, timeout=FFBB_TIMEOUT)
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    table = soup.find("table")
    if not table:
        return []

    standings = []
    for row in table.find_all("tr"):
        tds = row.find_all("td")
        if len(tds) < 11:
            continue

        rank_text = tds[0].get_text(strip=True)
        if not rank_text.isdigit():
            continue

        team_name = tds[1].get_text(strip=True)
        pts = int(tds[2].get_text(strip=True))

        rencontres_divs = tds[3].find_all("div")
        if len(rencontres_divs) >= 5:
            played = int(rencontres_divs[1].get_text(strip=True))
            wins = int(rencontres_divs[2].get_text(strip=True))
            losses = int(rencontres_divs[3].get_text(strip=True))
        else:
            played = wins = losses = 0

        points_divs = tds[10].find_all("div")
        if len(points_divs) >= 4:
            bp = int(points_divs[1].get_text(strip=True))
            bc = int(points_divs[2].get_text(strip=True))
            diff = points_divs[3].get_text(strip=True)
        else:
            bp = bc = 0
            diff = "0"

        standings.append({
            "rank": int(rank_text),
            "team": team_name,
            "pts": pts,
            "played": played,
            "wins": wins,
            "losses": losses,
            "bp": bp,
            "bc": bc,
            "diff": diff,
            "is_my_team": "UNION DU SILLON" in team_name.upper(),
        })

    return standings


def _scrape_calendar(team_id: str) -> list[dict]:
    url = f"{FFBB_BASE}/equipes/{team_id}"
    resp = requests.get(url, timeout=FFBB_TIMEOUT)

    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', resp.text, re.DOTALL)

    matches = []
    for chunk in chunks:
        if "date_rencontre" not in chunk:
            continue

        try:
            decoded = chunk.encode("utf-8").decode("unicode_escape")
        except Exception:
            decoded = chunk

        match_pattern = re.compile(
            r'\{"id":"(\d+)","date_rencontre":"([^"]+)","joue":(true|false),'
            r'"numero":"[^"]*","numeroJournee":"(\d+)",'
            r'"resultatEquipe1":"?(\w*)"?,"resultatEquipe2":"?(\w*)"?'
        )

        match_blocks = re.split(r'(?=\{"id":"\d+","date_rencontre")', decoded)

        for block in match_blocks:
            m = match_pattern.search(block)
            if not m:
                continue

            match_id, date_str, joue, journee, score1, score2 = m.groups()

            team1_match = re.search(
                r'"idEngagementEquipe1":\{"id":"(\d+)","numeroEquipe":"[^"]*","nom":"([^"]+)"',
                block
            )
            team2_match = re.search(
                r'"idEngagementEquipe2":\{"id":"(\d+)","numeroEquipe":"[^"]*","nom":"([^"]+)"',
                block
            )

            if not team1_match or not team2_match:
                continue

            team1_id = team1_match.group(1)
            team1_name = team1_match.group(2)
            team2_id = team2_match.group(1)
            team2_name = team2_match.group(2)

            is_home = team1_id == team_id

            matches.append({
                "journee": int(journee),
                "date": date_str[:10],
                "played": joue == "true",
                "home_team": team1_name,
                "away_team": team2_name,
                "home_score": int(score1) if score1 and score1 != "null" else None,
                "away_score": int(score2) if score2 and score2 != "null" else None,
                "is_home": is_home,
            })

        if matches:
            break

    matches.sort(key=lambda m: m["journee"])
    return matches


def fetch_ffbb_team_data(team_id: str) -> dict:
    """Detail d'une equipe (classement + calendrier). Cache 1h par team."""
    now = time.time()
    cached = _team_cache.get(team_id)
    if cached and (now - cached["fetched_at"]) < CACHE_TTL_TEAM:
        return cached["data"]

    try:
        standings = _scrape_standings(team_id)
        calendar = _scrape_calendar(team_id)
    except Exception:
        logger.exception("Erreur scraping equipe %s", team_id)
        return {"team_id": team_id, "standings": [], "calendar": []}

    # Trouver les infos label/categorie depuis la liste cachee
    teams = fetch_ffbb_teams()
    info = next((t for t in teams if t["team_id"] == team_id), None)

    data = {
        "team_id": team_id,
        "label": info["label"] if info else "",
        "categorie": info["categorie"] if info else "",
        "competition": info["competition"] if info else "",
        "standings": standings,
        "calendar": calendar,
    }

    _team_cache[team_id] = {"data": data, "fetched_at": now}
    return data


def fetch_ffbb_data() -> dict:
    """Compat retour : detail de l'equipe par defaut (DMU13)."""
    return fetch_ffbb_team_data(DEFAULT_TEAM_ID)
