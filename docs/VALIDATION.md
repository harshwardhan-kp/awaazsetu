# Verification record · 1 October 2026 (India)

## Confirmed

- Backend: **84 passing tests**, covering multilingual extraction/negation/adversarial prompts, score thresholds, location ambiguity/GPS bounds/Marathi suffixes, privacy/auth, report consent, tracking/status/clarification, merge preservation, identified-sender corroboration, webhook signing/replay/commands, subscription preferences, body and decoded audio duration limits, offline held-out evaluator arithmetic, retention, CSV injection and concurrent delivery. One upstream TestClient deprecation warning remains.
- Synthetic triage regression suite: **150/150**, 50 each English/Hindi/Marathi. This is a template fixture suite and does not establish real-world accuracy, severity F1 or critical recall.
- Frontend: TypeScript and Vite production build; npm production dependency audit reports zero vulnerabilities. Seven mocked browser workflow/responsive tests separately verify UI contracts.
- Real hosted browser workflow: public API auth denial, Marathi form, actual text submission, private tracking, password login, incident map/detail, synthetic seed, status action, coverage/outbox/settings, desktop1440/mobile390 screenshots, no page overflow and no JavaScript runtime errors.
- Real OpenAI strict-schema extraction correctly canonicalized the supplied Marathi flood example to rescue/trapped/elderly/waist/Ekta Nagar. Rule-policy additive score90 (+5 if night at intake), with the proposal's point ambiguity documented.
- Real OpenAI speech test: a **synthetic English** audio clip was transcribed, submitted through the hosted voice endpoint, extracted as rescue and successfully tracked. One measured warm hosted request completed in approximately5.33seconds. This is not Marathi/Hindi WER and not SMS handset acknowledgement latency.
- Real multilingual embedding experiment: raw English/Marathi equivalent reports scored0.285, below the proposal threshold. English factual summaries from the existing extraction call scored0.892 for one synthetic pair. Service now compares those summaries, while preserving original messages. One pair is not duplicate-merge F1; approximate locations are intentionally not auto-merged.
- Gazetteer: 449 source-linked OSM records +1 explicitly approximate anchor; no fabricated ward boundaries.
- Live deployments: Vercel frontend/API proxy and Azure Python backend with persistent SQLite under `/home`. Azure plan verified F1 / Free. No existing VM/network resources modified.
- Local encrypted-contact backup helper executed successfully; source secret scan passed and `.env` is gitignored. No external SMS or Telegram messages were sent.

## Still requires external setup or data

Android/SIM and real gateway delivery, Telegram token/voice webhook, real multilingual participant recordings, noisy-speech WER, two-labeller held-out data, real duplicate/location F1, SMS60-second target, administrative ward boundaries/population baselines and a consenting community drill. IndicConformer/Sarvam are not installed adapters; implemented speech provider is OpenAI.

## Not verified here

PostgreSQL/PostGIS deployment, Docker image build, provider/phone multipart-delivery behavior, disaster-scale load, real emergency response performance and automatic remote backups. The live release intentionally uses one worker and persistent SQLite for a small drill. Process locks/rate limits are not a multi-instance coordination design.

## Reproduce

From project root: `.venv/bin/python -m pytest -q`, `.venv/bin/python scripts/evaluate.py`, `npm --prefix frontend run build`.

From `frontend/`: `npx playwright test` (correct local config/dependency version).

From root: `node scripts/smoke_browser.mjs` verifies the real hosted flow. It uses private local coordinator password silently, creates a clearly labelled drill-only report and seeds synthetic data; no real messaging gateways are enabled. Screenshots/evidence are under gitignored `work/`.
