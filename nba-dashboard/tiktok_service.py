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
