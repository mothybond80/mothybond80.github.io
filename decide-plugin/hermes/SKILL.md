---
name: decide
description: Evidence-to-Decision Engine for Hermes. Use when Tim asks whether something works, is good or bad for him, or wants a decision grounded in scientific evidence. Runs the same decide-engine as the Claude Code /decide plugin.
---

# /decide for Hermes

This skill reuses the Claude Code plugin's engine so there is one scientific
appraisal method, not two. The engine is deterministic Python (no LLM calls);
Hermes supplies the reasoning, following the contract embedded in the pack.

Engine path: `~/.claude/plugins/marketplaces/mothybond80/decide-plugin/bin/decide-engine`
(or wherever the repo is checked out; set `DECIDE_ENGINE` to override).
Runs are written to `~/.decide/<timestamp>/`.

## Modes
`quick` (default), `deep`, `challenge <claim>`.

## Procedure

1. **Neutralise.** `decide-engine parse "<question>" --hide-asker`. Correct the
   PICO if the heuristic failed; use direction-free nouns only.
2. **Search.** `decide-engine search "<question>" --mode quick|deep --out
   ~/.decide/<ts>/pack.json [--exposure .. --outcome .. --population ..]`.
   Check `relevance_tiers.A > 0`.
3. **Appraise in isolation.** Hermes cannot fork a memory-less sub-context, so
   do the strongest available separation: open a *fresh* reasoning pass whose
   only input is the pack file and the `appraiser_contract` inside it. Do not
   read Tim's memories, prior chats or the `pack.asker.json` file during this
   pass. Write `appraisal.json` and `appraisal.md`. If Hermes supports
   delegating to Claude Code (`run_code_task` / the code MCP), prefer
   delegating this step to the Claude Code plugin's `decide:evidence-appraiser`
   agent, which is a genuinely isolated context.
4. **Lock.** `decide-engine lock appraisal.json` → record the hash.
5. **Challenge.** Second fresh pass using the challenger checklist in
   `../agents/evidence-challenger.md`. Write `challenge.md`.
6. **Verify.** `python3 ../skills/decide/scripts/check_refs.py <run>` then
   `decide-engine verify --file <run>/citations.json`. Drop or flag anything
   not verified; report retractions.
7. **Decide.** Only now read `pack.asker.json` and Tim's goals and constraints.
   Follow the decision framework in `../skills/decide/references/methodology.md`
   section 6. Keep scientific conclusion, assumptions and values separate.
8. **Report** using `../skills/decide/references/report-templates.md`. Medical
   topics: state when clinical supervision is needed.

## Limitation to state in every Hermes report
Hermes runs in one memory-bearing context. The appraisal pass is instructed to
ignore memory but cannot be proven to; the Claude Code route is isolated by
construction. If the answer matters, re-run with `/decide` in Claude Code.
