import json
from collections import Counter
from sqlalchemy import select
from ..db import Report, Incident
from ..config import ROOT

BASELINE_NOTE = "Coverage compares observed reports with explicit drill assignments only. A gap does not establish flood exposure or population under-representation. Pilot areas are not official ward boundaries."


def coverage(db):
    reports = db.scalars(select(Report)).all()
    incidents = db.scalars(select(Incident)).all()
    mapping = {i.id: i for i in incidents}
    counts = Counter((mapping[r.incident_id].ward or "Unlocated") for r in reports)
    baseline_path = ROOT / "data/drill_baseline.json"
    baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else {}
    wards = []
    for ward in sorted(set(counts) | set(baseline)):
        expected = baseline.get(ward)
        wards.append(
            {
                "ward": ward,
                "reports": counts[ward],
                "expected_reports": expected,
                "gap_index": round(max(0, 1 - counts[ward] / expected), 3)
                if expected
                else None,
                "baseline": "synthetic drill assignment"
                if expected
                else "not configured",
            }
        )
    return {
        "total_reports": len(reports),
        "total_incidents": len(incidents),
        "unique_reporters": len(
            {
                r.contact_id
                for r in reports
                if r.contact_id and r.channel in {"sms", "telegram"}
            }
        ),
        "by_language": [
            {"label": lang, "count": sum(r.language == lang for r in reports)}
            for lang in ["mr", "hi", "en"]
        ],
        "by_channel": [
            {"label": c, "count": sum(r.channel == c for r in reports)}
            for c in ["sms", "voice", "web", "telegram"]
        ],
        "wards": wards,
        "baseline_note": BASELINE_NOTE,
        "synthetic_reports": sum(r.synthetic for r in reports),
        "anonymous_reports": sum(r.contact_id is None for r in reports),
    }
