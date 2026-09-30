# Architecture and engineering decisions

React19 + TypeScript + Vite presents the public reporting form and private coordinator desk. FastAPI manages auth, intake, processing, coordinator actions and durable notifications. SQLAlchemy supports local/persistent SQLite and configurable PostgreSQL. One backend worker is intentional: intake/webhook/delivery locks provide in-process serialization; multi-worker scaling requires database locks/atomic claims and durable worker jobs.

## End-to-end pipeline

1. Validate report length, consent and bounded coordinates. Public clients cannot impersonate SMS/Telegram source channels.
2. Reserve AI budget before network calls. Extract strict-schema facts using OpenAI or deterministic rules. Never execute model output or treat resident text as instructions.
3. Resolve a phrase and then the original report against the local source-linked gazetteer. GPS is constrained to pilot bounds. Unknown/ambiguous locations stay null and trigger a landmark question.
4. Score with the proposal policy; cap100. Vulnerability counted once, water levels mutually exclusive. Home/rescue points can combine; the proposal's70-point example omits home points while its rules imply90, so this implementation explicitly chooses additive90.
5. Auto-merge only open, same-type incidents within500m and3h, with both location confidence>=0.8. Threshold0.75 for embeddings; lexical fallback requires0.9. At most10 candidates; each embedding request has its own budget reservation. Approximate neighborhoods do not auto-merge. Anonymous/web identities do not prove independent corroboration.
6. Persist source message, report ticket and tracking-token hash. Return only the caller's report projection; never a shared incident summary/ticket/count to public intake. Coordinator endpoints expose source reports behind bearer auth.
7. Queue acknowledgement and clarification. Tracking works without a phone. SMSGate/Telegram authenticated inbound senders receive transactional replies when delivery is enabled. Public optional phone numbers remain awaiting verification and never cause outbound messages.
8. Human status changes append history and notify every reporter in their own language. Manual merge is an audited override requiring a rationale; original messages/tickets remain, but target classification/location remain the coordinator-selected target. A mistaken merge requires operator/database recovery; there is no unmerge UI yet.

## Privacy/security

Coordinator login issues HS256 JWT with12-hour expiry. Password/secrets are random and local `.env` is permission600 and gitignored. Contact identities use HMAC-SHA256; delivery addresses use Fernet encryption. Tracking tokens have high entropy and are stored hashed. No public lists/map, phone numbers or coordinator notes in tracking responses. CSP, no-referrer, nosniff and frame denial apply; application access logs are disabled so URL tracking tokens are not written to application access logs. Hosting providers may still have their own access logs.

HTTP bodies are capped cumulatively even without Content-Length. Login/intake/audio have per-process request limits; persistent daily AI caps further limit provider use. Limits are single-instance safeguards, not distributed abuse protection. SMSGate HMAC authenticates raw body + timestamp with300-second freshness; Telegram uses Bot API secret header. Complete webhook processing is serialized and duplicate update IDs are stored. Outbox delivery is serialized, capped at3 attempts and uses SMSGate idempotency message IDs. Accepted-by-gateway is distinguished from delivered-to-handset.

Opt-in is required only for `area_alert`; transactional ticket/command responses do not require alert subscription. STOP cancels pending area alerts. JOIN chooses area/language explicitly, and reporting elsewhere does not silently change a subscription. Alerts only queue to opted-in contacts with the selected language; arbitrary prose is not silently machine translated.

Retention purge runs at startup, daily while the process runs, and via private `/api/maintenance/purge`. Report text, old outbox/history and unused incident records expire after90 days. Active subscribers remain until STOP; unreferenced opted-out contacts older than90 days are removed. Backups require their own retention handling. Raw uploaded audio is processed in memory/temporary files and not retained by this application; AI-provider retention is governed by the user's provider account.

## Deliberate boundaries

Speech provider is OpenAI, rather than claiming IndicConformer has been installed/evaluated. IndicConformer/Sarvam adapters are not included. Location matching is offline; no report text sent to a live geocoder. Pilot-area groups are not official administrative wards. Coverage compares reports to explicitly synthetic drill assignments, not inferred population exposure. No live112/PMC integration, mass telecom sending, real emergency dispatch or model training. Voice read-back confirmation before accepting a report and OTP verification for public phone numbers remain follow-up work.

## Sources used for integrations

- OpenAI speech: https://developers.openai.com/api/docs/guides/speech-to-text
- OpenAI structured outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- SMSGate webhooks/signing: https://docs.sms-gate.app/features/webhooks/
- SMSGate sending: https://docs.sms-gate.app/features/sending-messages/
- Telegram Bot API: https://core.telegram.org/bots/api
- Azure Python hosting/persistent `/home`: https://learn.microsoft.com/en-us/azure/app-service/configure-language-python
