"""Build an *evidence pack*: everything an isolated appraiser needs, and nothing
about the asker.

The pack contains the neutral question, the PICO guess, the domain guidance,
the exact executed searches (database, query, PubMed's own query translation,
hit counts, URLs), the deduplicated records with design classification and
integrity flags, and overlap warnings between syntheses. It contains NO user
identity, NO conversation text and NO expectation direction - that is kept in a
separate `asker` block written to a different file so the appraiser never sees
it.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from .classify import classify, domain_guidance
from .fetch import FetchBlocked, Fetcher
from .overlap import dedupe, review_overlap
from .question import ParsedQuestion, parse_question, search_strategy
from .sources import (europepmc_search, openalex_search, openalex_work, pubmed_fetch, pubmed_search, scite_tally)

OBSERVATIONAL_DOMAINS = {"nutrition", "economics", "social_science", "psychology"}

MODE_LIMITS = {
    "quick": {"pubmed_reviews": 25, "pubmed_trials": 25, "pubmed_obs": 0, "pubmed_recent": 15, "openalex": 20, "europepmc": 0,
              "openalex_refs_for": 15, "scite": False, "linked_comments": 20},
    "deep": {"pubmed_reviews": 60, "pubmed_trials": 60, "pubmed_obs": 40, "pubmed_recent": 40, "openalex": 50, "europepmc": 50,
             "openalex_refs_for": 25, "scite": True, "linked_comments": 40},
}


def sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def build_pack(question: str, mode: str = "quick", fetcher: Fetcher | None = None, pq: ParsedQuestion | None = None,
               recent_years: int = 3) -> dict[str, Any]:
    f = fetcher or Fetcher()
    pq = pq or parse_question(question)
    lim = dict(MODE_LIMITS[mode])
    # Domains where the best available evidence is usually observational: always search it.
    if lim["pubmed_obs"] == 0 and any(d in OBSERVATIONAL_DOMAINS for d in pq.domains):
        lim["pubmed_obs"] = 20
    strat = search_strategy(pq)
    searches: list[dict[str, Any]] = []
    errors: list[str] = []
    records: list[dict[str, Any]] = []
    pmids: list[str] = []

    def _pm(label: str, term: str, n: int, mindate: str | None = None, sort: str = "relevance") -> None:
        if n <= 0:
            return
        try:
            ids, meta = pubmed_search(f, term, retmax=n, mindate=mindate, sort=sort)
            meta["label"] = label
            searches.append(meta)
            pmids.extend(ids)
        except FetchBlocked as e:
            errors.append(f"blocked (offline, not cached): {e}")
        except Exception as e:
            errors.append(f"pubmed {label}: {e!r}")

    _pm("pubmed_reviews", strat["pubmed"]["reviews"], lim["pubmed_reviews"])
    _pm("pubmed_trials", strat["pubmed"]["trials"], lim["pubmed_trials"])
    _pm("pubmed_observational", strat["pubmed"]["observational"], lim["pubmed_obs"])
    yr = time.gmtime().tm_year - recent_years
    _pm("pubmed_recent", strat["pubmed"]["recent_any"], lim["pubmed_recent"], mindate=f"{yr}/01/01", sort="pub_date")

    uniq = list(dict.fromkeys(pmids))
    if uniq:
        try:
            records.extend(pubmed_fetch(f, uniq))
        except FetchBlocked as e:
            errors.append(f"blocked (offline, not cached): {e}")
        except Exception as e:
            errors.append(f"pubmed efetch: {e!r}")

    if lim["openalex"]:
        try:
            recs, meta = openalex_search(f, strat["openalex"]["query"], per_page=lim["openalex"], sort="cited_by_count:desc")
            meta["label"] = "openalex_most_cited"
            searches.append(meta)
            records.extend(recs)
        except FetchBlocked as e:
            errors.append(f"blocked (offline, not cached): {e}")
        except Exception as e:
            errors.append(f"openalex: {e!r}")

    if lim["europepmc"]:
        try:
            recs, meta = europepmc_search(f, strat["europepmc"]["query"], page_size=lim["europepmc"])
            meta["label"] = "europepmc"
            searches.append(meta)
            records.extend(recs)
        except FetchBlocked as e:
            errors.append(f"blocked (offline, not cached): {e}")
        except Exception as e:
            errors.append(f"europepmc: {e!r}")

    merged = dedupe(records)
    for r in merged:
        r["classification"] = classify(r)
        r["relevance"] = relevance(r, pq)

    # Linked commentary: PubMed records carry CommentIn / ErratumIn / RetractionIn links. Published
    # criticism of a key synthesis (e.g. a letter about double counting) is exactly what a relevance
    # search misses, so fetch those linked records for the relevant syntheses (bounded).
    have = {r.get("pmid") for r in merged if r.get("pmid")}
    linked: dict[str, str] = {}
    for r in merged:
        if r["classification"]["is_synthesis"] and r["relevance"]["tier"] in ("A", "B"):
            for c in r.get("comments") or []:
                if c.get("type") in ("CommentIn", "ErratumIn", "RetractionIn", "ExpressionOfConcernIn") and c.get("pmid") and c["pmid"] not in have:
                    linked.setdefault(c["pmid"], r.get("pmid") or r.get("doi") or "")
    if linked:
        try:
            extra = pubmed_fetch(f, sorted(linked)[:lim["linked_comments"]])
            for e in extra:
                e["linked_from_pmid"] = linked.get(e.get("pmid"))
                e["classification"] = classify(e)
                e["relevance"] = relevance(e, pq)
                e["sources"] = ["pubmed"]
            merged.extend(extra)
            searches.append({"db": "pubmed", "label": "linked_commentary", "query": "CommentIn/ErratumIn/RetractionIn links from tier A/B syntheses",
                             "count": len(linked), "returned": len(extra), "url": None})
        except FetchBlocked as e:
            errors.append(f"blocked (offline, not cached): {e}")
        except Exception as e:
            errors.append(f"pubmed linked commentary: {e!r}")
    essential_blocked = [l.url for l in f.log if l.source == "blocked"]

    # Reference lists for syntheses (overlap detection) and Scite tallies, bounded
    syn = [r for r in merged if r["classification"]["is_synthesis"] and r["relevance"]["tier"] in ("A", "B")]
    syn.sort(key=lambda r: (r["relevance"]["tier"], -(r.get("year") or 0), -(r.get("cited_by_count") or 0)))
    for r in syn[: lim["openalex_refs_for"]]:
        if not r.get("referenced_works"):
            ident = f"doi:{r['doi']}" if r.get("doi") else (f"pmid:{r['pmid']}" if r.get("pmid") else None)
            if ident:
                try:
                    oa = openalex_work(f, ident)
                except FetchBlocked:
                    oa = None
                if oa:
                    r["referenced_works"] = oa.get("referenced_works") or []
                    r["openalex_id"] = r.get("openalex_id") or oa.get("openalex_id")
                    r["cited_by_count"] = r.get("cited_by_count") if r.get("cited_by_count") is not None else oa.get("cited_by_count")
                    r["is_retracted"] = bool(r.get("is_retracted")) or bool(oa.get("is_retracted"))
                    if not r.get("abstract") and oa.get("abstract"):
                        r["abstract"], r["abstract_source"] = oa["abstract"], "openalex_inverted"
        if lim["scite"] and r.get("doi"):
            try:
                t = scite_tally(f, r["doi"])
            except FetchBlocked:
                t = None
            if t:
                r["scite_tally"] = t

    overlaps = review_overlap(merged)
    merged.sort(key=_rank_key)
    for i, r in enumerate(merged, 1):
        r["ref"] = f"R{i}"

    counts: dict[str, int] = {}
    tiers = {"A": 0, "B": 0, "C": 0}
    for r in merged:
        tiers[r["relevance"]["tier"]] += 1
        counts[r["classification"]["study_type"]] = counts.get(r["classification"]["study_type"], 0) + 1
    evidence_gap = (tiers["A"] + tiers["B"]) == 0
    pop_cov = population_coverage(merged, pq)

    pack = {
        "engine_version": "0.1.1",
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": mode,
        "limits": lim,
        "question": {
            "neutral": pq.neutral_question, "exposure": pq.exposure, "outcome": pq.outcome, "population": pq.population,
            "comparator": pq.comparator, "domains": pq.domains, "framing_hash": pq.framing_hash,
        },
        "domain_guidance": domain_guidance(pq.domains),
        "search_strategy": strat,
        "searches": searches,
        "errors": errors,
        "fetch_log_summary": _log_summary(f),
        "n_records": len(merged),
        "study_type_counts": counts,
        "relevance_tiers": tiers,
        "evidence_gap": evidence_gap,
        "evidence_gap_note": ("No record mentions both the exposure and the outcome. The searches ran (see `searches`); the indexed "
                              "literature contains nothing on-topic in these databases. The only valid verdict is 'insufficient'; "
                              "tier C records are adjacent noise and must not be used to fill the gap.") if evidence_gap else None,
        "population_coverage": pop_cov,
        "retracted_or_flagged": [r["ref"] for r in merged if r.get("is_retracted") or r.get("integrity_flags")],
        "missing_urls": essential_blocked,
        "optional_missing_urls": [l.url for l in f.log if l.source == "blocked" and l.url not in essential_blocked],
        "overlap_warnings": overlaps,
        "records": merged,
        "appraiser_contract": APPRAISER_CONTRACT,
    }
    pack["pack_hash"] = sha({k: v for k, v in pack.items() if k not in ("built_at", "fetch_log_summary")})
    return pack


def asker_block(pq: ParsedQuestion) -> dict[str, Any]:
    """Kept OUT of the pack. Only the decision stage may read it."""
    return {"raw_question": pq.raw, "asker_direction": pq.asker_direction, "framing_hash": pq.framing_hash, "parser_notes": pq.notes}


def _rank_key(r: dict[str, Any]) -> tuple:
    order = {"umbrella_review": 0, "meta_analysis": 1, "systematic_review": 1, "guideline": 2, "rct": 3, "mendelian_randomisation": 3,
             "natural_experiment": 3, "replication": 4, "controlled_trial": 4, "cohort": 5, "longitudinal": 5, "clinical_trial": 5,
             "case_control": 6, "cross_sectional": 7, "observational": 7, "pilot": 8, "narrative_review": 9, "preclinical": 10,
             "case_report": 11, "protocol": 12, "comment": 13, "unclassified": 14, "retracted": 20}
    st = r["classification"]["study_type"]
    return (1 if r.get("is_retracted") else 0, r.get("relevance", {}).get("tier", "C"), order.get(st, 15), -(r.get("year") or 0), -(r.get("cited_by_count") or 0))


def relevance(r: dict[str, Any], pq: ParsedQuestion) -> dict[str, Any]:
    """Cheap lexical relevance so the appraiser can skip obvious noise (e.g. 'creatine kinase'
    hits for a creatine-supplementation question). Tier A: exposure in title and outcome anywhere;
    B: exposure and outcome both present somewhere; C: otherwise. A flag, not a filter."""
    import re as _re
    from .question import SYNONYMS
    title = (r.get("title") or "").lower()
    text = title + " " + (r.get("abstract") or "").lower()
    def terms(concept: str) -> list[str]:
        base = [t.lower() for t in (SYNONYMS.get(concept) or [concept])]
        return base + [w for w in concept.lower().split() if len(w) > 3]
    def hit(ts: list[str], where: str) -> bool:
        return any(_re.search(r"\b" + _re.escape(t) + r"\b", where) for t in ts)
    et, ot = terms(pq.exposure), terms(pq.outcome) if pq.outcome else []
    e_title, e_any = hit(et, title), hit(et, text)
    o_any = hit(ot, text) if ot else True
    o_title = hit(ot, title) if ot else True
    tier = "A" if (e_title and o_any) else ("B" if (e_any and o_any) else "C")
    return {"tier": tier, "exposure_in_title": e_title, "exposure_in_text": e_any, "outcome_in_title": o_title, "outcome_in_text": o_any}


POP_TERMS = {
    "adults": (["adult", "adults"], ["child", "children", "adolescent", "paediatric", "pediatric", "youth", "boys", "girls", "infant"]),
    "men": (["men", "male", "males"], []),
    "women": (["women", "female", "females"], []),
    "children": (["child", "children", "paediatric", "pediatric"], ["adult", "adults"]),
    "older adults": (["older adult", "elderly", "aged 6", "aged 7", "seniors"], ["young adult", "students"]),
}


def population_coverage(records: list[dict[str, Any]], pq: ParsedQuestion) -> dict[str, Any] | None:
    """Does the on-topic literature actually study the population in the question? A question about
    adults answered mostly by paediatric trials is an indirectness problem the appraiser must see."""
    import re as _re
    if not pq.population:
        return None
    key = pq.population.lower().strip()
    terms, contrary = POP_TERMS.get(key, ([key], []))
    ab = [r for r in records if r.get("relevance", {}).get("tier") in ("A", "B")]
    if not ab:
        return {"population": pq.population, "records_ab": 0, "mentioning": 0, "contrary": 0, "warning": None}
    def has(ts: list[str], r: dict[str, Any]) -> bool:
        text = ((r.get("title") or "") + " " + (r.get("abstract") or "")).lower()
        return any(_re.search(r"\b" + _re.escape(t), text) for t in ts)
    mentioning = sum(has(terms, r) for r in ab)
    contrary_n = sum(has(contrary, r) for r in ab) if contrary else 0
    warning = None
    if mentioning < max(1, len(ab) // 4) or (contrary and contrary_n > mentioning):
        warning = (f"Only {mentioning} of {len(ab)} on-topic records mention '{pq.population}'"
                   + (f"; {contrary_n} study a different population" if contrary else "")
                   + ". Treat as indirect evidence and say so; do not generalise silently.")
    return {"population": pq.population, "records_ab": len(ab), "mentioning": mentioning, "contrary": contrary_n, "warning": warning}


def _log_summary(f: Fetcher) -> dict[str, Any]:
    out = {"cache": 0, "network": 0, "blocked": 0, "error": 0}
    for l in f.log:
        out[l.source] = out.get(l.source, 0) + 1
    return out


APPRAISER_CONTRACT = {
    "role": "You are appraising evidence for a neutral research question. You have no information about who asked or what answer they hoped for, and you must not infer it.",
    "must": [
        "Read every record's title, design classification and abstract. Treat 'sample_size_guess' and regex-based 'study_type' as heuristics to verify from the abstract.",
        "Classify each relevant record: direction of finding (benefit / harm / null / mixed), outcome(s), effect size with CI where stated, population, and major limitations.",
        "Separate mechanistic plausibility, observational association, causal evidence (RCT / natural experiment / Mendelian randomisation) and demonstrated real-world effectiveness.",
        "Rate certainty per outcome using the five GRADE domains (risk_of_bias, inconsistency, indirectness, imprecision, publication_bias), each with a judgment and a one-line reason, then an overall certainty: high / moderate / low / very_low.",
        "Do not double-count: when overlap_warnings lists two syntheses, or a synthesis includes trials that also appear as records, say so and count the evidence once.",
        "Weight contradictory evidence by its quality, not by its existence. Do not manufacture balance between a large meta-analysis and a small pilot.",
        "Distinguish statistical significance from practical importance; state the absolute magnitude where possible.",
        "Say what full text you did not see. Findings based only on abstracts must be labelled 'abstract-only'.",
        "Never cite a record that is not in the pack. Every claim carries the record's ref (R-number) and identifier.",
        "If the records cannot answer the question, say 'insufficient evidence' and specify what study would be needed.",
        "If `evidence_gap` is true, the verdict is 'insufficient'. Do not use tier C records to build an answer.",
        "If `population_coverage.warning` is set, the evidence is indirect for the population asked about: downgrade indirectness and state the mismatch explicitly.",
    ],
    "output_schema": {
        "neutral_question": "string",
        "evidence_summary": "3-6 sentences, direction-neutral language",
        "verdict": "one of: strongly_supports | suggests_with_uncertainty | mixed | insufficient | contradicts | more_information_needed",
        "verdict_refers_to": "the specific directional claim being judged, stated neutrally as '<exposure> <changes> <outcome> in <population>'",
        "outcomes": [{"outcome": "", "direction": "benefit|harm|null|mixed", "magnitude": "", "certainty": "high|moderate|low|very_low",
                      "grade_domains": {"risk_of_bias": {"judgment": "", "reason": ""}, "inconsistency": {}, "indirectness": {}, "imprecision": {}, "publication_bias": {}},
                      "key_refs": ["R1"], "evidence_type": "causal|observational|mechanistic|effectiveness", "abstract_only": True}],
        "contradictory_evidence": [{"ref": "R#", "finding": "", "quality": "", "weight": ""}],
        "generalisability": "",
        "what_would_change_this": "",
        "records_used": ["R#"], "records_excluded": [{"ref": "R#", "why": ""}],
    },
}
