import pytest

import tiktok_service
from tiktok_service import _extract_video_id, _extract_thumbnail, _format_published


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
