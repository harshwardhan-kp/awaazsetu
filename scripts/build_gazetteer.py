#!/usr/bin/env python3
"""Download bounded Pune landmarks from OSM. No invented filler or live report queries."""

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
QUERY = """[out:json][timeout:90];(
 nwr["name"]["place"](18.43,73.75,18.59,73.93);
 nwr["name"]["amenity"~"hospital|clinic|school|college|university|police|fire_station|place_of_worship|community_centre|bus_station|library|townhall"](18.43,73.75,18.59,73.93);
 nwr["name"]["railway"="station"](18.43,73.75,18.59,73.93);
 nwr["name"]["bridge"="yes"](18.43,73.75,18.59,73.93);
);out center tags;"""
ALIASES = {
    "Warje": ["वारजे", "वारजे माळवाडी", "Warje Malwadi"],
    "Karve Nagar": ["कर्वे नगर", "कर्वेनगर", "Karvenagar"],
    "Sinhagad Road": ["सिंहगड रोड", "सिंहगड रस्ता", "Sinhgad Road"],
    "Deccan Gymkhana": ["डेक्कन", "डेक्कन जिमखाना", "Deccan"],
    "Shivajinagar": ["शिवाजीनगर", "Shivaji Nagar"],
    "Kothrud": ["कोथरूड", "कोथरुड"],
    "Dattawadi": ["दत्तवाडी", "Datta Wadi"],
    "Vadgaon Budruk": ["वडगाव बुद्रुक", "Wadgaon Budruk", "Vadgaon Bk"],
    "Hingne Khurd": ["हिंगणे खुर्द", "Hingane Khurd"],
    "Nanded": ["नांदेड", "Nanded Gaon"],
    "Erandwane": ["एरंडवणे", "Erandawane"],
    "Pune": ["पुणे", "Poona"],
}


def build(elements, timestamp):
    rows = []
    for e in elements:
        tags = e.get("tags", {})
        name = tags.get("name:en") or tags.get("name")
        c = e.get("center", e)
        if not name or "lat" not in c or "lon" not in c:
            continue
        aliases = set(ALIASES.get(name, []))
        for key in (
            "name",
            "name:en",
            "name:mr",
            "name:hi",
            "alt_name",
            "short_name",
            "loc_name",
            "official_name",
        ):
            aliases.update(x.strip() for x in tags.get(key, "").split(";") if x.strip())
        aliases.discard(name)
        rows.append(
            {
                "id": f"osm-{e['type']}-{e['id']}",
                "name": name,
                "aliases": sorted(aliases),
                "latitude": c["lat"],
                "longitude": c["lon"],
                "ward": None,
                "source": f"https://www.openstreetmap.org/{e['type']}/{e['id']}",
                "verified": False,
                "coordinate_accuracy": "OSM point or feature centre; not field verified",
                "osm_timestamp": timestamp,
                "category": tags.get("place")
                or tags.get("amenity")
                or tags.get("railway")
                or "bridge",
            }
        )
    # Keep every locality before selecting useful nearby amenities, spatially spread over the area.
    priorities = {
        "suburb": 0,
        "neighbourhood": 0,
        "quarter": 0,
        "village": 0,
        "town": 0,
        "city": 0,
        "hospital": 1,
        "police": 1,
        "fire_station": 1,
        "bridge": 1,
        "station": 1,
    }
    rows.sort(
        key=lambda r: (
            priorities.get(r["category"], 2),
            math.hypot(r["latitude"] - 18.505, r["longitude"] - 73.835),
            r["id"],
        )
    )
    seen = set()
    selected = []
    deferred = []
    counts = {}
    caps = {
        "hospital": 65,
        "bridge": 30,
        "school": 65,
        "place_of_worship": 65,
        "clinic": 50,
    }
    for r in rows:
        key = (r["name"].casefold(), round(r["latitude"], 3), round(r["longitude"], 3))
        if key not in seen:
            seen.add(key)
            category = r["category"]
            if counts.get(category, 0) >= caps.get(category, 100):
                deferred.append(r)
                continue
            selected.append(r)
            counts[category] = counts.get(category, 0) + 1
        if len(selected) >= 449:
            break
    selected.extend(deferred[: max(0, 449 - len(selected))])
    selected.append(
        {
            "id": "pilot-ekta-nagar-approx",
            "name": "Ekta Nagar",
            "aliases": ["एकता नगर", "एकतानगर", "Ektanagar"],
            "latitude": 18.478,
            "longitude": 73.819,
            "ward": "Pilot area: Ekta Nagar",
            "source": "Project proposal approximate pilot anchor; requires field validation",
            "verified": False,
            "coordinate_accuracy": "Approximate neighbourhood anchor, not a household position",
            "category": "pilot_area",
        }
    )
    # Group only into explicitly named pilot areas near imported locality anchors. These are not ward boundaries.
    anchors = [
        r
        for r in selected
        if r["name"] in ALIASES
        and r["category"] in ("suburb", "neighbourhood", "quarter", "village")
    ]
    anchors += [selected[-1]]
    for r in selected:
        near = sorted(
            anchors,
            key=lambda a: math.hypot(
                (r["latitude"] - a["latitude"]) * 111,
                (r["longitude"] - a["longitude"]) * 105,
            ),
        )
        if (
            near
            and math.hypot(
                (r["latitude"] - near[0]["latitude"]) * 111,
                (r["longitude"] - near[0]["longitude"]) * 105,
            )
            <= 1.5
        ):
            r["ward"] = f"Pilot area: {near[0]['name']}"
    return selected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="https://overpass-api.de/api/interpreter")
    parser.add_argument(
        "--input", type=Path, help="Existing Overpass JSON response; rebuild offline"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "data/gazetteer.json")
    args = parser.parse_args()
    if args.input:
        payload = json.loads(args.input.read_text())
    else:
        req = Request(
            args.endpoint,
            data=urlencode({"data": QUERY}).encode(),
            headers={"User-Agent": "AwaazSetu-pilot-gazetteer/1.0"},
        )
        with urlopen(req, timeout=120) as response:
            payload = json.load(response)
    stamp = payload.get("osm3s", {}).get(
        "timestamp_osm_base", datetime.now(timezone.utc).isoformat()
    )
    rows = build(payload["elements"], stamp)
    if len(rows) < 300:
        raise SystemExit(
            f"Only {len(rows)} sourced landmarks; existing file left unchanged."
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    print(
        f"Wrote {len(rows)} landmarks; OSM snapshot {stamp}. Attribution: © OpenStreetMap contributors, ODbL https://www.openstreetmap.org/copyright"
    )


if __name__ == "__main__":
    main()
