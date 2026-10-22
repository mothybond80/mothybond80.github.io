# Evaluation of existing tools (checked 21 Oct 2026)

Method: two auditing subagents fetched each project's README, manifest,
licence, commit history and main source files (raw.githubusercontent.com,
GitHub HTML, PyPI, vendor docs and pricing pages). Nothing was executed or
installed. "Not verified" marks what could not be checked from the sandbox.

## Summary table

| Tool | Status (Oct 2026) | Licence | Appraisal / RoB | Contradiction detection | Citation verification | Reuse decision |
|---|---|---|---|---|---|---|
| jostelzer/grounded | active, v0.5.6, 1 maintainer, 3 stars | MIT | prose guidance + GRADE-shaped schema validator (not GRADE) | none ("contrary searches required, disagreement is not") | yes: Crossref DOI resolve, title/year fuzzy match, Retraction Watch via `update-to` | borrow retraction/verification logic and certainty schema; do not vendor pipeline |
| openags/paper-search-mcp | active, 2.9k stars, PyPI 0.1.4 broken with mcp 2.x (issue #152) | MIT | none | none | DOI lookup only | skip: 74 tools, ~90 deps, scraping, Sci-Hub connector |
| makidav/clinical-assistant | dormant since Aug 2026, 1 star | CC-BY-4.0 (not a software licence) | prompt text only (RoB 2 / AMSTAR 2 named, not implemented) | prose taxonomy only | yes: PubMed + Crossref, PMID-aware, retraction markers, offline self-test | borrow verifier logic and contradiction taxonomy as rubric text |
| AkariAsai/OpenScholar | frozen since Aug 2025 | Apache-2.0 | none | none | LLM-only post-hoc attribution | skip: GPU/OpenAI-centric, `verify=False` TLS, no timeouts |
| future-house/paper-qa (PaperQA2) | active, v2026.08.12, 9.4k stars | Apache-2.0 | none | `contracrow` config: one claim vs corpus, 11-point agreement scale | hash-keyed chunk citations (structural guard) | borrow ContraCrow label scale and retraction post-processor idea; optional later add-on for local PDFs |
| Scite | commercial; public `/tallies/{doi}` and `/papers/{doi}` free | closed | none (citation sentiment) | "contrasting" tallies, independent eval: low recall (F 0.0-0.58) | retraction notices | use free tallies as advisory signal only (deep mode); no subscription |
| Elicit | commercial; API from $588/yr | closed | none (no RoB/GRADE fields in API) | none | extraction quotes | skip |
| PubMed / OpenAlex / Crossref / Europe PMC | free, keyless, stable | public | n/a | n/a | n/a | core of the engine |
| Semantic Scholar | free, throttled without key | public | n/a | n/a | n/a | implemented, off by default |

## Key findings

1. **No existing tool implements executable critical appraisal, risk of bias,
   GRADE or contradiction detection.** All of them either leave it to the
   model (grounded, clinical-assistant, PaperQA2) or do not attempt it.
2. **Citation and retraction verification is the one component with mature,
   small, stdlib implementations** (grounded: Crossref; clinical-assistant:
   PubMed + Crossref). The engine's `verify.py` and `sources.py` combine both:
   PubMed `PublicationType "Retracted Publication"` and `CommentsCorrections`
   (RetractionIn, ExpressionOfConcernIn, ErratumIn), Crossref `update-to`
   (carries Retraction Watch), OpenAlex `is_retracted`.
3. **Framing-blindness is absent from every tool reviewed.** They search what
   they are given. This is the engine's main novelty and the reason the
   deterministic layer owns query construction.
4. **Security:** grounded and clinical-assistant are stdlib-only and clean;
   paper-search-mcp has the largest surface (scraping, Sci-Hub, 90 deps);
   OpenScholar disables TLS verification. None of this needed installing: the
   engine is ~1,100 lines of new stdlib Python with no dependencies.
5. **Costs:** everything used is free. OpenAlex now rations keyless traffic
   per IP; a free key with its own budget is available from openalex.org and
   is read from `OPENALEX_API_KEY`. Scite/Elicit subscriptions are not
   justified: the features that would matter (RoB, GRADE) do not exist there.

## What was reused

- Retraction-marker logic (both verifiers) -> `sources.py`, `verify.py`.
- grounded's five-domain certainty record -> `appraiser_contract.output_schema`.
- clinical-assistant's contradiction taxonomy and PaperQA2's ContraCrow
  scale -> challenger instructions ("quality and weight of contradictory
  evidence", quote-or-UNSUPPORTED rule).
- OpenScholar's post-hoc attribution idea -> the challenger's citation
  integrity check (quote the abstract sentence or mark UNSUPPORTED).
- Scite public tallies -> `scite_tally()` with the recall caveat attached to
  every value.

Full audit transcripts are in the session; condensed findings above.
