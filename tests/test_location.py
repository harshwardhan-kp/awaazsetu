import json
import math
from unittest.mock import patch
from backend.app.m3.location import resolve_location, get_gazetteer


def test_source_linked_gazetteer():
    rows = get_gazetteer()
    assert 300 <= len(rows) <= 500
    assert len({r["id"] for r in rows}) == len(rows)
    osm = [r for r in rows if r["id"].startswith("osm-")]
    assert len(osm) >= 299
    assert all(r["source"].startswith("https://www.openstreetmap.org/") for r in osm)
    assert all(not r["verified"] for r in rows)
    assert all(r["ward"] is None or r["ward"].startswith("Pilot area:") for r in rows)


def test_ekta_three_languages_and_approximation():
    for text in [
        "Water entering home in Ekta Nagar",
        "एकता नगर में पानी",
        "एकतानगर येथे पाणी",
    ]:
        result = resolve_location(text)
        assert result["location_name"] == "Ekta Nagar"
        assert result["method"] == "gazetteer_approximate"
        assert result["confidence"] <= 0.65
        assert result["verified"] is False


def test_unknown_never_guesses():
    for text in [None, "", "water in my home", "unknown xyz place", "नगर", "Nagar"]:
        result = resolve_location(text)
        assert result["needs_clarification"]
        assert result["latitude"] is None


def test_gps_and_invalid_bounds():
    assert resolve_location(None, 18.49, 73.83)["method"] == "gps"
    for lat, lon in [
        (0, 0),
        (18.49, None),
        (float("nan"), 73.83),
        (18.49, float("inf")),
    ]:
        assert resolve_location("Ekta Nagar", lat, lon)["needs_clarification"]


def test_duplicate_name_requires_clarification():
    places = [
        dict(
            id="a",
            name="Central School",
            aliases=[],
            latitude=18.48,
            longitude=73.81,
            ward=None,
        ),
        dict(
            id="b",
            name="Central School",
            aliases=[],
            latitude=18.55,
            longitude=73.88,
            ward=None,
        ),
    ]
    with patch("backend.app.m3.location._load", return_value=places):
        result = resolve_location("near Central School")
        assert result["method"] == "ambiguous"
        assert result["latitude"] is None
        assert len(result["candidates"]) == 2


def test_fuzzy_small_typo_and_short_words():
    places = [
        dict(
            id="a",
            name="Kothrud",
            aliases=["कोथरूड"],
            latitude=18.5,
            longitude=73.81,
            ward=None,
        )
    ]
    with patch("backend.app.m3.location._load", return_value=places):
        assert resolve_location("Kothrud")["location_name"] == "Kothrud"
        assert resolve_location("Kothrudd")["method"] == "gazetteer_fuzzy"
        assert resolve_location("Kot")["needs_clarification"]
        assert resolve_location("कोथरूड")["location_name"] == "Kothrud"


def test_gazetteer_copy_is_independent():
    rows = get_gazetteer()
    name = rows[0]["name"]
    rows[0]["name"] = "corrupted"
    rows[0]["aliases"].append("fake alias")
    assert get_gazetteer()[0]["name"] == name
    assert "fake alias" not in get_gazetteer()[0]["aliases"]


def test_exact_proposal_marathi_message_attached_postposition():
    from backend.app.m3.location import resolve_location

    result = resolve_location(
        "एकता नगरमध्ये घरात पाणी शिरलं आहे, कमरेइतकं पाणी, आजी अडकल्या आहेत."
    )
    assert result["location_name"] == "Ekta Nagar" and not result["needs_clarification"]
    assert result["method"] == "gazetteer_approximate"
