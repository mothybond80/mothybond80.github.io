# Testing: what was run, what it showed, what it did not show

Date: 21 Oct 2026. Environment: Claude Code cloud sandbox whose network
policy blocked PubMed, OpenAlex, Crossref and Europe PMC directly; API
responses were fetched through a web proxy, stored in the engine cache
(`engine/tests/fixtures/cache`, gzip) and every engine run below is
reproducible offline from those fixtures. Model-stage runs (appraiser,
challenger) used fresh general-purpose subagents with no conversation history,
instructed from the agent definitions in `agents/`; the plugin's own
`decide:evidence-appraiser` / `decide:evidence-challenger` agents add
`omitClaudeMd` and tool restrictions on top of that.

## 1. Deterministic layer

`cd engine && .venv/bin/python -m pytest -q` -> see the count at the bottom of
this file. Covered: neutraliser, direction detection, PubMed XML parsing
(including retraction markers), classification, sample-size heuristic, dedupe,
erratum handling (regression), reference-list overlap, title similarity,
offline cache behaviour, end-to-end pack determinism and leak checks.

### Framing resistance (`tests/framing_harness.py --packs --offline`)

| subject | framings | distinct framing hashes | distinct strategies | distinct pack hashes | records |
|---|---|---|---|---|---|
| creatine -> cognitive performance | 4 | 1 | 1 | 1 | 97 |
| red meat -> longevity/mortality | 4 | 1 | 1 | 1 | 95 |
| extraversion (men) -> romantic attractiveness | 3 | 1 | 1 | (not fetched) | - |
| income -> subjective well-being | 3 | 1 | 1 | (not fetched) | - |
| cold water immersion -> ADHD symptoms | 3 | 1 | 1 | (not fetched) | - |
| Flow tDCS headset -> depression | 3 | 1 | 1 | (not fetched) | - |
| dietary intervention (adults) -> ADHD symptoms | 3 | 1 | 1 | (not fetched) | - |

All 23 framings of the 7 subjects produce identical direction-free PICO,
identical search strategies and (where packs were built) byte-identical packs.
The asker's direction is recorded in the separate `*.asker.json` and nowhere
in the pack (asserted by `test_pack_contains_no_asker_information`).

**Caveat:** the neutraliser was developed against these 23 framings. This is
regression coverage, not proof of generalisation. New phrasings go through the
orchestrator's PICO override, which is a model step.

### Failure modes found and fixed during testing

