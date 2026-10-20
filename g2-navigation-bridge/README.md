# G2 Navigation bridge

Takes a navigation request ("take me to Tim Bond Dental"), resolves it with Google Maps
Platform, and hands it to the Even Realities G2 glasses. Exposed two ways:

- **MCP tool** `navigate_to_g2` (stdio), for Claude Code / Claude Desktop / Hermes
- **HTTP endpoint** `POST /navigate_to_g2`, for anything else (Shortcuts, Hermes jobs, curl)

```
request ─▶ validate (zod) ─▶ Google Places text search ─┬─▶ Google Routes ─▶ Google Maps link ─▶ G2 adapter ─▶ response
                              (Geocoding as fallback)    └ (skipped if no origin)                 mock | webhook | deep_link
```

> **The G2 side is a mock for now.** Even Realities publishes no API, webhook or
> deep-link scheme for the G2's built-in Navigation (checked October 2026 against
> [hub.evenrealities.com/docs](https://hub.evenrealities.com/docs)). Their only
> third-party surface is Even Hub plugins: web apps that run inside the Even app on the
> phone. So the bridge ships with a clearly marked mock adapter, plus ready-to-configure
> `webhook` and `deep_link` modes. See [Completing the G2 integration](#completing-the-g2-integration).

## Setup

Requires Node 20+.

```bash
cd g2-navigation-bridge
npm install
cp .env.example .env      # then fill in GOOGLE_MAPS_API_KEY
npm test
npm run build
```

### Google Cloud

1. In a Google Cloud project with billing enabled, enable **Places API (New)**, **Routes API**
   and **Geocoding API**.
2. Create an API key under *APIs & Services → Credentials*.
3. Restrict the key: *API restrictions* → those three APIs only. Add an IP restriction too if
   the bridge runs on a fixed IP.

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GOOGLE_MAPS_API_KEY` | yes | | Google Maps Platform key |
| `GOOGLE_REGION` | | `uk` | Region bias for search and routing |
| `GOOGLE_LANGUAGE` | | `en-GB` | Language of addresses and route text |
| `GOOGLE_UNITS` | | `IMPERIAL` | `IMPERIAL` (miles) or `METRIC` |
| `GOOGLE_LOCATION_BIAS` | | | `lat,lng` to bias place search, e.g. Rugby `52.3709,-1.2650` |
| `GOOGLE_LOCATION_BIAS_RADIUS_M` | | `30000` | Bias radius in metres (max 50000) |
| `DEFAULT_ORIGIN` | | | Used when origin is missing or "current location" |
| `G2_MODE` | | `mock` | `mock`, `webhook` or `deep_link` |
| `G2_NAVIGATION_API_URL` | webhook | | Where to POST. Must be https unless localhost |
| `G2_NAVIGATION_API_TOKEN` | | | Sent as `Authorization: Bearer …` to the webhook |
| `G2_REQUEST_TIMEOUT_MS` | | `10000` | Per-attempt timeout for the webhook |
| `G2_DEEP_LINK_TEMPLATE` | deep_link | | e.g. `scheme://nav?lat={lat}&lng={lng}&name={name}` |
| `HOST` / `PORT` | | `127.0.0.1` / `3000` | HTTP bind address |
| `BRIDGE_API_TOKEN` | if HOST isn't loopback | | Bearer token callers must send |
| `RETRY_MAX_ATTEMPTS` | | `4` | Attempts for 429 / 5xx / network errors |
| `RETRY_BASE_DELAY_MS` / `RETRY_MAX_DELAY_MS` | | `300` / `5000` | Backoff bounds |
| `LOG_LEVEL` | | `info` | pino level |

Deep-link placeholders: `{lat}` `{lng}` `{name}` `{address}` `{place_id}` `{mode}`
`{google_maps_link}`. Values are URL-encoded. An unknown placeholder is an error.

## Running

```bash
npm run dev           # HTTP server with reload (tsx)
npm start             # HTTP server from dist/
npm run start:mcp     # MCP stdio server from dist/ (normally Claude Code starts this)
```

## Claude Code MCP configuration

Build first (`npm run build`), then register the server. Secrets stay in `.env`: the MCP
entry point loads `g2-navigation-bridge/.env` itself, so nothing goes in Claude's config.

```bash
claude mcp add g2-navigation -- node /absolute/path/to/g2-navigation-bridge/dist/mcp.js
```

Or in a project's `.mcp.json`:

```json
{
  "mcpServers": {
    "g2-navigation": {
      "command": "node",
      "args": ["/absolute/path/to/g2-navigation-bridge/dist/mcp.js"]
    }
  }
}
```

Check with `claude mcp list`, then in Claude Code: *"Navigate to Tim Bond Dental from my
current location."* Claude calls `navigate_to_g2` with
`{"destination":"Tim Bond Dental","origin":"current location"}`.

This bridge calls Google Maps Platform directly rather than going through your Google Maps
MCP server: one MCP server can't call another, and calling the APIs directly lets the bridge
validate every response and handle retries itself. Your Google Maps MCP server stays
useful for browsing places in Claude. Both can share the same key.

## HTTP API

### `POST /navigate_to_g2`

```json
{
  "destination": "string, required",
  "origin": "string, optional: address, \"lat,lng\" or \"current location\"",
  "travel_mode": "driving | walking | cycling | transit (default driving)",
  "avoid_tolls": false,
  "avoid_highways": false,
  "notes": "string, optional"
}
```

Status codes: `200` for success (`sent` / `link_created`), `400` for invalid input, `401` for a bad token,
`404` when the destination isn't found, `502` when Google or G2 rejects the request, `503` when an upstream is still down after retries.

### `GET /healthz`

`{"ok":true,"g2_mode":"mock"}`

## Example: "Navigate to Tim Bond Dental from my current location"

```bash
npm start &
./examples/tim-bond-dental.sh
```

which sends [`examples/tim-bond-dental.json`](examples/tim-bond-dental.json):

```bash
curl -s -X POST http://127.0.0.1:3000/navigate_to_g2 \
  -H 'Content-Type: application/json' \
  -d '{"destination":"Tim Bond Dental","origin":"current location","travel_mode":"driving"}'
```

The response looks like this in mock mode. Coordinates and IDs below are illustrative;
yours come from Google:

```json
{
  "status": "link_created",
  "destination": "Tim Bond Dental",
  "coordinates": { "lat": 52.3712, "lng": -1.2614 },
  "distance_text": null,
  "duration_text": null,
  "g2_response": "[MOCK] G2 Navigation is not connected, so nothing was sent to the glasses. Open google_maps_link on your phone. ...",
  "g2_deep_link": null,
  "google_maps_link": "https://www.google.com/maps/dir/?api=1&destination=Tim+Bond+Dental&destination_place_id=ChIJ...&travelmode=driving",
  "address": "..., Rugby ..., UK",
  "place_id": "ChIJ...",
  "travel_mode": "driving",
  "origin_used": "current location (device)",
  "g2_mode": "mock",
  "warnings": ["No origin known for \"current location\", so distance and duration were not calculated. ..."],
  "g2_payload": { "type": "navigation.request", "...": "the payload webhook mode would send" }
}
```

**About "current location":** the bridge runs on a server, so it doesn't know where your
phone is. It handles this three ways:

1. **No origin (the default):** the Google Maps link leaves origin out, so it opens from your
   phone's live location. Distance and duration come back `null` with a warning.
2. **A GPS fix:** send `"origin": "52.3478,-1.5803"` (an iOS Shortcut can supply *Current
   Location*). You get distance, duration and a polyline. Try
   `ORIGIN="52.3478,-1.5803" ./examples/tim-bond-dental.sh`.
3. **`DEFAULT_ORIGIN`:** a fixed fallback, such as your home address.

If "Tim Bond Dental" resolves to the wrong place, make the destination more specific
("Rugby Smiles, Rugby") or set `GOOGLE_LOCATION_BIAS`.

## Completing the G2 integration

All G2-specific code is in [`src/adapters/g2-navigation.adapter.ts`](src/adapters/g2-navigation.adapter.ts).
Nothing else needs to change. To finish it, I need **one** of these:

1. **A G2 HTTP receiver.** If you build an Even Hub plugin with a backend, or a relay on
   the Mac mini next to even-terminal, give me:
   - the endpoint URL → `G2_NAVIGATION_API_URL`
   - how it authenticates (bearer token, HMAC signature, mTLS) → `G2_NAVIGATION_API_TOKEN` (and a code change if it isn't bearer)
   - the request body it expects. Until then `mapToG2Payload()` sends the provisional shape below
   - what a success response looks like, and its error codes
2. **A deep-link / URL scheme** that the Even app (or a plugin) opens with a destination:
   the scheme, the parameter names, and whether it wants coordinates, an address or a
   place ID → `G2_DEEP_LINK_TEMPLATE`.
3. **Even Realities documentation or SDK access** that covers the built-in Navigation
   feature, if they have shared any with you privately.

Provisional webhook payload (`G2_MODE=webhook`):

```json
{
  "type": "navigation.request",
  "version": 1,
  "request_id": "uuid (also sent as the Idempotency-Key header)",
  "requested_at": "2026-10-20T08:00:00.000Z",
  "destination": { "name": "Tim Bond Dental", "address": "...", "lat": 52.37, "lng": -1.26, "place_id": "ChIJ..." },
  "route": { "mode": "driving", "distance_m": 24300, "duration_s": 1560, "distance_text": "15.1 mi", "duration_text": "26 mins", "polyline": "encoded" },
  "links": { "google_maps": "https://www.google.com/maps/dir/?api=1&..." },
  "display": { "lines": ["To: Tim Bond Dental", "15.1 mi · 26 mins (driving)"] },
  "notes": null
}
```

`display.lines` is kept to 32 characters per line for the G2's 576×288 monochrome display,
so a plugin can render it as-is.

## Security

- Secrets live only in environment variables / `.env` (git-ignored). Config errors name the
  variable, never its value.
- The Google key goes in the `X-Goog-Api-Key` header for Places and Routes. Geocoding only
  accepts it as a query parameter, so request URLs are logged as host + path only.
- Logs never include headers, tokens, keys or upstream bodies. A pino redaction list covers
  anything that slips through, and a test checks it.
- Upstream error bodies (which can echo request details) are never returned to the client.
- Every Google and G2 response is validated with zod before use.
- Retries: 429, 5xx, network errors and timeouts get exponential backoff with jitter, honouring
  `Retry-After`. Other 4xx responses fail fast. Webhook retries reuse one `Idempotency-Key`, so a
  receiver can drop duplicates.
- The HTTP server binds to `127.0.0.1` by default and refuses to bind anywhere else without
  `BRIDGE_API_TOKEN`. The token is compared in constant time. The body limit is 16 KB.
- The webhook URL must be https, except for localhost. Deep-link templates with `javascript:`,
  `data:`, `file:` or `vbscript:` schemes are rejected.

## Tests

```bash
npm test
```

All external APIs are mocked with an injected `fetch`. The tests cover input and config
validation, Google response normalisation (Places, Geocoding, Routes, Maps links), G2 payload
mapping, deep links and webhook delivery, retry and backoff behaviour, secret redaction,
and the HTTP endpoint end to end, including the Tim Bond Dental example.

## Layout

```
src/
  adapters/g2-navigation.adapter.ts   all G2 specifics (mock / webhook / deep_link)
  google/google-maps.client.ts        Places, Geocoding, Routes calls
  google/normalise.ts                 response validation + normalisation, Maps links
  http/retry.ts                       fetch with backoff
  navigate.ts                         the navigate_to_g2 flow
  server.ts / index.ts                Express app / HTTP entry point
  mcp.ts                              MCP stdio entry point
  config.ts  logger.ts  schemas.ts  errors.ts  container.ts
```
