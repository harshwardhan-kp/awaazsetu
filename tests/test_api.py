import pytest, hashlib, hmac, time, json
from fastapi.testclient import TestClient
from sqlalchemy import select
from backend.app.main import app
from backend.app.db import Base, engine, SessionLocal, Contact, Outbox
from backend.app.security import buckets


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    buckets.clear()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def headers(client):
    result = client.post(
        "/api/auth/login", json={"password": "test-coordinator-password"}
    )
    assert result.status_code == 200
    return {"Authorization": "Bearer " + result.json()["token"]}


def report(
    client,
    text="Water entering home at Ekta Nagar. Elderly person trapped in waist deep water.",
    **kwargs,
):
    return client.post(
        "/api/reports", json={"text": text, "language": "en", "consent": True, **kwargs}
    )


def test_private_console_and_settings(client):
    for url in [
        "/api/incidents",
        "/api/coverage",
        "/api/settings",
        "/api/outbox",
        "/api/export/reports.csv",
    ]:
        assert client.get(url).status_code == 401
    assert client.post("/api/demo/seed").status_code == 401
    assert client.get("/api/health").status_code == 200


def test_consent_channel_and_contact_validation(client):
    assert (
        client.post("/api/reports", json={"text": "Flood at Warje"}).status_code == 422
    )
    assert report(client, channel="sms").status_code == 422
    assert report(client, contact="garbage").status_code == 422
    assert report(client, text="   ").status_code == 422


def test_report_tracking_and_status_notifications(client, headers):
    result = report(client, contact="+919876543210")
    assert result.status_code == 200
    data = result.json()
    ticket = data["ticket_id"]
    token = data["tracking_token"]
    id = data["incident"]["id"]
    assert data["report"]["fields"]["trapped"]
    assert client.get(f"/api/track/{ticket}?token=wrong").status_code == 404
    assert client.get(f"/api/track/{ticket}?token={token}").json()["status"] == "new"
    status = client.patch(
        "/api/incidents/" + id,
        headers=headers,
        json={"status": "verified", "notes": "Checked in drill"},
    )
    assert status.status_code == 200
    tracked = client.get(f"/api/track/{ticket}?token={token}").json()
    assert tracked["status"] == "verified" and "notes" not in str(tracked)
    detail = client.get("/api/incidents/" + id, headers=headers).json()
    assert "9876543210" not in str(detail)
    with SessionLocal() as db:
        c = db.scalar(select(Contact))
        assert (
            c.encrypted_address != "+919876543210"
            and "9876543210" not in c.encrypted_address
        )
        assert len(db.scalars(select(Outbox)).all()) == 2


def test_duplicate_retry_returns_no_tracking_secret(client):
    first = report(client, idempotency_key="test-retry").json()
    again = report(client, idempotency_key="test-retry").json()
    assert again == {"duplicate": True, "ticket_id": first["ticket_id"]}


def test_no_automatic_merge_unknown_or_far_locations(client, headers):
    report(client, text="Residents trapped at unknown bridge")
    report(client, text="Residents trapped at unknown bridge")
    assert client.get("/api/incidents", headers=headers).json()["total"] == 2
    report(client, text="Water entering home at Warje")
    report(client, text="Water entering home at Dattawadi")
    assert client.get("/api/incidents", headers=headers).json()["total"] == 4


def test_exact_duplicate_merges_and_sender_count(client, headers):
    a = report(
        client, contact="+919876543210", latitude=18.478, longitude=73.819
    ).json()
    b = report(
        client, contact="+919876543210", latitude=18.478, longitude=73.819
    ).json()
    assert a["incident"]["id"] == b["incident"]["id"]
    detail = client.get("/api/incidents/" + a["incident"]["id"], headers=headers).json()
    assert detail["report_count"] == 2 and detail["unique_reporters"] == 0


def test_clarification_does_not_guess(client):
    d = report(client, text="People trapped near unnamed bridge").json()
    assert d["incident"]["needs_clarification"] and d["incident"]["latitude"] is None
    url = "/api/track/" + d["ticket_id"] + "/clarify"
    assert (
        client.post(
            url, json={"token": d["tracking_token"], "text": "unknown landmark"}
        ).status_code
        == 422
    )
    r = client.post(url, json={"token": d["tracking_token"], "text": "Warje"})
    assert r.status_code == 200
    assert r.json()["needs_clarification"] == False
    assert (
        client.post(
            url, json={"token": d["tracking_token"], "text": "Dattawadi"}
        ).status_code
        == 409
    )


