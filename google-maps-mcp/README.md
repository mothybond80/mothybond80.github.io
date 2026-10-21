# Google Maps MCP server

A small MCP server that gives Claude Google Maps: find a place, geocode an address, get
distance and travel time, and build a link that opens turn-by-turn navigation on the phone.

Runs two ways from the same code:

- **Streamable HTTP** (`npm start`): for a **claude.ai connector**, through the Mac mini gateway
- **stdio** (`npm run start:mcp`): for Claude Code / Claude Desktop

## Tools

| Tool | What it does |
|---|---|
| `find_place` | Search for a business, landmark or address. Returns name, address, coordinates, place ID, rating, phone, website, open-now and a Google Maps link. Biased to the configured area. |
| `geocode` | Address or postcode → coordinates, or `lat,lng` → address. |
| `get_directions` | Distance and time from an origin to a destination by driving, walking, cycling or transit, plus a navigation link. |
| `navigation_link` | A Google Maps directions link only. No API call, no cost. |

"Current location" handling: the server runs on the Mac mini, so it can't see where your
phone is. `get_directions` with no origin uses `DEFAULT_ORIGIN` for the distance/time (or
skips them if unset) and always leaves the origin out of the link, so the phone starts
navigation from wherever it is. Pass `origin` as `lat,lng` (an iOS Shortcut can supply this)
for an exact answer.

## Setup

Requires Node 20+.

```bash
cd google-maps-mcp
npm install
cp .env.example .env      # then fill in GOOGLE_MAPS_API_KEY and MCP_AUTH_TOKEN
npm test
npm run build
```

### Google Cloud

1. In a Google Cloud project with billing enabled, enable **Places API (New)**, **Routes API**
   and **Geocoding API**.
2. Create an API key under *APIs & Services → Credentials*.
3. Restrict the key: *API restrictions* → those three APIs only.

