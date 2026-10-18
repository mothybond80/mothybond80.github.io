# Claude Memory MCP server

Gives Claude a persistent memory and a skill library that work the way
[Hermes Agent](https://github.com/NousResearch/hermes-agent)'s do. It is shared by every
place Claude connects to it from: Claude Code, Claude Desktop, claude.ai and the Claude
mobile apps.

- **Memory** is two small Markdown files that Claude curates itself. Claude loads them at
  the start of every conversation and keeps them up to date as it learns.
- **Skills** are procedures Claude writes down after finishing a complex task. It follows
  them next time and improves them whenever they turn out wrong or incomplete. Every
  earlier version is kept.

Everything is plain files on your own machine. Nothing is sent anywhere else.

## What is stored

```
~/.claude-memory/
├── USER.md                 who you are: preferences, style, role, people      (2,500 chars)
├── MEMORY.md               Claude's notes: setup, conventions, lessons        (5,000 chars)
├── skills/
│   ├── <name>/SKILL.md     one procedure, in Claude Code's SKILL.md format
│   ├── <name>/.history/    the last 10 versions, for rollback
│   ├── <name>/.stats.json  use count and last use
│   └── .archive/           retired skills, restorable
└── log.jsonl               every change, with the old text, so nothing is lost
```

Entries in the two memory files are separated by a line containing only `§`, the same
format Hermes uses. You can open and edit any of these files by hand.

## Tools

| Tool | What it does |
|---|---|
| `memory_view` | Loads the memory and the skill list. Claude calls it at the start of each conversation |
| `memory_add` | Saves one fact to `user` or `memory` |
| `memory_replace` | Rewrites or merges an entry, found by a short unique piece of its text |
| `memory_remove` | Deletes an entry |
| `skill_list` | Lists skills with version, use count and status (active, stale or archived) |
| `skill_view` | Opens a skill before doing its task, and records the use |
| `skill_create` | Saves a new procedure |
| `skill_update` | Improves a skill by a targeted edit or a full rewrite. Keeps the old version |
| `skill_rollback` | Restores an earlier version as the newest one |
| `skill_archive` / `skill_restore` | Retires a skill or brings it back |

The server sends Claude instructions on connect telling it when to save, how to keep
entries short, when to turn work into a skill and when to fix one.

### Safeguards

- **Caps.** When a memory file is full the write is refused and Claude is shown the
  current entries so it can merge or drop some first, the same as Hermes.
- **No secrets.** Writes that look like passwords, API keys, tokens or private keys are
  refused, as is text with invisible Unicode or prompt-injection phrasing.
- **No patient data.** The instructions tell Claude never to store patient-identifiable or
  clinical information.
- **Duplicates** are ignored, and an ambiguous edit is refused rather than guessed.
- **Safe writes.** Writes are atomic and locked, so several Claude sessions can share the
  store. Files are readable only by your user.
- **Skills older than 30 days** without use or change are flagged as stale in the list.

## Install

Requires Python 3.11 or newer. With [uv](https://docs.astral.sh/uv/):

```bash
cd claude-memory-mcp
uv venv
uv pip install -e .
```

## Connect it

### Through the Mac mini gateway (claude.ai, mobile apps and Claude Code cloud sessions)

The gateway runs each MCP server as a stdio process behind its OAuth sign-in, so this
server needs no extra auth there.

1. Add an entry to `SERVERS` in `~/.config/hermes/gateway/launch-servers.py`:

   ```python
   "claude-memory": f'{HOME}/claude-memory-site/claude-memory-mcp/.venv/bin/python {HOME}/claude-memory-site/claude-memory-mcp/server.py',
   ```

2. Add a `handle_path /claude-memory/*` block to `Caddyfile.template`, copied from the
   withings block. Edit the template, not `Caddyfile.rendered`.
3. Leave it out of `RO_PATHS` in `oauth-server.py`. Memory needs write access.
4. Restart the servers and Caddy agents with `launchctl kickstart -k`.
5. In claude.ai, go to **Customize → Connectors → Add custom connector**. Name it
   *Claude memory* and use this URL:

   ```
   https://mac-mini-cowork.taila4414e.ts.net/claude-memory/mcp
   ```

   Sign in with the **read-write** passphrase. The connector then appears in the mobile
   apps and in Claude Code cloud sessions too.

### Claude Code on the same machine

```bash
claude mcp add --scope user claude-memory -- /path/to/claude-memory-mcp/.venv/bin/python /path/to/claude-memory-mcp/server.py
```

To have the memory loaded automatically at the start of every session, add a SessionStart
hook to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command",
        "command": "/path/to/claude-memory-mcp/.venv/bin/python /path/to/claude-memory-mcp/server.py snapshot" } ] }
    ]
  }
}
```

Skills use Claude Code's own `SKILL.md` format. To make Claude Code also discover them as
native skills, symlink `~/.claude-memory/skills` to `~/.claude/skills`.

### Standalone HTTP server

To run it as a Streamable HTTP server instead:

```bash
CLAUDE_MEMORY_TOKEN=<long random string> python server.py serve --port 8765
```

It serves MCP at `/mcp` and an open `/health`. Every other request needs
`Authorization: Bearer <token>`. When running behind a proxy, list the public hostname in
`CLAUDE_MEMORY_ALLOWED_HOSTS`.

## Make Claude use it everywhere

The server's instructions ask Claude to load memory first. To make sure it happens in every
claude.ai and mobile chat, add this to **Settings → Profile → personal preferences**:

```
At the start of every conversation, call memory_view from the Claude memory connector and treat it as what you already know about me. Save durable facts, preferences and corrections there, and turn complex workflows into skills.
```

Turn off claude.ai's built-in memory under **Settings → Capabilities** if you want this to
be the only memory. Otherwise Claude tends to rely on the built-in one.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `CLAUDE_MEMORY_DIR` | `~/.claude-memory` | Where everything is stored |
| `CLAUDE_MEMORY_LIMIT` | `5000` | `MEMORY.md` character cap |
| `CLAUDE_MEMORY_USER_LIMIT` | `2500` | `USER.md` character cap |
| `CLAUDE_MEMORY_TOKEN` | unset | HTTP mode: required bearer token |
| `CLAUDE_MEMORY_ALLOWED_HOSTS` | unset | HTTP mode: extra accepted `Host` headers, comma-separated |

## Tests

```bash
uv pip install -e ".[test]"
pytest
```

The tests run offline against a temporary folder and never touch `~/.claude-memory`.