def test_manual_merge_preserves_tickets(client, headers):
    a = report(client, text="Water entering home at Warje").json()
    b = report(client, text="Road waterlogging at Warje").json()
    result = client.post(
        "/api/incidents/" + a["incident"]["id"] + "/merge",
        headers=headers,
        json={
            "source_id": b["incident"]["id"],
            "reason": "Reviewed both reports; same drill flood event",
        },
    )
    assert result.status_code == 200 and result.json()["report_count"] == 2
    assert (
        client.get(
            f"/api/track/{b['ticket_id']}?token={b['tracking_token']}"
        ).status_code
        == 200
    )
    assert client.get("/api/incidents", headers=headers).json()["total"] == 1


def test_demo_seed_idempotent_and_coverage_honesty(client, headers):
    assert client.post("/api/demo/seed", headers=headers).json()["reports"] == 9
    assert client.post("/api/demo/seed", headers=headers).json()["reports"] == 0
    coverage = client.get("/api/coverage", headers=headers).json()
    assert coverage["synthetic_reports"] == 9 and coverage["total_reports"] == 9
    assert all(
        w["gap_index"] is None for w in coverage["wards"] if w["ward"] == "Unlocated"
    )
    assert "not official" in coverage["baseline_note"]


def sms(client, text, message_id="sms1"):
    return client.post(
        "/api/webhooks/sms",
        headers={"X-Webhook-Secret": "test-webhook-secret"},
        json={
            "deviceId": "device",
            "event": "sms:received",
            "payload": {
                "messageId": message_id,
                "sender": "+919876543210",
                "message": text,
            },
        },
    )


def test_webhook_auth_replay_join_stop(client, headers):
    assert client.post("/api/webhooks/sms", json={}).status_code == 401
    assert sms(client, "JOIN mr Ekta Nagar").json()["command"] == "JOIN"
    a = client.post(
        "/api/alerts",
        headers=headers,
        json={
            "ward": "Pilot area: Ekta Nagar",
            "language": "mr",
            "message": "सराव सूचना",
        },
    ).json()
    assert a["queued"] == 1
    assert sms(client, "JOIN mr Ekta Nagar").json()["duplicate"]
    assert sms(client, "STOP", "sms2").status_code == 200
    assert (
        client.post(
            "/api/alerts",
            headers=headers,
            json={
                "ward": "Pilot area: Ekta Nagar",
                "language": "mr",
                "message": "सराव सूचना",
            },
        ).json()["queued"]
        == 0
    )
    with SessionLocal() as db:
        assert db.scalar(select(Contact)).opted_in == False
        assert (
            db.scalar(
                select(Outbox).where(
                    Outbox.kind == "area_alert", Outbox.message.contains("सराव सूचना")
                )
            ).status
            == "cancelled"
        )


def test_voice_unavailable_honest(client):
    r = client.post(
        "/api/reports/voice",
        files={"audio": ("voice.wav", b"not-real-audio", "audio/wav")},
        data={"consent": "true", "language": "mr"},
    )
    assert r.status_code == 503


def test_login_rate_limit(client):
    for _ in range(5):
        assert (
            client.post("/api/auth/login", json={"password": "wrong"}).status_code
            == 401
        )
    assert client.post("/api/auth/login", json={"password": "wrong"}).status_code == 429


def test_export_formula_injection(client, headers):
    assert report(client, text="=SUM(1,2) Water on road at Warje").status_code == 200
    csv = client.get("/api/export/reports.csv", headers=headers)
    assert csv.status_code == 200 and "'=SUM" in csv.text


def test_approximate_locations_do_not_auto_merge(client, headers):
    a = report(client).json()
    b = report(client).json()
    assert a["incident"]["id"] != b["incident"]["id"]
    assert (
        client.get("/api/incidents/" + a["incident"]["id"], headers=headers).json()[
            "unique_reporters"
        ]
        == 0
    )
    assert not any(
        "distinct reporters" in reason["label"]
        for reason in a["incident"]["severity_reasons"]
    )


