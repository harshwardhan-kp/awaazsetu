"""Resolve text against a source-linked gazetteer without external report disclosure.

Scores represent matching heuristics, not measured positional accuracy. Administrative
ward boundaries are deliberately not inferred from nearest neighbourhood anchors.
"""

from functools import lru_cache
from pathlib import Path
import json
import math
import re
import unicodedata
from difflib import SequenceMatcher

GAZETTEER_PATH = Path(__file__).resolve().parents[3] / "data" / "gazetteer.json"
# backend/app/m3/location.py -> repository root is parents[3].
BOUNDS = (18.35, 18.70, 73.65, 74.10)
FUZZY_THRESHOLD = 0.88
AMBIGUITY_MARGIN = 0.06


def normalize(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"[^\w\s\u0900-\u097f]", " ", text)
    tokens = text.replace("_", " ").split()
    # Marathi postpositions attach to place names (नगरमध्ये, वारजेला).
    # Strip only explicit long locative suffixes; never arbitrary trailing letters.
    tokens = [
        re.sub(r"(मध्ये|मधील|जवळ)$", "", t) if re.search(r"[\u0900-\u097f]", t) else t
        for t in tokens
    ]
    return " ".join(tokens)


@lru_cache(maxsize=1)
def _load():
    with GAZETTEER_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def get_gazetteer():
    """Return independent records so callers cannot alter cached resolution data."""
    return [dict(r, aliases=list(r.get("aliases", []))) for r in _load()]


def _distance(a, b):
    lat1, lon1, lat2, lon2 = map(
        math.radians, (a["latitude"], a["longitude"], b["latitude"], b["longitude"])
    )
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 6371000 * 2 * math.asin(min(1, math.sqrt(h)))


def _candidate(row, score):
    return {
        k: row.get(k)
        for k in (
            "id",
            "name",
            "latitude",
            "longitude",
            "ward",
            "source",
            "verified",
            "coordinate_accuracy",
        )
    } | {"confidence": round(score, 3)}


def _unknown(method="unknown", candidates=None):
    return {
        "latitude": None,
        "longitude": None,
        "location_name": None,
        "ward": None,
        "confidence": 0.0,
        "method": method,
        "needs_clarification": True,
        "candidates": candidates or [],
    }


def _resolved(row, confidence, method, candidates):
    return {
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "location_name": row["name"],
        "ward": row.get("ward"),
        "confidence": round(confidence, 3),
        "method": method,
        "needs_clarification": False,
        "candidates": candidates,
        "source": row.get("source"),
        "verified": row.get("verified", False),
        "coordinate_accuracy": row.get("coordinate_accuracy"),
    }


def _contains(query, alias):
    # Unicode marks are not all \w characters, hence space boundaries on normalized text.
    return f" {alias} " in f" {query} "


def resolve_location(
    text: str | None, latitude: float | None = None, longitude: float | None = None
) -> dict:
    rows = _load()
    if latitude is not None or longitude is not None:
        try:
            lat, lon = float(latitude), float(longitude)
        except (ValueError, TypeError):
            return _unknown("invalid_gps")
        if (
            not math.isfinite(lat)
            or not math.isfinite(lon)
            or not (BOUNDS[0] <= lat <= BOUNDS[1] and BOUNDS[2] <= lon <= BOUNDS[3])
        ):
            return _unknown("outside_pilot_bounds")
        point = {"latitude": lat, "longitude": lon}
        closest = min(rows, key=lambda r: _distance(point, r), default=None)
        distance = _distance(point, closest) if closest else float("inf")
        return {
            "latitude": lat,
            "longitude": lon,
            "location_name": closest["name"]
            if closest and distance <= 250
            else "Provided GPS location",
            "ward": closest.get("ward") if closest and distance <= 250 else None,
            "confidence": 0.95,
            "method": "gps",
            "needs_clarification": False,
            "candidates": [_candidate(closest, 0.95)]
            if closest and distance <= 250
            else [],
            "coordinate_accuracy": "Device-supplied position; device accuracy not provided",
            "verified": False,
        }
    query = normalize(text or "")
    if not query:
        return _unknown()
    matches = []
    for row in rows:
        aliases = [normalize(a) for a in [row["name"], *row.get("aliases", [])]]
        exact = [a for a in aliases if len(a) >= 4 and _contains(query, a)]
        if exact:
            matches.append((row, 0.92, max(len(a) for a in exact), "gazetteer_exact"))
    if matches:
        # A long named landmark takes precedence over its containing suburb name.
        longest = max(m[2] for m in matches)
        matches = [m for m in matches if m[2] == longest]
    elif len(query) <= 120:
        for row in rows:
            aliases = [normalize(a) for a in [row["name"], *row.get("aliases", [])]]
            best = 0.0
            for alias in aliases:
                if len(alias) < 6:
                    continue
                # Match same-length contiguous token windows, including romanized aliases.
                parts = query.split()
                width = len(alias.split())
                spans = [
                    " ".join(parts[i : i + width])
                    for i in range(max(0, len(parts) - width + 1))
                ]
                best = max(
                    best,
                    *(SequenceMatcher(None, alias, span).ratio() for span in spans),
                    0.0,
                )
            if best >= FUZZY_THRESHOLD:
                matches.append((row, best, 0, "gazetteer_fuzzy"))
    if not matches:
        return _unknown()
    matches.sort(key=lambda m: (-m[1], m[0]["id"]))
    top = matches[0]
    close = [m for m in matches if top[1] - m[1] < AMBIGUITY_MARGIN]
    candidates = [_candidate(m[0], m[1]) for m in close[:5]]
    # Repeated branch names and mentions of distant equal-specificity places require a choice.
    if any(_distance(top[0], other[0]) > 250 for other in close[1:]):
        return _unknown("ambiguous", candidates)
    row, score, _, method = top
    if row.get("category") == "pilot_area":
        method = "gazetteer_approximate"
        score = min(score, 0.65)
    elif row.get("category") in (
        "suburb",
        "neighbourhood",
        "quarter",
        "village",
        "city",
        "town",
    ):
        score = min(score, 0.75)
    return _resolved(row, score, method, candidates)
