"""Service pour recuperer les derniers Reels TikTok via RapidAPI."""

import json
import logging
import os
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

DEFAULT_HOST = "tiktok-scraper7.p.rapidapi.com"
DEFAULT_USERNAME = "beyond_the_hoop"

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", DEFAULT_HOST)
TIKTOK_USERNAME = os.getenv("TIKTOK_USERNAME", DEFAULT_USERNAME)

CACHE_TTL = 3600  # 1 heure
_cache = {"videos": [], "fetched_at": 0}


def _format_published(create_time) -> str:
    """Convertit un timestamp Unix (secondes) en ISO 8601 UTC."""
    if not create_time:
        return ""
    try:
        return datetime.fromtimestamp(int(create_time), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return ""


def _build_video_url(video_id: str, username: str) -> str:
    """Construit l'URL publique TikTok d'une video."""
    if not video_id:
        return ""
    return f"https://www.tiktok.com/@{username}/video/{video_id}"


def fetch_latest_tiktoks(max_results: int = 6) -> list[dict]:
    """Recupere les derniers Reels TikTok via RapidAPI. Cache memoire 1h."""
    now = time.time()
    if _cache["videos"] and (now - _cache["fetched_at"]) < CACHE_TTL:
        return _cache["videos"][:max_results]

    if not RAPIDAPI_KEY:
        logger.warning("RAPIDAPI_KEY non definie — onglet TikTok desactive")
        return []

    url = f"https://{RAPIDAPI_HOST}/user/posts"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
    }
    # On demande plus que max_results pour absorber les videos epinglees
    # (typiquement 1 a 3 par profil) qui seront filtrees ensuite.
    params = {"unique_id": TIKTOK_USERNAME, "count": str(max_results + 6)}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
    except requests.RequestException as e:
        logger.warning("Erreur reseau RapidAPI TikTok: %s", e)
        return []

    if resp.status_code != 200:
        logger.warning("RapidAPI TikTok status %s", resp.status_code)
        return []

    try:
        payload = resp.json()
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("JSON invalide RapidAPI TikTok: %s", e)
        return []

    if payload.get("code") != 0:
        logger.warning("RapidAPI TikTok code applicatif %s: %s",
                       payload.get("code"), payload.get("msg"))
        return []

    videos = []
    for item in payload.get("data", {}).get("videos", []):
        # Skip les videos epinglees pour ne garder que les vraies dernieres
        if item.get("is_top"):
            continue
        video_id = str(item.get("video_id") or "")
        if not video_id:
            continue
        videos.append({
            "video_id": video_id,
            "caption": item.get("title") or "",
            "published": _format_published(item.get("create_time")),
            "thumbnail": item.get("cover") or "",
            "url": _build_video_url(video_id, TIKTOK_USERNAME),
        })

    _cache["videos"] = videos
    _cache["fetched_at"] = now
    return videos[:max_results]