def test_sms_hmac_official_payload_timestamp_order(client):
    body = {
        "deviceId": "device",
        "event": "sms:received",
        "payload": {
            "messageId": "signed1",
            "sender": "+919876543210",
            "message": "Road flooded in Warje",
        },
    }
    raw = json.dumps(body).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(
        b"test-webhook-secret", raw + timestamp.encode(), hashlib.sha256
    ).hexdigest()
    r = client.post(
        "/api/webhooks/sms",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Timestamp": timestamp,
            "X-Signature": signature,
        },
    )
    assert r.status_code == 200 and r.json()["ticket_id"].startswith("PN-")
    old = "1"
    sig = hmac.new(
        b"test-webhook-secret", raw + old.encode(), hashlib.sha256
    ).hexdigest()
    assert (
        client.post(
            "/api/webhooks/sms",
            content=raw,
            headers={"X-Timestamp": old, "X-Signature": sig},
        ).status_code
        == 401
    )


def test_public_auto_merge_does_not_disclose_other_reports(client, headers):
    a = report(
        client,
        text="Water in home at Warje. My private description is here.",
        latitude=18.4801,
        longitude=73.803,
    ).json()
    b = report(
        client,
        text="Water in home at Warje. My private description is here.",
        latitude=18.4801,
        longitude=73.803,
    ).json()
    assert a["incident"]["id"] == b["incident"]["id"]
    assert (
        "report_count" not in b["incident"] and "unique_reporters" not in b["incident"]
    )
    assert b["incident"]["ticket_id"] == b["ticket_id"]
    assert b["incident"]["ticket_id"] != a["ticket_id"]


def test_web_optional_phone_cannot_trigger_sms_or_corroboration(client, headers):
    a = report(
        client, contact="+919876543210", latitude=18.478, longitude=73.819
    ).json()
    with SessionLocal() as db:
        item = db.scalar(select(Outbox))
        assert item.status == "awaiting_contact_verification"
    detail = client.get("/api/incidents/" + a["incident"]["id"], headers=headers).json()
    assert detail["unique_reporters"] == 0


def test_sms_commands_preserve_language_and_transactional_kind(client):
    assert sms(client, "JOIN mr Ekta Nagar", "join-lang").status_code == 200
    assert sms(client, "STOP", "stop-lang").status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(Contact)).language == "mr"
        commands = db.scalars(
            select(Outbox).where(Outbox.message.startswith("Area alerts stopped"))
        ).all()
        assert len(commands) == 1 and commands[0].kind == "transactional"


def test_join_area_does_not_drift_on_report(client):
    assert sms(client, "JOIN mr Ekta Nagar", "join-fixed").status_code == 200
    assert sms(client, "Road flooded at Warje", "report-other-area").status_code == 200
    with SessionLocal() as db:
        c = db.scalar(select(Contact))
        assert c.language == "mr" and c.ward == "Pilot area: Ekta Nagar"


def test_retention_removes_old_report_contents(client, headers):
    from backend.app.db import Report, Incident

    d = report(client).json()
    with SessionLocal() as db:
        r = db.scalar(select(Report))
        r.created_at = "2020-01-01T00:00:00+00:00"
        db.commit()
    assert (
        client.post("/api/maintenance/purge", headers=headers).json()["removed_reports"]
        == 1
    )
    assert client.get("/api/incidents", headers=headers).json()["total"] == 0


def test_chunked_upload_body_limit(client):
    def chunks():
        for _ in range(11):
            yield b"x" * 1000000

    assert (
        client.post(
            "/api/reports",
            content=chunks(),
            headers={"content-type": "application/json"},
        ).status_code
        == 413
    )


def test_cross_language_merge_compares_english_summaries(client, monkeypatch):
    import backend.app.service as service

    original = service.extract_report
    inputs = []

    async def extraction(text, language, use_ai=True):
        f = await original(text, language, use_ai=False)
        f["summary"] = (
            "An elderly person is trapped in waist-deep flood water at Ekta Nagar."
        )
        f["extraction_method"] = "openai"
        return f

    async def similarity(a, b, use_ai=True):
        inputs.append((a, b))
        return {"value": 0.95, "method": "openai_embeddings"}

    monkeypatch.setattr(service, "extract_report", extraction)
    monkeypatch.setattr(service, "similarity", similarity)
    a = report(
        client,
        text="Elderly person trapped at Ekta Nagar",
        latitude=18.478,
        longitude=73.819,
    ).json()
    b = report(
        client,
        text="एकता नगरमध्ये आजी अडकल्या आहेत.",
        language="mr",
        latitude=18.478,
        longitude=73.819,
    ).json()
    assert a["incident"]["id"] == b["incident"]["id"]
    assert inputs and all(x.startswith("An elderly person") for x in inputs[0])
    assert b["report"]["text"] == "एकता नगरमध्ये आजी अडकल्या आहेत."
