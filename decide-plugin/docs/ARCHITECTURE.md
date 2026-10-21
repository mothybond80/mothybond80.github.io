# Architecture

```
user question ("Isn't X actually good for Y?")
        |
        v
+---------------------------+      asker block (direction, raw wording)
| 1. Neutraliser (engine)   |----> pack.asker.json   [sealed until step 8]
|   strip rhetoric/negation |
|   PICO, domain, hash      |
+---------------------------+
        | neutral question + direction-free strategy
        v
+---------------------------+   PubMed E-utilities, OpenAlex, Crossref,
| 2. Searcher (engine)      |-> Europe PMC, (Scite tallies, deep)   free, keyless
|   deterministic, cached   |   every request logged; cache keyed by URL sha256
|   dedupe, classify,       |
|   relevance tiers,        |
|   retraction flags,       |
|   reference overlap       |
+---------------------------+
        | pack.json  (no asker info)  --> pack_hash
        v
+---------------------------+   isolated agent: no conversation, no memory,
| 3. Appraiser (agent)      |   no CLAUDE.md, no web tools
|   GRADE per outcome,      |-> appraisal.json / appraisal.md
|   contradictions, overlap |
+---------------------------+
        v  lock (sha256 of pack + appraisal)
+---------------------------+   isolated agent, may run extra engine searches
| 4. Challenger (agent)     |-> challenge.md  (challenge_outcome)
|   10 falsification checks |
+---------------------------+
        v
+---------------------------+   check_refs.py + decide-engine verify
| 5. Verifier (engine)      |-> citations.json verdicts; retractions
+---------------------------+
        v  verdict.md (locked)
+---------------------------+   NOW reads pack.asker.json + user goals,
| 6. Decision (orchestrator)|   constraints, risk tolerance
|   E2D framework           |-> report (scientific | assumptions | values)
+---------------------------+
```

## Components

| Path | Role | Runs where |
|---|---|---|
| `engine/decide_engine/` | stdlib-only Python: question, sources, fetch, classify, verify, overlap, pack, cli | anywhere with python3 >= 3.11 |
| `bin/decide-engine` | launcher (`python3 -I`, no install) | Claude Code (plugin bin/ on PATH), Hermes terminal |
| `skills/decide/SKILL.md` | orchestrator: `/decide quick|deep|challenge` | Claude Code main context |
| `agents/evidence-appraiser.md` | isolated appraisal | Claude Code subagent (omitClaudeMd, no web tools, no Agent) |
| `agents/evidence-challenger.md` | adversarial review | Claude Code subagent |
| `skills/decide/scripts/check_refs.py` | R# integrity + citation list | orchestrator |
| `engine/mcp_server.py` | optional MCP exposure of the deterministic layer | Hermes (Route B) |
| `hermes/SKILL.md` | Hermes skill using the same engine | Hermes (Route A) |
| `engine/tests/` | unit tests, framing harness, recorded API fixtures | CI / local |

## Isolation model

Claude Code: the appraiser and challenger are custom subagents. Per the
current sub-agents documentation they do not inherit conversation history,
invoked skills, read files, auto-memory or output style; `omitClaudeMd: true`
removes project/user CLAUDE.md; `tools:` names no MCP tools so connectors
(including the memory connector) are not reachable; `disallowedTools: Agent`
prevents nesting back into a context that has history. They receive a file
path. The pack itself is built by code that never sees the raw question after
parsing, and the parser's output that could reveal framing (direction, raw
text, notes) is written to a separate file the agents are never pointed at.

What cannot be isolated: the orchestrator (main context) has the user's
history and sets PICO overrides. Mitigation: overrides are nouns only, the
engine strips direction words again, the framing hash and pack hash are
printed in the report, and the test suite checks the deterministic layer.

Hermes: a single memory-bearing context. Isolation is by instruction only
(documented as a limitation), or by delegating the appraisal to Claude Code
through the existing code-task bridge.

## Determinism and auditability

- Same cached responses -> byte-identical pack (`pack_hash` excludes only timestamps).
- Every search: database, label, query, DB query translation, hit count, URL.
- Cache directory doubles as test fixtures and as the workaround for
  sandboxes that block the APIs (`decide-engine plan` -> fetch elsewhere ->
  `cache-put` -> `search --offline`).
- Locks: sha256 of pack and appraisal recorded before the decision stage.

## Security posture

- No third-party Python dependencies in the engine; `mcp` only for the optional server.
- Outbound hosts: eutils.ncbi.nlm.nih.gov, api.openalex.org, api.crossref.org,
  www.ebi.ac.uk, api.scite.ai (deep mode), api.semanticscholar.org (off by default).
- Optional keys are read from env, sent only to their own API, redacted from logged URLs.
- No shell execution, no eval, no pickle, no telemetry. XML parsing via `xml.etree` on API responses only.
- The launcher uses `python3 -I` so a planted module in the working directory cannot be imported.
- Agents cannot reach MCP connectors (bank, email, memory, etc.) because their `tools` list excludes them.
