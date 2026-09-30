# AwaazSetu · आवाज़ सेतु

A working multilingual flood-reporting **community-drill MVP** for Pune. Residents submit Marathi, Hindi or English text/audio; coordinators receive an explained triage score and privately review mapped incidents. It is not connected to emergency dispatch.

## Hosted app

- Resident reporting: https://awaazsetu.vercel.app
- Private coordinator console: https://awaazsetu.vercel.app/console
- Persistent API / alternate full app: https://awaazsetu-hkp-2026.azurewebsites.net
- Coordinator password: private local `.env` → `ADMIN_PASSWORD`. Never commit `.env` or paste it into issues.

## Run locally

```sh
cd /Users/harshwardhan/Developer/awaazsetu
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.lock.txt
.venv/bin/python scripts/init_env.py
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Open http://127.0.0.1:8000. For development run `npm --prefix frontend run dev` in a second terminal; Vite proxies `/api` to port8000. Initialize `.env` only on a new checkout; the initializer preserves existing settings. Configure `OPENAI_API_KEY` privately for speech and AI extraction. The text flow works offline with rules.

## Implemented modules

- **M1:** validated consent-based text intake; browser recording/audio uploads with editable transcript review; OpenAI speech transcription; OGG conversion; authenticated SMSGate and Telegram webhooks; idempotency and request/body limits. Actual Android/SIM and Telegram bot provisioning remain external setup.
- **M2:** strict-schema AI extraction plus multilingual keyword fallback; transparent proposal scoring; bounded embedding/lexical comparisons; conservative location/time/type merge gates; human review. Counts corroboration only from authenticated inbound senders.
- **M3:** 449 source-linked OpenStreetMap places plus one explicitly approximate Ekta Nagar anchor; multilingual aliases; fuzzy matching; ambiguity/unknown clarification; GPS bounds; private Leaflet map; coordinator queue, source reports, notes, status and explained manual merge override.
- **M4:** localized acknowledgements/status/landmark prompts; encrypted delivery contacts; durable retry outbox; SMS delivery events; JOIN/STOP area subscriptions; language-specific opted-in alerts; drill coverage baselines; private CSV export; retention maintenance.

The live database is SQLite in Azure persistent `/home` storage, suitable for a small single-worker drill. `DATABASE_URL=postgresql+psycopg://...` supports PostgreSQL. A PostGIS bootstrap script is supplied; PostGIS spatial indexing is not required/used by this release's Python distance calculations. No public incident map.

## Verification

```sh
.venv/bin/python -m pytest -q
.venv/bin/python scripts/evaluate.py
npm --prefix frontend run build
cd frontend && npx playwright test
```

Tests isolate their database and disable paid AI/delivery. The 150-case synthetic evaluation is a developer regression suite, **not field accuracy**. Native Marathi/noisy voice WER, held-out duplicate F1, real landmark accuracy and real SMS acknowledgement latency still require participant recordings/labels and the phone. See `docs/VALIDATION.md` for actual evidence.

## Read next

- `docs/OPERATIONS.md`: Android/Telegram setup, subscriptions, deployment, backup and secrets.
- `docs/ARCHITECTURE.md`: interfaces, privacy and limitations.
- `docs/TRIAGE.md`, `docs/LOCATION.md`, `docs/UI.md`: module details and provenance.
- `docs/DRILL.md`: mock-drill scripts, consent and data-labelling templates.
- `docs/EVALUATION.md`: offline held-out accuracy, severity, duplicate, location, WER, latency and feedback metrics.

## Hosting boundaries

Azure App Service plan `awaazsetu-free` is F1 / Free; Vercel serves the static frontend and proxies the API. Free hosting can sleep or hit platform quotas; an instant/60-second response is not guaranteed. OpenAI API requests are metered separately; server caps AI reservations at200 per UTC day and audio at10MB /2minutes. Each extraction, transcription or embedding request consumes a reservation; provider failures still consume the reservation. Outbound delivery is **disabled** until real gateways are configured. Public web phone numbers are stored encrypted but never trigger SMS or independent-sender corroboration until ownership verification is implemented. Tracking links provide updates immediately.

OSM data © OpenStreetMap contributors, ODbL. Coordinates and pilot-area grouping are not validated ward boundaries. Synthetic drill baselines are labelled explicitly.
