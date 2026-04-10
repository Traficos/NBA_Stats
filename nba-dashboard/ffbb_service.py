import logging
import re

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

FFBB_TEAM_ID = "200000005259984"
FFBB_BASE = "https://competitions.ffbb.com/ligues/pdl/comites/0044/clubs/pdl0044217/equipes"
FFBB_TIMEOUT = 15


def fetch_ffbb_standings() -> list[dict]:
    """Scrape le classement depuis la page FFBB."""
    url = f"{FFBB_BASE}/{FFBB_TEAM_ID}/classement"
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

        # Rencontres: sub-divs contain J, G, P, N
        rencontres_divs = tds[3].find_all("div")
        if len(rencontres_divs) >= 5:
            played = int(rencontres_divs[1].get_text(strip=True))
            wins = int(rencontres_divs[2].get_text(strip=True))
            losses = int(rencontres_divs[3].get_text(strip=True))
        else:
            played = wins = losses = 0

        # Points: sub-divs contain BP, BC, Diff
        points_divs = tds[10].find_all("div")
        if len(points_divs) >= 4:
            bp = int(points_divs[1].get_text(strip=True))
            bc = int(points_divs[2].get_text(strip=True))
            diff = points_divs[3].get_text(strip=True)
        else:
            bp = bc = 0
            diff = "0"

        is_my_team = "UNION DU SILLON" in team_name.upper()

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
            "is_my_team": is_my_team,
        })

    return standings


def fetch_ffbb_calendar() -> list[dict]:
    """Scrape le calendrier depuis le RSC payload de la page equipe FFBB."""
    url = f"{FFBB_BASE}/{FFBB_TEAM_ID}"
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

        # Extract match blocks with surrounding team info
        pattern = (
            r'"idEngagementEquipe1":\{"id":"(\d+)","numeroEquipe":"[^"]*","nom":"([^"]+)"'
            r'.*?'
            r'"idEngagementEquipe2":\{"id":"(\d+)","numeroEquipe":"[^"]*","nom":"([^"]+)"'
            r'.*?'
            r'\{"id":"(\d+)","date_rencontre":"([^"]+)","joue":(true|false),'
            r'"numero":"[^"]*","numeroJournee":"(\d+)",'
            r'"resultatEquipe1":"?([^",]*)"?,"resultatEquipe2":"?([^",]*)"?'
        )

        # Simpler approach: find all match objects individually
        match_pattern = re.compile(
            r'\{"id":"(\d+)","date_rencontre":"([^"]+)","joue":(true|false),'
            r'"numero":"[^"]*","numeroJournee":"(\d+)",'
            r'"resultatEquipe1":"?(\w*)"?,"resultatEquipe2":"?(\w*)"?'
        )

        # Find team pairs for each match (equipe1 appears before match data, equipe2 after or vice versa)
        # Better approach: split around each match and grab team names
        match_blocks = re.split(r'(?=\{"id":"\d+","date_rencontre")', decoded)

        for block in match_blocks:
            m = match_pattern.search(block)
            if not m:
                continue

            match_id, date_str, joue, journee, score1, score2 = m.groups()

            # Find team names in surrounding context (look backwards for equipe1, forward for equipe2)
            # Team 1 is in the text before the match object
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

            is_home = team1_id == FFBB_TEAM_ID

            match_data = {
                "journee": int(journee),
                "date": date_str[:10],
                "played": joue == "true",
                "home_team": team1_name,
                "away_team": team2_name,
                "home_score": int(score1) if score1 and score1 != "null" else None,
                "away_score": int(score2) if score2 and score2 != "null" else None,
                "is_home": is_home,
            }
            matches.append(match_data)

        if matches:
            break

    matches.sort(key=lambda m: m["journee"])
    return matches


def fetch_ffbb_data() -> dict:
    """Recupere toutes les donnees FFBB."""
    try:
        standings = fetch_ffbb_standings()
        calendar = fetch_ffbb_calendar()
        return {
            "team": "Union Du Sillon Basket Club",
            "category": "DMU13 — Phase 2 Elite Poule B",
            "standings": standings,
            "calendar": calendar,
        }
    except Exception:
        logger.exception("Erreur lors de la recuperation des donnees FFBB")
        return {"team": "Union Du Sillon Basket Club", "category": "DMU13", "standings": [], "calendar": []}
