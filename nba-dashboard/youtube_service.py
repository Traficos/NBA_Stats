"""Service pour recuperer les dernieres videos YouTube de Prime Video Sport FR."""

import logging
import re
import time
import xml.etree.ElementTree as ET
from collections import Counter

import requests

logger = logging.getLogger(__name__)

CHANNEL_HANDLE = "PrimeVideoSportFR"
CHANNEL_URL = f"https://www.youtube.com/@{CHANNEL_HANDLE}"
# Channel ID connu — utilise comme fallback si la resolution dynamique echoue
KNOWN_CHANNEL_ID = "UCAbK-X3uoh2v9ytK4K0J3_Q"
RSS_URL_TEMPLATE = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Cookie pour bypasser la page de consentement EU
COOKIES = {
    "SOCS": "CAISNQgDEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjMwODI5LjA3X3AxGgJmciACGgYIgJnPpwY",
}

# Cache simple en memoire
_cache = {"channel_id": None, "videos": [], "fetched_at": 0}
CACHE_TTL = 3600  # 1 heure


def _resolve_channel_id() -> str:
    """Recupere le channel ID depuis la page YouTube, avec fallback."""
    if _cache["channel_id"]:
        return _cache["channel_id"]

    try:
        resp = requests.get(CHANNEL_URL, headers=HEADERS, cookies=COOKIES, timeout=10)
        resp.raise_for_status()

        # Trouve le channel ID le plus frequent dans le HTML
        uc_matches = re.findall(r'UC[a-zA-Z0-9_-]{22}', resp.text)
        if uc_matches:
            most_common = Counter(uc_matches).most_common(1)[0][0]
            _cache["channel_id"] = most_common
            return most_common
    except Exception as e:
        logger.warning("Impossible de resoudre le channel ID: %s", e)

    _cache["channel_id"] = KNOWN_CHANNEL_ID
    return KNOWN_CHANNEL_ID


def fetch_latest_videos(max_results: int = 6) -> list[dict]:
    """Recupere les dernieres videos de la chaine via le flux RSS."""
    now = time.time()
    if _cache["videos"] and (now - _cache["fetched_at"]) < CACHE_TTL:
        return _cache["videos"][:max_results]

    channel_id = _resolve_channel_id()

    try:
        rss_url = RSS_URL_TEMPLATE.format(channel_id=channel_id)
        resp = requests.get(rss_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "media": "http://search.yahoo.com/mrss/",
            "yt": "http://www.youtube.com/xml/schemas/2015",
        }

        videos = []
        for entry in root.findall("atom:entry", ns):
            video_id = entry.find("yt:videoId", ns)
            title = entry.find("atom:title", ns)
            published = entry.find("atom:published", ns)
            media_group = entry.find("media:group", ns)

            thumbnail_url = ""
            description = ""
            if media_group is not None:
                thumb = media_group.find("media:thumbnail", ns)
                if thumb is not None:
                    thumbnail_url = thumb.get("url", "")
                desc = media_group.find("media:description", ns)
                if desc is not None and desc.text:
                    description = desc.text[:200]

            if video_id is not None and title is not None:
                videos.append({
                    "video_id": video_id.text,
                    "title": title.text,
                    "published": published.text if published is not None else "",
                    "thumbnail": thumbnail_url,
                    "description": description,
                    "url": f"https://www.youtube.com/watch?v={video_id.text}",
                })

        # Ne garder que les résumés de matchs NBA
        videos = [v for v in videos if "sum" in v["title"].lower() and "match" in v["title"].lower()]

        _cache["videos"] = videos
        _cache["fetched_at"] = now
        return videos[:max_results]

    except Exception as e:
        logger.error("Erreur lors de la recuperation des videos: %s", e)
        return []
