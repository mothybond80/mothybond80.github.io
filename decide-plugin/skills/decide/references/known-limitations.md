# Known limitations (read before promising anything)

1. **Not a systematic review.** Bounded searches (fixed retmax per mode), one
   screener (a model), abstract-level screening, no PRISMA flow with human
   reconciliation. Say "structured evidence appraisal", never "systematic".
2. **Abstract-only by default.** Full text is not fetched. Effect sizes and n
   come from abstracts and must be labelled as such. Europe PMC full text
   exists for open-access PMC articles and could be added.
3. **Heuristic tags.** `study_type` falls back to title regexes and
   `sample_size_guess` is a regex; both are flagged and must be verified by the
   appraiser. PubMed PublicationType tags lag by months for new papers.
4. **Search noise.** PubMed relevance ranking admits off-topic records (e.g.
   "creatine kinase" for a creatine-supplement question). Relevance tiers are
   lexical; a tier-C record can still matter.
5. **Reference-list overlap** uses OpenAlex `referenced_works`, which is
   incomplete and includes background citations. It flags, it does not decide.
6. **Retraction detection** depends on PubMed, Crossref and OpenAlex having
   recorded the notice. Absence of a flag is not proof of integrity.
7. **Rate limits.** PubMed 3 req/s without a key; OpenAlex shares a small
   free daily budget per IP without a key; Semantic Scholar is throttled and
   off by default. Set DECIDE_MAILTO and optional keys for heavier use.
8. **Isolation is by construction in Claude Code** (forked agents without
   conversation, memory or CLAUDE.md) **but only by instruction in Hermes**,
   which runs one memory-bearing context.
9. **The neutraliser is a heuristic.** It handles the tested framings, but
   novel phrasings can produce a wrong PICO; the orchestrator must check and
   override with direction-free terms. The framing test suite covers 22
   framings of 7 subjects, not the open world.
10. **Model judgement remains.** GRADE ratings, screening and contradiction
    weighing are model outputs guided by a contract, not validated instruments.
    The challenge stage reduces but does not remove this.
11. **Grey literature, trial registries, non-English sources and preprints are
    not searched** (ClinicalTrials.gov, OSF, PROSPERO, medRxiv are candidates).
12. **Sandboxed environments** may block the APIs; the cache-put workaround
    works but depends on a web tool returning raw bodies.
