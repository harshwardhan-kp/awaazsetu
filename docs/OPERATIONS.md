# Operator guide

## First demonstration

1. Open the resident site and submit the supplied Marathi example with consent. Save its private tracking link.
2. Open `/console` and use `ADMIN_PASSWORD` from the private local `.env` (or private handoff file). No password is bundled in the frontend.
3. Use System → Load drill examples to add nine labelled synthetic reports once. Repeated seeding is idempotent.
4. Select an incident, inspect the source text/location confidence/score reasons and record a review note. Verify or move it to responding/resolved. Tracking shows localized status changes.
5. Inspect Coverage, Notifications and System readiness. `available_in_ticket` means visible through tracking; `awaiting_contact_verification` means an optional public phone will not receive outbound SMS. `queued` is not delivered.
6. Manual merge requires a review rationale. It is an explicit override, so verify the locations/types/times yourself before merging.

## Android/SIM later

Install SMS Gateway for Android from its official project, connect a spare phone/SIM, choose local/private/cloud mode and configure credentials privately:

- `SMS_GATEWAY_URL`: API base, e.g. `https://api.sms-gate.app/3rdparty/v1`
- `SMS_GATEWAY_USER`, `SMS_GATEWAY_PASSWORD`: from gateway app
- `SMS_WEBHOOK_SECRET`: app Settings → Webhooks → Signing Key
- Register `sms:received`, `sms:sent`, `sms:delivered`, `sms:failed` for `https://awaazsetu-hkp-2026.azurewebsites.net/api/webhooks/sms` using `scripts/setup_integrations.py sms`.
- SMSGate signs original JSON payload concatenated with Unix timestamp; server rejects stale/bad signatures. A trusted adapter can alternatively send `X-Webhook-Secret`.
- Show the community the consent/privacy notice before the drill: sending to the drill number consents to report processing, transactional replies and configured AI processing. Sending a report does not subscribe to area alerts.
- Enable `DELIVERY_ENABLED=true` only after a controlled phone test. Redeploy settings with the included script; never place credentials in shell history or code.

SMS commands: `JOIN mr Ekta Nagar` (explicit consent to Marathi alerts for the area), `JOIN hi Warje`, `STOP`, `STATUS PN-...`, `LOCATION PN-... Warje`. JOIN/STOP do not stop transactional report status replies. Registered multipart delivery callbacks are represented at message level; real carrier behavior must be tested.

## Telegram later

Create a private bot through BotFather yourself. Set `TELEGRAM_BOT_TOKEN` and a random `TELEGRAM_WEBHOOK_SECRET` in private configuration. Run `scripts/setup_integrations.py telegram`. Private chats only; `/start` gives the drill/AI consent notice. Bot voice messages (OGG/Opus) convert with ffmpeg. No existing user account/session is accessed. Browser recordings/audio uploads already work without Telegram. Users transcribe, review/edit the text and confirm it before creating a ticket. Every audio format is decoded locally and rejected if longer than2minutes; no silent truncation.

## Deploy / backup

Backend isolated Azure resources: group `rg-awaazsetu`, plan `awaazsetu-free` F1/Free, app `awaazsetu-hkp-2026`. Existing Hermes/n8n resources were not changed. Settings are applied through a permission600 temporary file which the deploy script deletes. Zip contains only backend, geodata, compiled frontend and dependencies; no local secrets/database. Runtime database is `/home/awaazsetu/awaazsetu.db`.

```sh
npm --prefix frontend run build
.venv/bin/python scripts/deploy_azure.py
cd frontend && vercel deploy --prod --yes
```

Verify health, login, intake and tracking after every deployment. Vercel static UI forwards same-origin `/api` requests to Azure. Azure also serves the built UI directly.

Local backup: `.venv/bin/python scripts/backup.py` uses SQLite's online backup API and writes a timestamped private copy in `work/backups/`. For hosted backup use an authenticated App Service SSH session and SQLite backup on `/home/awaazsetu/awaazsetu.db`; download it securely. No scheduled remote backup is configured. Preserve `CONTACT_ENCRYPTION_KEY` and `CONTACT_HASH_SECRET` with the backup; losing them breaks contact decryption/identity. Existing secrets must survive redeployments. Do not rotate encryption key without a migration. Rotate admin password/JWT secret to invalidate sessions as needed.

The API key was supplied in chat; replace it in private `.env` and Azure settings when convenient. Never commit it. Daily cap is request reservations, not an exact rupee cap. Free Azure may sleep/stop at quota and may cold-start slowly. Do not rely on it for emergency service.

## PostgreSQL / PostGIS

Use `DATABASE_URL=postgresql+psycopg://user:password@host/db`; deploy with one worker until database-level claims/locks replace process locks. First startup creates tables. Run `scripts/init_postgis.sql` after table creation if spatial indices are wanted. This version still calculates distances in Python. PostgreSQL is configurable but not live-tested in this run; the deployed path is persistent SQLite.

## Map background tiles

The dashboard uses Leaflet with the standard `https://tile.openstreetmap.org/{z}/{x}/{y}.png` endpoint and visible OSM attribution. Tile images explicitly use `referrerPolicy="strict-origin"`: OSM receives the site origin for identification, without report paths or tracking tokens. The rest of the site retains `no-referrer`. Do not strip this tile referrer, bypass browser caching, prefetch regions, or repeatedly pan automated browsers. UI contract tests mock tiles.

OSM's community service is best-effort, without an SLA. A 403 background tile is a provider rejection, not lost incident data. For an operational deployment, configure a supported commercial map service; Google Maps requires its own integration, restricted API key and billing. Map-provider changes do not change stored incident coordinates or fix an uncertain report location.
