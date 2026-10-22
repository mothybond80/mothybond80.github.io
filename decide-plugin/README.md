# decide — Evidence-to-Decision Engine for Claude Code and Hermes

`/decide quick|deep|challenge <question>` turns a possibly leading question
into a neutral research question, searches PubMed, OpenAlex, Crossref and
Europe PMC with a direction-free strategy, has an **isolated** agent appraise
the evidence (GRADE-style, per outcome), has a second isolated agent try to
falsify that appraisal, verifies every citation against the source databases
(including retraction status), locks the scientific verdict, and only then
applies your goals, constraints and risk tolerance to reach a decision.

It can conclude any of: strongly supports / suggests with uncertainty / mixed
/ insufficient / contradicts / more information required / the most reasonable
decision is to do nothing.

No paid services. No third-party Python dependencies. No LLM calls inside the
engine.

## Layout

```
decide-plugin/
  .claude-plugin/plugin.json      plugin manifest
  skills/decide/SKILL.md          /decide orchestrator (quick | deep | challenge)
  skills/decide/references/       methodology, report templates, known limitations
  skills/decide/scripts/check_refs.py
  agents/evidence-appraiser.md    isolated appraisal agent
  agents/evidence-challenger.md   isolated adversarial agent
  bin/decide-engine               launcher (no install needed)
  engine/decide_engine/           the deterministic engine (stdlib only)
  engine/mcp_server.py            optional MCP wrapper (needs `mcp`)
  engine/tests/                   unit tests, framing harness, recorded fixtures
  hermes/                         Hermes skill + integration notes
  docs/                           ARCHITECTURE, EVALUATION, TESTING, LIMITATIONS
```

## Install in Claude Code

From the repository root (this repo is also a plugin marketplace):

```
/plugin marketplace add mothybond80/mothybond80.github.io
/plugin install decide@mothybond80
```

or for local development: `claude --plugin-dir /path/to/decide-plugin`.

Requirements: python3 >= 3.9 on PATH (the Mac mini system Python 3.9.6 works); outbound HTTPS to
`eutils.ncbi.nlm.nih.gov`, `api.openalex.org`, `api.crossref.org`,
`www.ebi.ac.uk` (and `api.scite.ai` for deep mode). Set `DECIDE_MAILTO` to a
contact address so OpenAlex and Crossref put you in their polite pools.
Optional: `NCBI_API_KEY`, `OPENALEX_API_KEY` (free) for higher rate limits.

## Use

```
/decide quick Does creatine improve cognitive performance?
/decide deep  Isn't red meat actually good for longevity?
/decide challenge "Cold plunges reduce ADHD symptoms"
```

Each run writes an auditable directory (`.decide/<timestamp>/` in the
project, or `~/.decide/`) containing `pack.json` (everything the appraiser
saw), `pack.asker.json` (your framing, sealed until the decision step),
`appraisal.*`, `challenge.md`, `citations.json` with verification verdicts,
`verdict.md` and `lock.json` with SHA-256 hashes.

## Engine CLI (shared by Claude Code and Hermes)

```
bin/decide-engine parse  "question" --hide-asker
bin/decide-engine plan   "question" --mode quick|deep
bin/decide-engine search "question" --mode quick|deep --out pack.json [--exposure X --outcome Y --population P]
bin/decide-engine verify --doi 10.1093/nutrit/nuac064 --title "..." --year 2023 --author Prokopidis
bin/decide-engine verify --file citations.json
bin/decide-engine lock   pack.json
bin/decide-engine cache-put URL body.json     # feed a response fetched elsewhere
bin/decide-engine --offline search ...        # never touch the network
```

Exit codes: `search` 0 ok, 3 essential URLs blocked (see `missing_urls`);
`verify` 0 all verified, 2 at least one not verified (retracted, not_found,
title_mismatch), 3 at least one unverifiable offline. Tested on Python 3.9,
3.11, 3.13 and 3.14.

## Hermes

See `hermes/README.md`: Route A (Hermes skill calling the same CLI, zero
install), Route B (MCP server), Route C (delegate to Claude Code's isolated
agents through the existing code-task bridge).

## Tests

```
cd engine && uv venv && uv pip install pytest && .venv/bin/python -m pytest -q
.venv/bin/python tests/framing_harness.py --packs --offline --cache-dir tests/fixtures/cache
```
See `docs/TESTING.md` for what the tests show and do not show.

## Honesty clauses

The output is a *structured evidence appraisal*, not a systematic review.
Screening is from abstracts by a model. Searches are bounded. Read
`skills/decide/references/known-limitations.md` before relying on a result,
and for medical questions treat the report as preparation for a conversation
with a clinician, not a substitute for one.
