# Research and decision methodology

This is the method the `/decide` pipeline follows. It is *inspired by* NICE
evidence-review methods, Cochrane systematic-review principles, GRADE, PRISMA
and AMSTAR 2. It is not a systematic review and must never be described as one:
searches are bounded, screening is done by a model from abstracts, and no
second human reviewer exists.

## 1. Question formulation (framing-blind)

1. The user's wording is a hypothesis. Rhetorical framing ("isn't it true",
   "surely", "actually", "fail to") is stripped; the asker's implied direction
   is recorded in a separate file that the appraisal stages cannot read.
2. The question is rewritten as "What is the effect of <exposure> on
   <outcome> in <population>, and in which direction?". PICO fields contain
   nouns only. A `framing_hash` of the direction-free concept set is computed;
   identical hashes for opposite framings is the testable property.
3. The research domain is detected (medicine, nutrition, psychology,
   economics, social science, exercise science, emerging technology) and
   domain-specific guidance is attached to the pack (section 3).

## 2. Search (deterministic, auditable)

Databases, all free and keyless: PubMed E-utilities (relevance-ranked reviews,
trials, observational designs, plus a recency slice sorted by date), OpenAlex
(most-cited works and reference lists), Europe PMC (deep mode), Crossref
(DOI resolution, retraction/update metadata), optional Scite public tallies
(deep mode, advisory only). Semantic Scholar is implemented but off by default
because of unauthenticated rate limits.

The pack records for every search: database, label, the query string, the
database's own query translation (PubMed), total hit count, number retrieved,
and the URL. Dates searched are the pack's `built_at` timestamp. Limits per
mode are fixed in `MODE_LIMITS` and reported.

Inclusion is decided *before* reading results: any human study or synthesis
whose title or abstract mentions the exposure and outcome concepts (relevance
tier A or B). Tier C records are kept visible but marked. Comments, letters
and errata are kept because they often carry the strongest criticism of a
synthesis (e.g. a double-counting letter).

## 3. Domain-appropriate hierarchies

Medical hierarchies are not applied blindly. The pack's `domain_guidance`
lists preferred, supporting and weak designs for the detected domains and
what to watch for:

| Domain | Strongest usable evidence | Typical traps |
|---|---|---|
| Medicine | SR/MA of RCTs, RCTs, guidelines | surrogate outcomes, sponsor bias, harms under-reported |
| Nutrition | RCTs (often short), MR studies, cohorts | healthy-user confounding, substitution ("instead of what?"), relative vs absolute risk |
| Psychology | pre-registered replications, meta-analyses with bias correction | small samples, WEIRD samples, self-report, p-hacking |
| Economics | natural experiments, lotteries/windfalls, panels | identification strategy, log vs linear income, experienced vs evaluative measures |
| Social science | natural experiments, longitudinal, replications | selection, cross-cultural validity, ecological fallacy |
| Exercise science | RCTs (blinding often impossible) | expectancy effects, tiny n, surrogate biomarkers |
| Emerging technology | sham-controlled RCTs | manufacturer-run trials, open-label pilots, press releases |

Four levels of claim are kept distinct throughout: mechanistic plausibility,
observational association, causal evidence, demonstrated real-world
effectiveness.

## 4. Appraisal (isolated)

Performed by the `evidence-appraiser` agent, which sees only the pack. Per
record: design (verified against the abstract, not the heuristic tag),
population, n, comparator, outcomes, direction and magnitude with CI,
funding, limitations, abstract-only flag. Per outcome: GRADE domains (risk of
bias, inconsistency, indirectness, imprecision, publication bias) each with a
judgment and reason, then overall certainty high / moderate / low / very low.
Systematic reviews are checked for overlap (`overlap_warnings` from shared
reference lists) so the same trials are not counted twice. Statistical
significance is separated from practical importance by stating absolute
effects. Generalisability to the question's population is judged explicitly.
Retracted records and integrity flags (errata, expressions of concern) are
surfaced.

Verdict vocabulary: strongly_supports, suggests_with_uncertainty, mixed,
insufficient, contradicts, more_information_needed. The verdict always names
the directional claim it refers to.

## 5. Challenge (adversarial, isolated)

The `evidence-challenger` agent tries to falsify the appraisal using the ten
questions in the task specification (missed contradictory studies, weakest
link, alternative explanations, correlation vs causation, replication,
neglected nulls, publication bias, overreach, newer studies, citation
integrity). Objections carry an evidential weight so weak objections do not
get false parity. The challenger may run additional engine searches with
corrected terms and must quote abstract sentences for every claim it checks.

## 6. Verification

- Every `[R#]` used must exist in the pack (`check_refs.py`).
- Every cited DOI/PMID is re-resolved (`decide-engine verify`): title match,
  year, first author, retraction status via PubMed, Crossref and OpenAlex.
- Unverified claims are dropped or labelled. A tool summary is never treated
  as verification of the underlying paper; the appraiser quotes abstracts.
- The pack and the appraisal are SHA-256 locked before the decision stage.

## 7. Evidence-to-decision

Only after the lock may the user's goals, constraints, costs and risk
tolerance be read. The framework: expected benefit (absolute magnitude),
harms and severity, outcome probabilities where defensible (no invented
numbers), financial and opportunity cost, alternatives, reversibility,
short vs long term, evidence certainty, value of information and cost of
delay, and whether doing nothing is best. Bayesian reasoning is used
qualitatively (what prior does the evidence shift, and by roughly how much)
unless the pack contains quantities that justify arithmetic.

The report keeps three sections visibly apart: scientific conclusion;
decision assumptions; value judgements. A recommendation is made only when the
first and the user's stated values together justify it. For medical topics
the report states when clinical supervision is necessary.

## 8. What this method cannot do

See `known-limitations.md`. In short: abstract-level screening, bounded
searches, no human second reviewer, heuristic design tags, model judgement in
appraisal, and (for Hermes) weaker context isolation.
