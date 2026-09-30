# AwaazSetu web interface

React 19 / TypeScript / Vite application. Warm cream, navy, teal and muted orange visual language; responsive resident form and private operations console.

## Run

`cd frontend && npm ci && npm run dev` starts the UI at port 5173 and proxies `/api` to port 8000. `npm run build` produces `frontend/dist`, which the backend serves. Optional `VITE_API_BASE_URL` selects another API origin; default is same origin. Never place API keys or coordinator passwords in Vite environment variables.

## Implemented routes

- `/`: Marathi (default), Hindi and English resident forms; required consent including disclosure that text/audio may be processed by the configured AI provider, optional contact and GPS; text report or real microphone capture/audio upload. Audio is submitted to the server for transcription; unavailable transcription shows the server error. Receipt includes private ticket link and acknowledgement.
- `/track/:ticket_id?token=…`: private ticket status and updates, location clarification, manual refresh. Receiving a ticket does not promise assistance.
- `/console`: password login, per-tab sessionStorage bearer token, incident metrics from current filters, private Leaflet/OpenStreetMap map, priority queue with search/status/band/language/channel filters. Detail drawer shows rationale, original messages, approximate location confidence, coordinator notes/actions, duplicate merge and history. Drawer has keyboard focus trapping, Escape close, and focus restoration.
- `/console/coverage`: API-backed totals, language/channel bars and ward reporting table with missing-baseline caveat.
- `/console/notifications`: outbox with honest queue/delivery status, retry operation and alerts to opted-in ward recipients.
- `/console/settings`: integration readiness, gazetteer count, baseline caveat, private CSV export and server-provided idempotent drill seed.

## Verification

`npm run build` type-checks and builds successfully. `npx playwright test` uses installed Chrome and isolated mocked API responses to verify resident language/submission/tracking clarification, coordinator login/source review/status update/all operations routes, and horizontal overflow at 390, 768 and 1440 pixels. Five frontend contract tests pass. A separate `node tests/live-check.mjs` check passed against the actual local backend: real text intake, private tracking, silent coordinator login, incident detail, coverage, notifications, system settings, mobile console overflow, and no browser runtime errors. That script reads the local coordinator password without printing it and creates a DRILL ONLY test report; no live messages are sent. These checks are not proof of live gateway delivery or real-world triage quality. Test fixtures live only in `frontend/tests`; the actual app contains no hardcoded report dataset.

## Boundaries

The drill banner warns that this is not an emergency response service. Locations require verification before acting; scores are advisory and not field validated. Map tiles and Google font loading require internet; system fonts are fallback. Contact fields never appear in console incident data. Tokens are per-tab and removed on 401/sign out. Resident tracking links grant access to that ticket and should be kept private. Gateway/AI configuration and live SMS/Telegram/voice capability are backend concerns.

## Voice read-back confirmation

Resident audio now previews in a playback control. With consent checked, Marathi/Hindi/English users select the localized Transcribe and review action. POST `/api/transcriptions` returns an editable transcript without creating a ticket. Sending stays disabled until the user confirms the reviewed transcript; editing or replacing audio clears that confirmation. Final submission sends the corrected text to `/api/reports` with channel `voice`, preserving contact/GPS/consent and the 4000-character limit. The audio is transcribed once, rather than again on final submission. Provider errors remain explicit. Seven browser contract tests include preview consent/review gates, edited voice text payload, single transcription, unavailable-provider error and replacement-audio reset.
