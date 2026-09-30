# M3: private pilot location resolution

`backend.app.m3.location.resolve_location(text, latitude=None, longitude=None)` returns a conservative location decision. It performs no network requests and never sends residents' text to a geocoder. `get_gazetteer()` returns source-linked records for the coordinator UI and evaluation.

## Data and provenance

`data/gazetteer.json` contains 450 records: 449 real OpenStreetMap objects imported via a bounded Overpass query and one explicitly approximate project-proposal anchor for Ekta Nagar. Every OSM record links to its original node/way/relation and records the OSM database snapshot timestamp. Feature centres for ways/relations are approximate landmarks, not household coordinates. All records have `verified: false`: importing a public source is not field validation. Duplicate place names remain possible and intentional. The data covers a bounded Pune/Mutha pilot region (18.43–18.59 N, 73.75–73.93 E); the allowed GPS submission region is broader (18.35–18.70 N, 73.65–74.10 E).

Data attribution: **© OpenStreetMap contributors**, [ODbL and copyright](https://www.openstreetmap.org/copyright). The extracted OSM database remains subject to the ODbL; retain its attribution and licence when redistributing it. Source records can change after the bundled snapshot. The build query and transformation are in `scripts/build_gazetteer.py`.

Ekta Nagar at 18.478 N / 73.819 E comes from the project contract as an approximate neighbourhood anchor. Its source explicitly says it requires field validation and its method is `gazetteer_approximate`, with confidence capped at 0.65. Do not describe this position as geocoded or verified.

## Resolution behavior

* GPS requires both finite numbers within the pilot bounds. Missing halves and out-of-region coordinates require clarification. GPS positions do not inherit a neighbourhood position; a nearby landmark name is supplied only within 250 metres. Device accuracy is unknown.
* Unicode-normalized English, Marathi and Hindi names use OSM native-language aliases plus curated transliterated spelling variants for major neighbourhoods (Warje, Karve Nagar, Vadgaon/Wadgaon Budruk, Erandwane/Erandawane and others). Marathi and Hindi share Devanagari aliases. This is an alias-based multilingual resolver, not universal translation or arbitrary Devanagari transliteration.
* Exact name matches require complete name boundaries. The longest recognized landmark wins over a shorter containing neighbourhood. Short generic fragments such as `Nagar` do not select a location.
* Minor spelling differences can use contiguous token windows and a similarity threshold of 0.88. Near-tied matches within 0.06 and more than 250 metres apart produce `ambiguous`, null coordinates and up to five source-linked candidates.
* Unknown text always produces null coordinates and `needs_clarification: true`. Ask for a nearby named landmark or a GPS pin. The coordinator should verify any result against the resident before dispatch.
* Confidence values are heuristics, not validated accuracy percentages. Broad neighbourhood matches are capped at 0.75. No geocoder result proves that a resident is at a precise point.

The `ward` field carries **`Pilot area: <name>`** labels for records within 1.5 km of selected neighbourhood anchors. These labels are operational pilot groupings, not PMC administrative wards or point-in-polygon assignments. Unassigned records retain `ward: null`. Coverage dashboards must preserve the prefix and must not claim administrative boundaries or population-based reporting gaps from these groupings.

## Rebuild and verify

```sh
python scripts/build_gazetteer.py
python -m pytest tests/test_location.py -q
```

The builder contacts one public Overpass endpoint once, with a bounded query and 90-second query limit. It retains the existing file if fewer than 300 real/explicitly sourced records are returned; it does not invent entries to meet a quota. `--endpoint` allows an operator-chosen compliant endpoint, and `--input response.json` rebuilds offline from a saved Overpass response. Avoid repeatedly rebuilding against a shared public service.

No live Nominatim dependency is needed. If an operator later introduces external geocoding, obtain an approved data disclosure design first, comply with that service's current usage policy, cache results, and retain attribution. [OSMF API policy](https://operations.osmfoundation.org/policies/api/) and [Overpass documentation](https://wiki.openstreetmap.org/wiki/Overpass_API) are primary references.
