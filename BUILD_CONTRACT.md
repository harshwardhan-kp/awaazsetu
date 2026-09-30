# AwaazSetu implementation contract

Real drill-ready MVP, not an emergency response service. Python FastAPI + SQLAlchemy (SQLite local, PostgreSQL configurable), React/Vite/TypeScript frontend. Backend serves compiled frontend for single deployment. Private coordinator endpoints require bearer auth; public ticket tracking requires random tracking token. No public map. Don't read `.env` or print secrets. No external message sending during tests.

## Ownership
Supervisor: backend core/config/database/API, M1 intake/audio/Telegram/SMS, M4 alerts/coverage, deploy/integration/security testing.
triage agent: ONLY backend/app/m2/, tests/test_triage.py, data/evaluation/, scripts/evaluate.py, docs/TRIAGE.md.
location agent: ONLY backend/app/m3/, data/gazetteer.json, scripts/build_gazetteer.py, tests/test_location.py, docs/LOCATION.md.
frontend agent: ONLY frontend/ and docs/UI.md. Do not edit backend.

## Domain contract
Language en|hi|mr. Channels web|sms|telegram|voice. Datetimes UTC ISO strings.
M2 `backend.app.m2.triage` exports async `extract_report(text: str, language: str | None = None, use_ai: bool = True) -> dict`, pure `score_report(fields: dict, corroborations: int = 1, night: bool = False) -> dict`, async `similarity(a: str, b: str, use_ai: bool = True) -> dict` returns value float,method string. Extract fields: language,incident_type (rescue|medical|water_in_home|road_waterlogging|other),people_count int|null,vulnerable list[str] (elderly|child|disabled|sick),water_level (roof|chest|waist|knee|unknown),needs list[str],location_text str|null,trapped bool,medical_emergency bool,water_entering_home bool,summary str,confidence float,extraction_method str,field_confidence dict. Score: score int 0..100,band critical|high|medium|low,reasons list[{label,points}],version. Water levels mutually exclusive; rescue +40; medical +30; home +20; vulnerability +15 once; road +10 only for road type; 5+ people +10; night +5; 3+ unique senders +10. Main enforces <=500m <=3h and same incident type before merge. Never claim thresholds validated.
M3 `backend.app.m3.location` exports `resolve_location(text: str | None, latitude: float | None = None, longitude: float | None = None) -> dict` returns latitude,longitude,location_name,ward (nullable),confidence float,method str,needs_clarification bool,candidates list. `get_gazetteer() -> list[dict]`. GPS bounds lat18.35..18.70 lon73.65..74.10. Gazetteer id,name,aliases list,latitude,longitude,ward,source,verified bool. Demo Ekta Nagar approx 18.478/73.819 must label approximate. Source real OSM entries if possible, no invented 300–500 landmarks. Unknown -> ask landmark, never guess.

## HTTP frontend contract
Same-origin `/api` default, optional VITE_API_BASE_URL. Errors FastAPI detail. Coordinator token sessionStorage, never bundled.
GET /api/health -> {status,version,mode,capabilities:{ai_extraction,voice,sms,telegram},demo}
POST /api/auth/login {password} -> {token,expires_in}
POST /api/reports {text,language:"mr",channel:"web",contact?:str,consent:true,latitude?:number,longitude?:number,idempotency_key?:str} -> {report,incident,acknowledgement,ticket_id,tracking_token,tracking_url}
POST /api/reports/voice multipart audio,language optional,contact optional,consent=true -> same response. Real transcription or clear 503, no fake transcript.
GET /api/track/{ticket_id}?token=... -> {ticket_id,status,language,acknowledgement,updates:[{status,message,created_at}],needs_clarification,clarification_prompt}
POST /api/track/{ticket_id}/clarify {token,text} -> tracking data
GET /api/incidents?status=&band=&language=&channel=&q= -> {items:[Incident],total}
GET /api/incidents/{id} -> Incident incl reports,history
PATCH /api/incidents/{id} {status?:new|verified|responding|resolved|dismissed,notes?:str} -> Incident
POST /api/incidents/{id}/merge {source_id:str} -> Incident
GET /api/coverage -> {total_reports,total_incidents,unique_reporters,by_language:[{label,count}],by_channel:[{label,count}],wards:[{ward,reports,expected_reports,gap_index,baseline}],baseline_note}
GET /api/outbox -> {items:[{id,channel,ticket_id,language,message,status,created_at,attempts}],total}
POST /api/outbox/retry -> {processed,sent,failed}
POST /api/alerts {ward,language?:str,message} -> {queued,alert_id} (opted-in only)
GET /api/settings -> {demo,integrations:[{name,configured,description}],gazetteer_count,baseline_note}
POST /api/demo/seed -> {reports,incidents} idempotent, coordinator-only, demo enabled only
GET /api/export/reports.csv private

Incident: id,ticket_id,summary,incident_type,status,severity_score,severity_band,severity_reasons:[{label,points}],latitude,longitude,location_name,location_method,location_confidence,ward,needs_clarification,report_count,unique_reporters,languages:[str],channels:[str],created_at,updated_at,reports?:[Report],history?:[{status,notes,created_at}]. Report: id,ticket_id,text,language,channel,fields,created_at,extraction_method,location,consent; no contacts exposed.

## UI
Resident `/` Marathi/Hindi/English localized form,microphone/voice upload,consent,optional GPS,ticket confirmation. Console `/console` auth, polished operational dashboard with private Leaflet map,queue,detail drawer rationale and source text,filters,verify/respond/resolve/dismiss + merge. `/console/coverage`, `/console/notifications`, `/console/settings`; tracking `/track/:ticket_id?token=`. Responsive/mobile, visible drill mode,honest missing integrations,accessible forms,empty/loading/errors. No fake data hardcoded in UI, use seed endpoint. Map attribution and location accuracy disclaimer.

## Final reviewed refinements
Public intake returns caller-specific incident projection, never shared incident metadata. MergeIn requires reason; human merge is an explicit audited override. Automatic merges require confidence>=0.8 on both locations, known same type and <=500m/3h; lexical threshold0.9, embeddings0.75. AI extraction summary is English for cross-language comparison; source text remains unchanged. Only authenticated SMS/Telegram source identities count as independent reporters. Outbox.kind distinguishes transactional vs area_alert; optional public phone replies await verification. Retention is implemented at startup/daily/admin endpoint. Single-worker deployment is required by process locks.
