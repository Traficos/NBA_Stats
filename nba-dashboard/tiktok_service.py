"""Service pour recuperer les derniers Reels TikTok via RSSHub."""

import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

logger = logging.getLogger(__name__)

DEFAULT_RSS_URL = "http://localhost:1200/tiktok/user/@beyond_the_hoop"
RSS_URL = os.getenv("TIKTOK_RSS_URL", DEFAULT_RSS_URL)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; nba-dashboard/1.0)"}

CACHE_TTL = 3600
_cache = {"videos": [], "fetched_at": 0}


def _extract_video_id(link: str) -> str:
    """Extrait l'ID numerique d'un lien TikTok (segment apres /video/)."""
    match = re.search(r"/video/(\d+)", link or "")
    return match.group(1) if match else ""


def _extract_thumbnail(description: str) -> str:
    """Extrait l'URL d'une <img> embedee dans la description HTML du flux."""
    match = re.search(r'<img\s+[^>]*src="([^"]+)"', description or "")
    return match.group(1) if match else ""


def _format_published(pub_date: str) -> str:
    """Convertit une date RFC 822 (format flux RSS) en ISO 8601."""
    if not pub_date:
        return ""
    try:
        dt = parsedate_to_datetime(pub_date)
        return dt.isoformat()
    except (TypeError, ValueError):
        return ""


def fetch_latest_tiktoks(max_results: int = 6) -> list[dict]:
    """Recupere les derniers Reels TikTok via RSSHub. Cache memoire 1h."""
    now = time.time()
    if _cache["videos"] and (now - _cache["fetched_at"]) < CACHE_TTL:
        return _cache["videos"][:max_results]

    try:
        resp = requests.get(RSS_URL, headers=HEADERS, timeout=10)
    except requests.RequestException as e:
        logger.warning("Erreur reseau RSSHub TikTok: %s", e)
        return []

    if resp.status_code != 200:
        logger.warning("RSSHub TikTok status %s", resp.status_code)
        return []

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        logger.warning("XML invalide RSSHub TikTok: %s", e)
        return []

    videos = []
    for item in root.findall("./channel/item"):
        link_el = item.find("link")
        title_el = item.find("title")
        pub_el = item.find("pubDate")
        desc_el = item.find("description")

        link = link_el.text if link_el is not None and link_el.text else ""
        video_id = _extract_video_id(link)
        if not video_id:
            continue

        videos.append({
            "video_id": video_id,
            "caption": title_el.text if title_el is not None and title_el.text else "",
            "published": _format_published(pub_el.text) if pub_el is not None and pub_el.text else "",
            "thumbnail": _extract_thumbnail(desc_el.text) if desc_el is not None and desc_el.text else "",
            "url": link,
        })

    _cache["videos"] = videos
    _cache["fetched_at"] = now
    return videos[:max_results]
