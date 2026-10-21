# Hermes integration

Two supported routes, both using the same engine code as the Claude Code plugin.

## Route A (recommended, zero install): Hermes skill + terminal tool
Copy or symlink `hermes/` to `~/.hermes/skills/decide/` so `SKILL.md` is at
`~/.hermes/skills/decide/SKILL.md`. Hermes calls the engine through its
terminal tool. Requires only python3 >= 3.11 and outbound HTTPS to the four
APIs (PubMed, OpenAlex, Crossref, Europe PMC).

```bash
ln -s "$HOME/.claude/plugins/marketplaces/mothybond80/decide-plugin/hermes" "$HOME/.hermes/skills/decide"
```

## Route B: MCP server
```bash
cd decide-plugin/engine && uv venv && uv pip install -e ".[mcp]"
```
Then add to `~/.hermes/config.yaml` (shape depends on the Hermes version; check
`hermes mcp --help` or the existing `mcp_servers:` block):

```yaml
mcp_servers:
  decide-engine:
    command: /path/to/decide-plugin/engine/.venv/bin/python
    args: ["/path/to/decide-plugin/engine/mcp_server.py"]
    env:
      DECIDE_MAILTO: you@example.org      # polite-pool contact for OpenAlex/Crossref
      DECIDE_RUNS_DIR: /Users/you/.decide
```
Tools: `decide_parse`, `decide_search`, `decide_pack_records`, `decide_verify`,
`decide_lock`. Appraisal and decision reasoning stay with the calling model,
following the pack's `appraiser_contract`.

## Route C: delegate to Claude Code
Hermes already has a `run_code_task` bridge to Claude Code on the Mac mini.
`run_code_task(task="/decide deep <question>", folder=<any folder with the
plugin enabled>)` gives the fully isolated appraiser/challenger agents.

## Credentials
None required. Optional: `NCBI_API_KEY`, `OPENALEX_API_KEY`, `S2_API_KEY`
raise rate limits. Keys are read from the environment and redacted from logs.
Nothing is ever sent to the APIs except the search terms and identifiers.
