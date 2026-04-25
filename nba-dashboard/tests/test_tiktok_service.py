from unittest.mock import patch, MagicMock

import pytest
import requests

import tiktok_service
from tiktok_service import (
    _format_published,
    _build_video_url,
    fetch_latest_tiktoks,
)


SAMPLE_PAYLOAD = {
    "code": 0,
    "msg": "success",
    "processed_time": 0.45,
    "data": {
        "videos": [
            {
                "video_id": "7632611984948661526",
                "title": "Insane buzzer beater from last night",
                "create_time": 1777105969,
                "cover": "https://p16-common-sign.tiktokcdn-eu.com/cover1.jpg",
                "play_count": 32416,
            },
            {
                "video_id": "7632611984948661527",
                "title": "Game winner",
                "create_time": 1777019569,
                "cover": "https://p16-common-sign.tiktokcdn-eu.com/cover2.jpg",
                "play_count": 12000,
            },
        ]
    },
}


@pytest.fixture(autouse=True)
def reset_state():
    """Reset cache et la cle API entre chaque test."""
    tiktok_service._cache = {"videos": [], "fetched_at": 0}
    original_key = tiktok_service.RAPIDAPI_KEY
    tiktok_service.RAPIDAPI_KEY = "test-key-123"
    yield
    tiktok_service._cache = {"videos": [], "fetched_at": 0}
    tiktok_service.RAPIDAPI_KEY = original_key


def _mock_response(status=200, payload=None, raise_json=False):
    resp = MagicMock()
    resp.status_code = status
    if raise_json:
        resp.json.side_effect = ValueError("not json")
    else:
        resp.json.return_value = payload if payload is not None else SAMPLE_PAYLOAD
    return resp


class TestFormatPublished:
    def test_unix_timestamp_vers_iso(self):
        result = _format_published(1777105969)
        assert result.startswith("2026-04-25T")
        assert "+00:00" in result

    def test_string_numerique(self):
        result = _format_published("1777105969")
        assert result.startswith("2026-04-25T")

    def test_zero_renvoie_chaine_vide(self):
        assert _format_published(0) == ""
        assert _format_published(None) == ""
        assert _format_published("") == ""

    def test_invalide_renvoie_chaine_vide(self):
        assert _format_published("not a number") == ""


class TestBuildVideoUrl:
    def test_url_construite(self):
        url = _build_video_url("7632611984948661526", "beyond_the_hoop")
        assert url == "https://www.tiktok.com/@beyond_the_hoop/video/7632611984948661526"

    def test_video_id_vide_renvoie_vide(self):
        assert _build_video_url("", "beyond_the_hoop") == ""


class TestFetchLatestTiktoks:
    @patch("tiktok_service.requests.get")
    def test_renvoie_videos_parsees(self, mock_get):
        mock_get.return_value = _mock_response()

        videos = fetch_latest_tiktoks()

        assert len(videos) == 2
        v = videos[0]
        assert v["video_id"] == "7632611984948661526"
        assert v["caption"] == "Insane buzzer beater from last night"
        assert v["published"].startswith("2026-04-25T")
        assert v["thumbnail"] == "https://p16-common-sign.tiktokcdn-eu.com/cover1.jpg"
        assert v["url"] == "https://www.tiktok.com/@beyond_the_hoop/video/7632611984948661526"

    @patch("tiktok_service.requests.get")
    def test_envoie_les_bons_headers(self, mock_get):
        mock_get.return_value = _mock_response()
        fetch_latest_tiktoks()
        kwargs = mock_get.call_args.kwargs
        headers = kwargs["headers"]
        assert headers["X-RapidAPI-Key"] == "test-key-123"
        assert headers["X-RapidAPI-Host"] == "tiktok-scraper7.p.rapidapi.com"
        assert kwargs["params"]["unique_id"] == "beyond_the_hoop"

    @patch("tiktok_service.requests.get")
    def test_tronque_a_max_results(self, mock_get):
        mock_get.return_value = _mock_response()
        videos = fetch_latest_tiktoks(max_results=1)
        assert len(videos) == 1

    @patch("tiktok_service.requests.get")
    def test_cache_hit_evite_2eme_requete(self, mock_get):
        mock_get.return_value = _mock_response()

        fetch_latest_tiktoks()
        fetch_latest_tiktoks()

        assert mock_get.call_count == 1

    @patch("tiktok_service.requests.get")
    def test_cache_expire_refait_requete(self, mock_get):
        mock_get.return_value = _mock_response()

        fetch_latest_tiktoks()
        tiktok_service._cache["fetched_at"] = 0
        fetch_latest_tiktoks()

        assert mock_get.call_count == 2

    @patch("tiktok_service.requests.get")
    def test_cle_absente_renvoie_liste_vide_sans_requete(self, mock_get):
        tiktok_service.RAPIDAPI_KEY = ""
        result = fetch_latest_tiktoks()
        assert result == []
        mock_get.assert_not_called()

    @patch("tiktok_service.requests.get")
    def test_status_non_200_renvoie_liste_vide(self, mock_get):
        mock_get.return_value = _mock_response(status=403)
        assert fetch_latest_tiktoks() == []

    @patch("tiktok_service.requests.get")
    def test_request_exception_renvoie_liste_vide(self, mock_get):
        mock_get.side_effect = requests.RequestException("connection refused")
        assert fetch_latest_tiktoks() == []

    @patch("tiktok_service.requests.get")
    def test_json_invalide_renvoie_liste_vide(self, mock_get):
        mock_get.return_value = _mock_response(raise_json=True)
        assert fetch_latest_tiktoks() == []

    @patch("tiktok_service.requests.get")
    def test_code_applicatif_non_zero_renvoie_liste_vide(self, mock_get):
        mock_get.return_value = _mock_response(payload={"code": -1, "msg": "rate limit"})
        assert fetch_latest_tiktoks() == []

    @patch("tiktok_service.requests.get")
    def test_video_sans_id_est_skippee(self, mock_get):
        payload = {
            "code": 0,
            "data": {
                "videos": [
                    {"video_id": "", "title": "missing id", "create_time": 1777105969, "cover": "x"},
                    {"video_id": "123", "title": "good", "create_time": 1777105969, "cover": "y"},
                ]
            }
        }
        mock_get.return_value = _mock_response(payload=payload)
        videos = fetch_latest_tiktoks()
        assert len(videos) == 1
        assert videos[0]["video_id"] == "123"
