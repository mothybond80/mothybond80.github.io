# Limitations and proposed improvements

The operative list of limitations is
`../skills/decide/references/known-limitations.md` (loaded by the skill so the
model sees it at run time). This file adds the roadmap.

## Observed in this build (see TESTING.md for evidence)

- Search noise from PubMed relevance ranking (creatine kinase, statin trials
  for a creatine-supplement question). Relevance tiers push these to the end
  but they still cost appraiser tokens.
- OpenAlex coverage of `referenced_works` is partial, so reference-list
  overlap under-detects. The 2018 and 2022/23 creatine reviews share 16 of
  ~50 references and were flagged; two reviews with sparse OpenAlex reference
  data would not be.
- The neutraliser is a lexical heuristic tuned on the seven test subjects. It
  passed all 22 framings in the suite, but a new topic can produce a wrong
  PICO; the orchestrator's override is the safety net, and it is a model.
- Year disagreements between sources (online-first vs print) are tolerated
  (+/- 1) in dedupe and verification.
- In sandboxed Claude Code cloud environments the APIs were blocked by the
  network policy; the cache workaround works but is manual.
- Hermes cannot provide a provably isolated appraisal context.

## Proposed improvements, in order of value

1. **Full text for open-access records** via Europe PMC `fullTextXML`
   (and Unpaywall for OA links), so effect sizes and risk-of-bias judgements
   are not abstract-only. Keep abstract-only labelling for the rest.
2. **Trial registries and grey literature**: ClinicalTrials.gov v2 API
   (registered but unpublished trials = publication-bias signal), PROSPERO,
   medRxiv/bioRxiv via Europe PMC preprint flag.
3. **Second search phrasing automatically** (brand name + generic class,
   MeSH expansion via PubMed's query translation) rather than relying on the
   orchestrator in deep mode.
4. **Included-study extraction for syntheses**: parse "included N trials"
   and, where OA full text exists, the inclusion table, to make overlap
   detection exact rather than reference-list based.
5. **Calibration set**: a dozen questions with Cochrane/NICE/USPSTF answers
   as ground truth, scored automatically on verdict label and certainty
   level, run on every change to the agent prompts.
6. **Decision-analysis helper**: a small script for absolute-risk arithmetic
   (NNT/NNH from baseline risk and relative effects) so the decision stage
   cannot mis-multiply.
7. **Headless mode**: `claude --bare -p "/decide:decide quick ..."` wrapper
   so Hermes can get the fully isolated pipeline without the code-task
   bridge.
8. **Semantic Scholar with a free key** for citation-context ("cites as
   contrasting") and TLDRs, once rate limits are not a concern.
9. **PaperQA2 add-on** for questions where the user supplies PDFs (guideline
   documents, paywalled trials).
10. **Multilingual search** (Europe PMC indexes non-English abstracts) and
    LILACS for Latin American literature where relevant.