Personal use stays inside Google's monthly free allowance. Set a budget alert in Cloud
Billing anyway.

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GOOGLE_MAPS_API_KEY` | yes | | Google Maps Platform key |
| `GOOGLE_REGION` | | `uk` | Region bias for search and routing |
| `GOOGLE_LANGUAGE` | | `en-GB` | Language of addresses and route text |
| `GOOGLE_UNITS` | | `IMPERIAL` | `IMPERIAL` (miles) or `METRIC` |
| `GOOGLE_LOCATION_BIAS` | | | `lat,lng` to bias place search, e.g. Rugby `52.3709,-1.2650` |
| `GOOGLE_LOCATION_BIAS_RADIUS_M` | | `30000` | Bias radius in metres (max 50000) |
| `DEFAULT_ORIGIN` | | | Used by `get_directions` when no origin is given |
| `HOST` / `PORT` | | `127.0.0.1` / `3460` | HTTP bind address |
| `MCP_AUTH_TOKEN` | if HOST isn't loopback | | Bearer token clients must send. `openssl rand -hex 32` |
| `RETRY_MAX_ATTEMPTS` | | `4` | Attempts for 429 / 5xx / network errors |
| `RETRY_BASE_DELAY_MS` / `RETRY_MAX_DELAY_MS` | | `300` / `5000` | Backoff bounds |
| `LOG_LEVEL` | | `info` | pino level |

## claude.ai connector (via the Mac mini gateway)

The gateway on the Mac mini is: Tailscale funnel → Caddy (`127.0.0.1:7777`) → `mcp-proxy`
aggregator (`127.0.0.1:7810`) → one **stdio** MCP subprocess per server. Auth is enforced by
Caddy (gateway keys + forward-auth), not inside each server. So the connector uses the
**stdio** entry point, `dist/mcp.js`; the Streamable HTTP server is only for running it
somewhere without that gateway.

1. Build: `npm run build`.
2. Key: put `GOOGLE_MAPS_API_KEY=...` in `~/.hermes/.env` (the gateway merges it into every
   server's environment). The project's own `.env` also works; it is read by `dist/mcp.js`.
3. Register the server. In `~/.config/hermes/gateway/launch-servers.py`, add to `SERVERS`:

   ```python
   "google-maps": "node /Users/timbondlocalserver/withings-site/google-maps-mcp/dist/mcp.js",
   ```

   In `~/.config/hermes/gateway/Caddyfile.template`, add before the fallback `handle`, mirroring
   the `claude-memory` block (same auth posture):

   ```
   handle_path /google-maps/* {
       rewrite * /servers/google-maps{uri}
       reverse_proxy 127.0.0.1:7810
   }
   ```

4. Reload only the two gateway agents (never `tailscale serve reset`):

   ```bash
   launchctl kickstart -k gui/$(id -u)/com.timbond.mcp-gateway-servers
   launchctl kickstart -k gui/$(id -u)/com.timbond.mcp-gateway-caddy
   curl -I https://mac-mini-cowork.taila4414e.ts.net/google-maps/mcp   # non-404 proves routing
   ```

5. In claude.ai: **Settings → Connectors → Add custom connector**, name `Google Maps`, URL
   `https://mac-mini-cowork.taila4414e.ts.net/google-maps/mcp`, same auth as the other
   Mac mini connectors.

6. Test in a chat: *"Find Rugby Smiles and tell me how long it takes to drive there from Kenilworth."*

### Standalone Streamable HTTP (no gateway)

```bash
npm start                    # 127.0.0.1:3460, POST /mcp (and /), GET /healthz
```

Set `MCP_AUTH_TOKEN` and put it behind TLS before exposing it anywhere.

## Claude Code

Build first, then register the stdio server. It loads `.env` itself, so nothing goes in
Claude's config.

```bash
claude mcp add google-maps -- node /absolute/path/to/google-maps-mcp/dist/mcp.js
```

Or in a project's `.mcp.json`:

```json
{
  "mcpServers": {
    "google-maps": {
      "command": "node",
      "args": ["/absolute/path/to/google-maps-mcp/dist/mcp.js"]
    }
  }
}
```

## Example calls

`get_directions`:

```json
{ "destination": "Rugby Smiles, Rugby", "origin": "Kenilworth", "travel_mode": "driving" }
```

→

```json
{
  "destination": { "name": "Rugby Smiles", "address": "...", "coordinates": { "lat": 52.37, "lng": -1.26 }, "place_id": "ChIJ...", "...": "..." },
  "origin_used": "Kenilworth",
  "travel_mode": "driving",
  "distance_text": "15.1 mi",
  "duration_text": "26 mins",
  "distance_meters": 24300,
  "duration_seconds": 1560,
  "google_maps_link": "https://www.google.com/maps/dir/?api=1&origin=Kenilworth&destination=Rugby+Smiles&destination_place_id=ChIJ...&travelmode=driving"
}
```

`find_place` with `{ "query": "Rugby Smiles" }` returns up to `max_results` places, each
with `name`, `address`, `coordinates`, `place_id`, `type`, `rating`, `rating_count`, `phone`,
`website`, `open_now` and `google_maps_link`.

## Security

- Secrets live only in environment variables / `.env` (git-ignored). Config errors name the
  variable, never its value.
- The Google key goes in the `X-Goog-Api-Key` header for Places and Routes. Geocoding only
  accepts it as a query parameter, so request URLs are logged as host + path only.
- Logs never include headers, tokens, keys or upstream bodies. A pino redaction list covers
  anything that slips through, and a test checks it.
- Upstream error bodies (which can echo request details) are never returned to the client.
- Every Google response is validated with zod before use.
- Retries: 429, 5xx, network errors and timeouts get exponential backoff with jitter, honouring
  `Retry-After`. Other 4xx responses fail fast.
- The HTTP server binds to `127.0.0.1` by default and refuses to bind anywhere else without
  `MCP_AUTH_TOKEN`. The token is compared in constant time. Stateless transport: no session
  table. Body limit 64 KB.

## Tests

```bash
npm test
```

All Google calls are mocked with an injected `fetch`. The tests cover input and config
validation, Google response normalisation (Places, Geocoding, Routes, Maps links), each tool,
retry and backoff behaviour, secret redaction, and the Streamable HTTP endpoint end to end
over JSON-RPC (initialize, tools/list, tools/call, bearer auth).

## Layout

```
src/
  tools.ts                            the four tools + MCP registration
  http.ts                             Streamable HTTP entry point (claude.ai connector)
  mcp.ts                              stdio entry point (Claude Code)
  google/google-maps.client.ts        Places, Geocoding, Routes calls
  google/normalise.ts                 response validation + normalisation, Maps links
  http/retry.ts                       fetch with backoff
  config.ts  logger.ts  schemas.ts  errors.ts
```
