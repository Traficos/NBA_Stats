import pytest
import requests

import tiktok_service
from tiktok_service import _extract_video_id, _extract_thumbnail, _format_published

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>@beyond_the_hoop</title>
  <link>https://www.tiktok.com/@beyond_the_hoop</link>
  <description>TikTok feed for beyond_the_hoop</description>
  <item>
    <title>Insane buzzer beater</title>
    <description>&lt;img src="https://p16-sign.tiktokcdn.com/img1.jpg"/&gt;&lt;p&gt;Caption 1&lt;/p&gt;</description>
    <pubDate>Wed, 23 Apr 2026 18:42:11 GMT</pubDate>
    <link>https://www.tiktok.com/@beyond_the_hoop/video/7395123456789012345</link>
  </item>
  <item>
    <title>Game winner</title>
    <description>&lt;img src="https://p16-sign.tiktokcdn.com/img2.jpg"/&gt;</description>
    <pubDate>Tue, 22 Apr 2026 12:00:00 GMT</pubDate>
    <link>https://www.tiktok.com/@beyond_the_hoop/video/7395123456789012346</link>
  </item>
</channel>
</rss>"""


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset le cache module-level entre chaque test."""
    tiktok_service._cache = {"videos": [], "fetched_at": 0}
    yield
    tiktok_service._cache = {"videos": [], "fetched_at": 0}


class TestExtractVideoId:
    def test_url_simple(self):
        link = "https://www.tiktok.com/@beyond_the_hoop/video/7395123456789012345"
        assert _extract_video_id(link) == "7395123456789012345"

    def test_url_avec_query_params(self):
        link = "https://www.tiktok.com/@beyond_the_hoop/video/7395123456789012345?is_from_webapp=1"
        assert _extract_video_id(link) == "7395123456789012345"

    def test_url_invalide_renvoie_chaine_vide(self):
        assert _extract_video_id("https://www.tiktok.com/@user") == ""
        assert _extract_video_id("") == ""


class TestExtractThumbnail:
    def test_description_avec_img(self):
        desc = '<img src="https://p16-sign.tiktokcdn.com/img.jpg"/><p>Caption</p>'
        assert _extract_thumbnail(desc) == "https://p16-sign.tiktokcdn.com/img.jpg"

    def test_description_sans_img(self):
        assert _extract_thumbnail("<p>Just text</p>") == ""
        assert _extract_thumbnail("") == ""

    def test_img_avec_attributs_supplementaires(self):
        desc = '<img alt="thumb" src="https://example.com/x.jpg" width="100"/>'
        assert _extract_thumbnail(desc) == "https://example.com/x.jpg"


class TestFormatPublished:
    def test_rfc822_vers_iso(self):
        result = _format_published("Wed, 23 Apr 2026 18:42:11 GMT")
        assert result.startswith("2026-04-23T18:42:11")

    def test_date_invalide_renvoie_chaine_vide(self):
        assert _format_published("not a date") == ""
        assert _format_published("") == ""


from unittest.mock import patch, MagicMock

from tiktok_service import fetch_latest_tiktoks


def _mock_response(status=200, text=SAMPLE_RSS):
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    return resp


class TestFetchLatestTiktoks:
    @patch("tiktok_service.requests.get")
    def test_renvoie_videos_parsees(self, mock_get):
        mock_get.return_value = _mock_response()

        videos = fetch_latest_tiktoks()

        assert len(videos) == 2
        v = videos[0]
        assert v["video_id"] == "7395123456789012345"
        assert v["caption"] == "Insane buzzer beater"
        assert v["published"].startswith("2026-04-23T18:42:11")
        assert v["thumbnail"] == "https://p16-sign.tiktokcdn.com/img1.jpg"
        assert v["url"] == "https://www.tiktok.com/@beyond_the_hoop/video/7395123456789012345"

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
        # Force l'expiration du cache
        tiktok_service._cache["fetched_at"] = 0
        fetch_latest_tiktoks()

        assert mock_get.call_count == 2

    @patch("tiktok_service.requests.get")
    def test_status_non_200_renvoie_liste_vide(self, mock_get):
        mock_get.return_value = _mock_response(status=404, text="not found")
        assert fetch_latest_tiktoks() == []

    @patch("tiktok_service.requests.get")
    def test_request_exception_renvoie_liste_vide(self, mock_get):
        mock_get.side_effect = requests.RequestException("connection refused")
        assert fetch_latest_tiktoks() == []

    @patch("tiktok_service.requests.get")
    def test_xml_invalide_renvoie_liste_vide(self, mock_get):
        mock_get.return_value = _mock_response(text="<not valid xml")
        assert fetch_latest_tiktoks() == []
