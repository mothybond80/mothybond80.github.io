"""Overlap detection between evidence syntheses.

Two systematic reviews of the same question usually share many included
trials. Treating them as independent confirmation double-counts the evidence.
We measure overlap with the OpenAlex `referenced_works` lists (reference-list
Jaccard and the share of the smaller list contained in the larger), and we
flag likely overlapping primary studies by DOI / PMID identity and near-
identical titles.

This is a *flag*, not a verdict: reference lists include background citations
and OpenAlex coverage of references is incomplete, so moderate overlap values
must be confirmed against the reviews' inclusion tables.
"""

from __future__ import annotations

from itertools import combinations
from typing import Any

from .verify import title_similarity


def review_overlap(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    syn = [r for r in records if r.get("classification", {}).get("is_synthesis") and r.get("referenced_works")]
    out = []
    for a, b in combinations(syn, 2):
        sa, sb = set(a["referenced_works"]), set(b["referenced_works"])
        if not sa or not sb:
            continue
        inter = len(sa & sb)
        jacc = inter / len(sa | sb)
        contain = inter / min(len(sa), len(sb))
        if inter >= 3 and (jacc >= 0.15 or contain >= 0.4):
            out.append({"a": a.get("doi") or a.get("pmid") or a.get("openalex_id"), "b": b.get("doi") or b.get("pmid") or b.get("openalex_id"),
                        "a_title": a.get("title"), "b_title": b.get("title"), "shared_refs": inter, "jaccard": round(jacc, 3),
                        "containment": round(contain, 3),
                        "note": "likely overlapping included studies; do not count as independent confirmation without checking inclusion tables"})
    return out


ANCILLARY_TYPES = {"Published Erratum", "Comment", "Letter", "Editorial", "Retraction of Publication", "Expression of Concern"}


def _ancillary(r: dict[str, Any]) -> bool:
    """Errata, comments and letters often carry the same title as the paper they refer to.
    They must stay separate records (they are evidence about integrity), so they are never
    merged by title similarity, only by exact identifier."""
    return bool(ANCILLARY_TYPES & set(r.get("pub_types") or [])) or (r.get("title") or "").lower().startswith(("erratum", "correction", "corrigendum", "comment on", "re:", "response to", "reply to"))


def dedupe(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge hits for the same paper from different databases. Keeps the richest record."""
    merged: list[dict[str, Any]] = []
    for r in records:
        hit = None
        for m in merged:
            if (r.get("doi") and r["doi"] == m.get("doi")) or (r.get("pmid") and r["pmid"] == m.get("pmid")) or \
               (r.get("openalex_id") and r["openalex_id"] == m.get("openalex_id")):
                hit = m
                break
            if not _ancillary(r) and not _ancillary(m) and r.get("title") and m.get("title") and \
               title_similarity(r["title"], m["title"]) >= 0.93 and \
               (r.get("year") is None or m.get("year") is None or abs(r["year"] - m["year"]) <= 1):
                hit = m
                break
        if hit is None:
            r = dict(r)
            r["sources"] = [r["source"]]
            merged.append(r)
        else:
            hit.setdefault("sources", [hit.get("source")])
            if r["source"] not in hit["sources"]:
                hit["sources"].append(r["source"])
            for k, v in r.items():
                if k in ("source", "sources"):
                    continue
                if (hit.get(k) in (None, [], "", False)) and v not in (None, [], ""):
                    hit[k] = v
            hit["is_retracted"] = bool(hit.get("is_retracted")) or bool(r.get("is_retracted"))
            # keep PubMed pub types if available (most reliable)
            if r.get("source") == "pubmed" and r.get("pub_types"):
                hit["pub_types"] = r["pub_types"]
            if r.get("abstract_source") == "pubmed" and r.get("abstract") and len(r["abstract"]) >= len(hit.get("abstract") or ""):
                hit["abstract"], hit["abstract_source"] = r["abstract"], "pubmed"
    return merged