1. **Parser notes leaked framing into the pack.** `parser_notes` ("removed
   framing matching isn't...") differed between framings and broke pack-hash
   equality. Moved to the sealed asker file. Caught by the hash test.
2. **Erratum swallowed the article.** Dedupe merged the 2025 corrigendum of
   the Xu 2024 creatine meta-analysis into the article by title similarity
   and the "keep PubMed abstract" rule replaced the real abstract with
   "[This corrects the article...]". The appraiser then reported the key
   2024 meta-analysis as "present only as its erratum". Fixed: ancillary
   types (erratum, comment, letter, editorial, retraction notice) never merge
   by title; abstracts are never replaced by shorter ones. Regression test
   added.
3. **Published criticism was missed by relevance search.** The letter showing
   double counting in the 2023 memory meta-analysis (Eckert & Pascher 2023)
   and two 2026 methodological critiques of the 2026 ageing review were not in
   the top-25 PubMed hits. Fixed: the pack now fetches PubMed CommentIn /
   ErratumIn / RetractionIn links for every relevant synthesis ("linked
   commentary"); 4 critiques entered the creatine pack and 2 the red-meat pack.
4. **Quick mode skipped observational designs for a nutrition question.** The
   red-meat pack initially had 1 cohort study. Fixed: observational search is
   always on for nutrition, economics, social-science and psychology domains.
5. **Sample-size regex** picked 272 from "1,674,272" in one abstract and
   mis-sized several trials; **study-type regex** labelled a scoping review as
   a meta-analysis and some commentaries as RCTs. Not fixed (heuristics): the
   appraiser is instructed to verify both against the abstract and did so
   (17 and 21 corrections documented in the two appraisals).
6. **Search noise.** PubMed relevance returned "creatine kinase" cardiology
   papers; relevance tiers pushed them to tier C and the appraiser excluded
   them with reasons. Cost: appraiser tokens, not accuracy.

## 2. Model stages on real packs

### Creatine -> cognitive performance (quick mode, pack hash 05b8a228..., appraisal hash 8d57566d...)

Isolated appraisal: **suggests_with_uncertainty** for "creatine supplementation
improves cognitive performance (most specifically memory) relative to placebo
in adults"; memory benefit confined to older or sleep-deprived adults, pooled
evidence for general cognition in healthy young adults null (SMD 0.03, 95% CI
-0.14 to 0.20). Per-outcome GRADE: memory low; reasoning/processing speed
very low (mixed; the n=123 trial did not replicate the n=45 trial); sleep
deprivation low; older adults low (mixed); real-world perceived benefit very
low (null). 19 records used, 57 excluded with reasons, 17 heuristic
corrections. Coverage limits stated first. The appraiser did not see the
critiques (run predates fix 3) and said so: "comments on R7 and R1 not in pack".

Comparison with external references: EFSA's 2024 health-claim evaluation (in
the pack only as a reference inside a commentary) did not uphold a creatine
cognition claim; the appraisal's "low / very low" certainties are consistent
with that stance and with the two published double-counting critiques.

Reference check: 54 [R#] citations, all present in the pack. Verification
against the pack's PubMed metadata: 52 verified, 2 unverifiable offline
(OpenAlex-only records). No retractions.

### Red meat -> longevity/mortality (quick mode, pack hash a6aee4ac..., appraisal hash a9bea2ff...)

Isolated appraisal: **suggests_with_uncertainty** for "higher red meat
consumption (total, including processed) is associated with higher all-cause
mortality"; direction harm, small relative magnitude (RR ~1.10 per serving
red meat; 1.15-1.29 processed/total), absolute risk not reported in any
abstract, all observational and abstract-only. GRADE: processed meat low;
unprocessed red meat very low (unprocessed RR 1.10, 95% CI 0.98-1.22,
non-significant); CVD mortality very low (mixed); cancer mortality very low;
modelled life expectancy very low. 25 records used, 52 excluded, 21 heuristic
corrections; noted that the 2019 NutriRECS syntheses were absent although
two records criticise them.

Comparison with external references: the direction and the "low / very low"
certainty match the 2019 NutriRECS GRADE ratings and the 2022 Burden of
Proof study (both rate the evidence as weak); the appraisal did not overstate
beyond them.

Reference check: 77 citations, all present. Verification against pack
metadata: see `run-redmeat/verification.json` summary in section 4.

### Adversarial challenge

See section 4 (appended when the challenger runs completed).

## 3. What was NOT tested

- Live network runs from the Mac mini (the production environment). Expected
  to work since every URL is standard; not demonstrated here.
- The five other subjects at pack level (extraversion, income, cold plunge,
  Flow headset, diet/ADHD). Only the deterministic layer was exercised.
- Deep mode (Europe PMC, Scite tallies, second phrasing).
- The plugin agents as installed (`decide:evidence-appraiser`) rather than
  general-purpose subagents given the same instructions.
- Inter-run variability of the model stages (each appraisal was run once).
- Decision-stage behaviour with real user goals.

## 4. Verification and challenge results

Citation verification demos (offline, from recorded fixtures):

| claim | verdict | notes |
|---|---|---|
| Wakefield 1998, PMID 9500320 | retracted | PubMed "Retracted Publication" + two RetractionIn links |
| Prokopidis 2023, DOI 10.1093/nutrit/nuac064, correct title | verified | Crossref, title similarity 0.94 |
| same DOI, wrong title/author/year | title_mismatch | year, first-author and title checks all fail |
| fabricated DOI 10.1093/nutrit/nuac999 | not_found | Crossref 404 |
