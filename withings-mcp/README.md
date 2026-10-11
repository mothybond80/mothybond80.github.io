# Withings MCP server

A small [Model Context Protocol](https://modelcontextprotocol.io) server that gives Claude
read access to a Withings account: weight and body composition, blood pressure, sleep,
daily activity, workouts, ECG recordings, devices and goals.

It talks to the Withings Public Health Data API over OAuth2, stores tokens locally and
refreshes them automatically. Runs over stdio, so it works with Claude Desktop, Claude Code
and any other MCP client.

## Tools

| Tool | What it returns |
|---|---|
| `withings_auth_status` | Whether the server is connected and when the token expires |
| `withings_get_auth_url` | Link to approve access (step 1 of connecting) |
| `withings_exchange_code` | Finish connecting with the code from the callback page (step 2) |
| `withings_revoke_token` | Delete the stored tokens |
| `withings_get_body_measurements` | Weigh-ins with weight, fat, muscle, bone, water, visceral fat, BMR |
| `withings_get_latest_measurements` | Most recent value of every measurement type on the account |
| `withings_get_blood_pressure` | BP and heart rate readings with period averages |
| `withings_get_sleep_summary` | Nightly sleep score, stages, heart and breathing rate, wake-ups, snoring |
| `withings_get_sleep_details` | Stage-by-stage timeline for one night |
| `withings_get_activity` | Daily steps, distance, calories, active minutes, HR zones |
| `withings_get_workouts` | Recorded workouts with duration, calories, distance, HR |
| `withings_get_ecg_recordings` | ECG recordings with AFib classification |
| `withings_get_ecg_signal` | Raw waveform for one ECG recording |
| `withings_get_devices` | Linked devices with battery and last sync |
| `withings_get_goals` | Step, sleep and weight goals |

All date arguments are `YYYY-MM-DD`. Most tools take `start_date`, `end_date` and `days`
and default to a recent window ending today.

## 1. Register an app with Withings

1. Sign in at <https://developer.withings.com> and open the Developer Dashboard.
2. Create a new application of type **Public API integration**.
3. Set the **Callback URL** to:

   ```
   https://mothybond80.github.io/withings-mcp/callback.html
   ```

   This is the static page in this folder. After you approve access, Withings redirects
   there and the page shows the authorisation code for you to copy. No data passes through
   the page beyond that code, which is only valid for about 30 seconds.

4. Note the **Client ID** and **Client Secret**.

## 2. Install

Requires Python 3.11 or newer. With [uv](https://docs.astral.sh/uv/):

```bash
cd withings-mcp
uv venv
uv pip install -e .
```

Or with plain pip:

```bash
cd withings-mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## 3. Connect your account

Export the credentials, then run the one-off login:

```bash
export WITHINGS_CLIENT_ID=...
export WITHINGS_CLIENT_SECRET=...
python server.py auth
```

Open the printed link, approve access, copy the code from the callback page and paste it
back within 30 seconds. Tokens are saved to `~/.config/withings-mcp/tokens.json` with
owner-only permissions.

You can also connect from inside Claude: call `withings_get_auth_url`, open the link,
then call `withings_exchange_code` with the code.

## 4. Add to Claude

### Claude Code

```bash
claude mcp add withings \
  -e WITHINGS_CLIENT_ID=... \
  -e WITHINGS_CLIENT_SECRET=... \
  -- /path/to/withings-mcp/.venv/bin/python /path/to/withings-mcp/server.py
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "withings": {
      "command": "/path/to/withings-mcp/.venv/bin/python",
      "args": ["/path/to/withings-mcp/server.py"],
      "env": {
        "WITHINGS_CLIENT_ID": "...",
        "WITHINGS_CLIENT_SECRET": "..."
      }
    }
  }
}
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `WITHINGS_CLIENT_ID` | required | From the Withings developer dashboard |
| `WITHINGS_CLIENT_SECRET` | required | From the Withings developer dashboard |
| `WITHINGS_REDIRECT_URI` | the callback page above | Must match the URL registered with Withings exactly |
| `WITHINGS_TOKEN_FILE` | `~/.config/withings-mcp/tokens.json` | Where tokens are stored |

## Notes

- Withings access tokens last 3 hours. The server refreshes them a minute early and
  retries once on an authentication failure. Refresh tokens rotate on every use, so the
  token file is rewritten each time.
- The standard tier is limited to 120 requests per minute. The server pages through
  large result sets, capped at 20 pages per call.
- Measurement values are decoded from Withings' `value × 10^unit` encoding and labelled
  with units. Durations are returned in seconds with a readable `1h23m` alongside.
- Sleep Analyzer data is available in the UK and EU. Activity data needs a Withings tracker
  or a linked phone health app.
- Disconnect fully by calling `withings_revoke_token` and then removing the app under
  Connected apps in the Withings app.

## Tests

```bash
uv pip install -e ".[test]"
pytest
```

The tests use a fake HTTP transport, so they run offline and never touch Withings.
