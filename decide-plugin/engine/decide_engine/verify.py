"""Citation verification against source metadata.

A citation is a claim: "paper X, by Y, in year Z, says W". We can mechanically
check X/Y/Z against Crossref, PubMed and OpenAlex. Whether it says W is for the
appraising agent to check against the abstract/full text, but we supply the
abstract so that the check is against source material, not memory.

Verdicts:
  verified         - identifier resolves and title matches (ratio >= 0.85)
  title_mismatch   - identifier resolves but the title differs materially
  not_found        - identifier does not resolve and no bibliographic match
  resolved_by_search - no identifier given; a close bibliographic match exists
  retracted        - resolves, but flagged retracted in PubMed/Crossref/OpenAlex
"""

from __future__ import annotations

import difflib
import re
from typing import Any

from .fetch import FetchBlocked, Fetcher
from .sources import crossref_search, crossref_work, norm_doi, openalex_work, pubmed_fetch


def _norm_title(t: str | None) -> str:
    t = (t or "").lower()
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def title_similarity(a: str | None, b: str | None) -> float:
    """Max of sequence ratio and containment (longest common substring / shorter title), so a
    citation that omits a subtitle still matches while unrelated titles do not."""
    ta, tb = _norm_title(a).split(), _norm_title(b).split()
    if not ta or not tb:
        return 0.0
    sm = difflib.SequenceMatcher(None, ta, tb)
    ratio = sm.ratio()
    m = sm.find_longest_match(0, len(ta), 0, len(tb))
    containment = m.size / min(len(ta), len(tb))
    return max(ratio, containment if m.size >= 4 else 0.0)


def verify_citation(f: Fetcher, claimed: dict[str, Any], pack_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """claimed: {title, year, first_author, doi, pmid}. Returns a verdict dict with the resolved record.

    pack_records: optional records from an evidence pack. Those that came from PubMed are
    source metadata already fetched from the database, so they resolve the identifier even when
    the network is unavailable; retraction cross-checks against Crossref/OpenAlex still need it."""
    doi = norm_doi(claimed.get("doi"))
    pmid = str(claimed.get("pmid")).strip() if claimed.get("pmid") else None
    resolved: dict[str, Any] | None = None
    via = None
    checks: list[str] = []
    blocked = False
    if pack_records:
        for r in pack_records:
            if "pubmed" in (r.get("sources") or [r.get("source")]) and ((pmid and r.get("pmid") == pmid) or (doi and r.get("doi") == doi)):
                resolved, via = r, "pack(pubmed)"
                checks.append("resolved from PubMed metadata already in the evidence pack")
                break

    if resolved is None and pmid:
        try:
            recs = pubmed_fetch(f, [pmid])
        except FetchBlocked:
            recs, blocked = [], True
            checks.append("PubMed lookup not possible (offline / blocked)")
        except Exception as e:  # HTTP error etc.
            recs = []
            checks.append(f"PubMed lookup failed: {e!r}")
        if recs:
            resolved, via = recs[0], "pubmed"
        elif not blocked:
            checks.append(f"PMID {pmid} did not resolve in PubMed")
    definite_404 = False
    if resolved is None and doi:
        n0 = len(f.log)
        resolved = crossref_work(f, doi)
        via = "crossref" if resolved else None
        if resolved is None:
            definite_404 = any(l.status in (404, 410) for l in f.log[n0:])
            if any(l.source == "blocked" for l in f.log[n0:]):
                blocked = True
            n1 = len(f.log)
            oa = openalex_work(f, f"doi:{doi}")
            if any(l.source == "blocked" for l in f.log[n1:]):
                checks.append("OpenAlex lookup not possible (offline / blocked)")
            if oa:
                resolved, via = oa, "openalex"
            elif definite_404:
                checks.append(f"DOI {doi} does not exist in Crossref (HTTP 404)")
            else:
                checks.append(f"DOI {doi} did not resolve in Crossref or OpenAlex")
    if resolved is None and definite_404:
        return {"verdict": "not_found", "via": None, "checks": checks, "resolved": None, "claimed": claimed}
    if resolved is None and claimed.get("title"):
        cands = crossref_search(f, f"{claimed.get('title')} {claimed.get('first_author') or ''} {claimed.get('year') or ''}".strip(), rows=5)
        best = max(cands, key=lambda c: title_similarity(c.get("title"), claimed.get("title")), default=None)
        if best and title_similarity(best.get("title"), claimed.get("title")) >= 0.85:
            resolved, via = best, "crossref_search"
            checks.append("no identifier supplied; matched by bibliographic search")
        elif blocked or any(l.source == "blocked" for l in f.log[-6:]):
            return {"verdict": "unverifiable_offline", "via": None, "checks": checks + ["network unavailable; could not resolve identifiers"], "resolved": None, "claimed": claimed}
        else:
            return {"verdict": "not_found", "via": None, "checks": checks + ["no close bibliographic match (title ratio < 0.85)"], "resolved": None, "claimed": claimed}

    if resolved is None:
        if blocked or any(l.source == "blocked" for l in f.log[-6:]):
            return {"verdict": "unverifiable_offline", "via": None, "checks": checks + ["network unavailable; could not resolve identifiers"], "resolved": None, "claimed": claimed}
        return {"verdict": "not_found", "via": None, "checks": checks, "resolved": None, "claimed": claimed}

    sim = title_similarity(resolved.get("title"), claimed.get("title")) if claimed.get("title") else None
    year_ok = None
    if claimed.get("year") and resolved.get("year"):
        year_ok = abs(int(claimed["year"]) - int(resolved["year"])) <= 1
        if not year_ok:
            checks.append(f"year mismatch: claimed {claimed['year']}, source {resolved['year']}")
    author_ok = None
    if claimed.get("first_author") and resolved.get("authors"):
        fa = re.sub(r"[^a-z]", "", claimed["first_author"].split()[0].lower()) if claimed["first_author"].split() else ""
        author_ok = fa != "" and fa in re.sub(r"[^a-z]", "", resolved["authors"][0].lower())
        if not author_ok:
            checks.append(f"first author mismatch: claimed '{claimed['first_author']}', source '{resolved['authors'][0]}'")

    # Retraction: consult every source we can reach for the resolved identifiers
    retracted = bool(resolved.get("is_retracted"))
    rdoi = resolved.get("doi") or doi
    n_before = len(f.log)
    if not retracted and rdoi and via != "crossref":
        cr = crossref_work(f, rdoi)
        if cr and cr.get("is_retracted"):
            retracted = True
            checks.append("Crossref update-to indicates retraction")
    if not retracted and rdoi and via != "openalex":
        oa = openalex_work(f, f"doi:{rdoi}")
        if oa and oa.get("is_retracted"):
            retracted = True
            checks.append("OpenAlex is_retracted=true")
    if any(l.source == "blocked" for l in f.log[n_before:]):
        checks.append("retraction cross-check against Crossref/OpenAlex NOT performed (offline); PubMed markers only")

    if retracted:
        verdict = "retracted"
    elif sim is not None and sim < 0.85:
        verdict = "title_mismatch"
        checks.append(f"title similarity {sim:.2f} < 0.85")
    elif via == "crossref_search":
        verdict = "resolved_by_search"
    else:
        verdict = "verified"
    return {"verdict": verdict, "via": via, "title_similarity": sim, "year_ok": year_ok, "first_author_ok": author_ok,
            "checks": checks, "resolved": resolved, "claimed": claimed}
