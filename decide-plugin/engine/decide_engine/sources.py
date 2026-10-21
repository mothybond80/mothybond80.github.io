"""Adapters for free scholarly APIs. Each returns a list of `Record` dicts with a
common shape so downstream code never cares which database a hit came from.

Databases (all free, no key required; optional keys raise rate limits):
  PubMed E-utilities  https://www.ncbi.nlm.nih.gov/books/NBK25501/   NCBI_API_KEY
  OpenAlex            https://docs.openalex.org                       OPENALEX_API_KEY
  Crossref            https://api.crossref.org                        (mailto only)
  Europe PMC          https://europepmc.org/RestfulWebService         (none)
  Semantic Scholar    https://api.semanticscholar.org                 S2_API_KEY (optional)

Nothing here interprets results. It only retrieves and normalises.
"""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from typing import Any

from .fetch import Fetcher, build_url

PUBMED = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
OPENALEX = "https://api.openalex.org"
CROSSREF = "https://api.crossref.org"
EUROPEPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
S2 = "https://api.semanticscholar.org/graph/v1"


def new_record(**kw: Any) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "source": None,          # which database produced this hit
        "pmid": None,
        "pmcid": None,
        "doi": None,
        "openalex_id": None,
        "title": None,
        "authors": [],           # list of "Surname AB"
        "year": None,
        "journal": None,
        "pub_types": [],         # PubMed PublicationType strings when available
        "abstract": None,
        "abstract_source": None, # "pubmed" | "openalex_inverted" | "europepmc" | None
        "cited_by_count": None,
        "is_retracted": False,
        "retraction_notice": None,
        "has_full_text_oa": None,
        "referenced_works": [],  # OpenAlex W-ids, used for overlap detection
        "mesh": [],
        "url": None,
    }
    rec.update(kw)
    return rec


def norm_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    d = doi.strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    d = re.sub(r"^doi:\s*", "", d)
    return d or None


# ----------------------------------------------------------------------------
# PubMed
# ----------------------------------------------------------------------------

def pubmed_search(f: Fetcher, term: str, retmax: int = 50, mindate: str | None = None, sort: str = "relevance") -> tuple[list[str], dict[str, Any]]:
    """Return (pmids, meta). meta includes PubMed's own query translation so the
    exact executed query is auditable."""
    params: dict[str, Any] = {"db": "pubmed", "term": term, "retmode": "json", "retmax": retmax, "sort": sort}
    if mindate:
        params["mindate"] = mindate
        params["datetype"] = "pdat"
    key = os.environ.get("NCBI_API_KEY")
    if key:
        params["api_key"] = key
    url = build_url(f"{PUBMED}/esearch.fcgi", params)
    data = f.get_json(url)
    res = data.get("esearchresult", {})
    meta = {
        "db": "pubmed",
        "url": _redact(url),
        "query": term,
        "query_translation": res.get("querytranslation"),
        "count": int(res.get("count", 0) or 0),
        "returned": len(res.get("idlist", [])),
    }
    return list(res.get("idlist", [])), meta


def pubmed_fetch(f: Fetcher, pmids: list[str]) -> list[dict[str, Any]]:
    """Fetch full PubMed records (XML) in batches of 100 and normalise."""
    out: list[dict[str, Any]] = []
    for i in range(0, len(pmids), 100):
        batch = pmids[i:i + 100]
        params: dict[str, Any] = {"db": "pubmed", "id": ",".join(batch), "retmode": "xml"}
        key = os.environ.get("NCBI_API_KEY")
        if key:
            params["api_key"] = key
        xml = f.get(build_url(f"{PUBMED}/efetch.fcgi", params))
        out.extend(_parse_pubmed_xml(xml))
    return out


def _parse_pubmed_xml(xml: str) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return recs
    for art in root.iter("PubmedArticle"):
        med = art.find("MedlineCitation")
        if med is None:
            continue
        pmid = (med.findtext("PMID") or "").strip() or None
        article = med.find("Article")
        if article is None:
            continue
        title = "".join(article.find("ArticleTitle").itertext()).strip() if article.find("ArticleTitle") is not None else None
        # abstract: join labelled sections
        abs_parts = []
        for ab in article.findall("Abstract/AbstractText"):
            label = ab.get("Label")
            text = "".join(ab.itertext()).strip()
            abs_parts.append(f"{label}: {text}" if label else text)
        abstract = "\n".join(abs_parts) or None
        authors = []
        for a in article.findall("AuthorList/Author"):
            ln = a.findtext("LastName")
            ini = a.findtext("Initials") or ""
            coll = a.findtext("CollectiveName")
            if ln:
                authors.append(f"{ln} {ini}".strip())
            elif coll:
                authors.append(coll)
        year = None
        for path in ("Journal/JournalIssue/PubDate/Year", "Journal/JournalIssue/PubDate/MedlineDate", "ArticleDate/Year"):
            y = article.findtext(path)
            if y:
                m = re.search(r"\d{4}", y)
                if m:
                    year = int(m.group(0))
                    break
        journal = article.findtext("Journal/Title") or article.findtext("Journal/ISOAbbreviation")
        pub_types = [pt.text.strip() for pt in article.findall("PublicationTypeList/PublicationType") if pt.text]
        doi = None
        pmcid = None
        for aid in art.findall("PubmedData/ArticleIdList/ArticleId"):
            if aid.get("IdType") == "doi" and aid.text:
                doi = norm_doi(aid.text)
            if aid.get("IdType") == "pmc" and aid.text:
                pmcid = aid.text.strip()
        if doi is None:
            for eid in article.findall("ELocationID"):
                if eid.get("EIdType") == "doi" and eid.text:
                    doi = norm_doi(eid.text)
        mesh = [mh.findtext("DescriptorName") for mh in med.findall("MeshHeadingList/MeshHeading") if mh.findtext("DescriptorName")]
        comments = []
        for cc in med.findall("CommentsCorrectionsList/CommentsCorrections"):
            comments.append({"type": cc.get("RefType"), "pmid": cc.findtext("PMID"), "ref": cc.findtext("RefSource")})
        is_retracted = "Retracted Publication" in pub_types or any(c["type"] == "RetractionIn" for c in comments)
        notice = next((c for c in comments if c["type"] == "RetractionIn"), None)
        concerns = [c for c in comments if c["type"] in ("ExpressionOfConcernIn", "ErratumIn", "RetractionOf", "UpdateIn")]
        recs.append(new_record(
            source="pubmed", pmid=pmid, pmcid=pmcid, doi=doi, title=title, authors=authors, year=year,
            journal=journal, pub_types=pub_types, abstract=abstract, abstract_source="pubmed" if abstract else None,
            is_retracted=is_retracted, retraction_notice=notice, mesh=mesh,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
            comments=comments, integrity_flags=[c["type"] for c in concerns],
        ))
    return recs


# ----------------------------------------------------------------------------
# OpenAlex
# ----------------------------------------------------------------------------

OA_SELECT = "id,doi,title,display_name,publication_year,type,cited_by_count,is_retracted,authorships,primary_location,open_access,referenced_works,abstract_inverted_index,ids"


def openalex_search(f: Fetcher, query: str, per_page: int = 50, filters: str | None = None, sort: str | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params: dict[str, Any] = {"search": query, "per-page": per_page, "select": OA_SELECT, "mailto": f.mailto}
    if filters:
        params["filter"] = filters
    if sort:
        params["sort"] = sort
    key = os.environ.get("OPENALEX_API_KEY")
    if key:
        params["api_key"] = key
    url = build_url(f"{OPENALEX}/works", params)
    data = f.get_json(url)
    meta = {"db": "openalex", "url": _redact(url), "query": query, "filter": filters,
            "count": data.get("meta", {}).get("count"), "returned": len(data.get("results", []))}
    return [_parse_openalex(w) for w in data.get("results", [])], meta


def openalex_work(f: Fetcher, ident: str) -> dict[str, Any] | None:
    """ident: 'doi:10...' or 'pmid:123' or 'W123'."""
    params: dict[str, Any] = {"select": OA_SELECT, "mailto": f.mailto}
    key = os.environ.get("OPENALEX_API_KEY")
    if key:
        params["api_key"] = key
    try:
        data = f.get_json(build_url(f"{OPENALEX}/works/{ident}", params))
    except Exception:
        return None
    return _parse_openalex(data) if data and data.get("id") else None


def _invert(idx: dict[str, list[int]] | None) -> str | None:
    if not idx:
        return None
    pos: dict[int, str] = {}
    for word, places in idx.items():
        for p in places:
            pos[p] = word
    return " ".join(pos[i] for i in sorted(pos)) or None


def _parse_openalex(w: dict[str, Any]) -> dict[str, Any]:
    ids = w.get("ids", {}) or {}
    pmid = ids.get("pmid")
    if pmid:
        pmid = pmid.rsplit("/", 1)[-1]
    pmcid = ids.get("pmcid")
    if pmcid:
        pmcid = pmcid.rsplit("/", 1)[-1]
    loc = w.get("primary_location") or {}
    src = (loc.get("source") or {})
    return new_record(
        source="openalex",
        openalex_id=(w.get("id") or "").rsplit("/", 1)[-1] or None,
        doi=norm_doi(w.get("doi")),
        pmid=pmid, pmcid=pmcid,
        title=w.get("title") or w.get("display_name"),
        authors=[(a.get("author") or {}).get("display_name") for a in (w.get("authorships") or []) if (a.get("author") or {}).get("display_name")],
        year=w.get("publication_year"),
        journal=src.get("display_name"),
        pub_types=[w.get("type")] if w.get("type") else [],
        abstract=_invert(w.get("abstract_inverted_index")),
        abstract_source="openalex_inverted" if w.get("abstract_inverted_index") else None,
        cited_by_count=w.get("cited_by_count"),
        is_retracted=bool(w.get("is_retracted")),
        has_full_text_oa=bool((w.get("open_access") or {}).get("is_oa")),
        referenced_works=[r.rsplit("/", 1)[-1] for r in (w.get("referenced_works") or [])],
        url=w.get("doi") or w.get("id"),
    )


# ----------------------------------------------------------------------------
# Crossref (DOI resolution + retraction/update metadata)
# ----------------------------------------------------------------------------

def crossref_work(f: Fetcher, doi: str) -> dict[str, Any] | None:
    doi = norm_doi(doi)
    if not doi:
        return None
    url = build_url(f"{CROSSREF}/works/{doi}", {"mailto": f.mailto})
    try:
        data = f.get_json(url)
    except Exception:
        return None
    m = data.get("message") or {}
    if not m:
        return None
    title = (m.get("title") or [None])[0]
    year = None
    for k in ("published-print", "published-online", "issued", "created"):
        dp = (m.get(k) or {}).get("date-parts")
        if dp and dp[0] and dp[0][0]:
            year = dp[0][0]
            break
    updates = m.get("update-to") or []
    retraction = next((u for u in updates if (u.get("type") or "").lower() in ("retraction", "retracted", "withdrawal")), None)
    return new_record(
        source="crossref", doi=doi, title=title,
        authors=[f"{a.get('family','')} {a.get('given','')}".strip() for a in (m.get("author") or []) if a.get("family")],
        year=year, journal=(m.get("container-title") or [None])[0],
        pub_types=[m.get("type")] if m.get("type") else [],
        is_retracted=retraction is not None or (m.get("type") == "retraction"),
        retraction_notice=retraction, cited_by_count=m.get("is-referenced-by-count"),
        url=m.get("URL"), crossref_updates=updates,
    )


def crossref_search(f: Fetcher, bibliographic: str, rows: int = 5) -> list[dict[str, Any]]:
    url = build_url(f"{CROSSREF}/works", {"query.bibliographic": bibliographic, "rows": rows, "mailto": f.mailto,
                                           "select": "DOI,title,author,issued,container-title,type,is-referenced-by-count,URL"})
    try:
        data = f.get_json(url)
    except Exception:
        return []
    items = (data.get("message") or {}).get("items") or []
    out = []
    for m in items:
        dp = ((m.get("issued") or {}).get("date-parts") or [[None]])[0]
        out.append(new_record(
            source="crossref", doi=norm_doi(m.get("DOI")), title=(m.get("title") or [None])[0],
            authors=[f"{a.get('family','')} {a.get('given','')}".strip() for a in (m.get("author") or []) if a.get("family")],
            year=dp[0] if dp else None, journal=(m.get("container-title") or [None])[0],
            pub_types=[m.get("type")] if m.get("type") else [], cited_by_count=m.get("is-referenced-by-count"), url=m.get("URL"),
        ))
    return out


# ----------------------------------------------------------------------------
# Europe PMC (alternative index; full-text availability; citations)
# ----------------------------------------------------------------------------

def europepmc_search(f: Fetcher, query: str, page_size: int = 50) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    url = build_url(f"{EUROPEPMC}/search", {"query": query, "format": "json", "pageSize": page_size, "resultType": "lite"})
    data = f.get_json(url)
    hits = data.get("resultList", {}).get("result", [])
    meta = {"db": "europepmc", "url": url, "query": query, "count": data.get("hitCount"), "returned": len(hits)}
    out = []
    for h in hits:
        out.append(new_record(
            source="europepmc", pmid=h.get("pmid"), pmcid=h.get("pmcid"), doi=norm_doi(h.get("doi")), title=h.get("title"),
            authors=[a.strip() for a in (h.get("authorString") or "").rstrip(".").split(",") if a.strip()],
            year=int(h["pubYear"]) if h.get("pubYear") else None, journal=h.get("journalTitle"),
            pub_types=h.get("pubType", "").split("; ") if h.get("pubType") else [],
            cited_by_count=h.get("citedByCount"), has_full_text_oa=(h.get("isOpenAccess") == "Y"),
            url=f"https://europepmc.org/abstract/{h.get('source')}/{h.get('id')}" if h.get("id") else None,
        ))
    return out, meta


# ----------------------------------------------------------------------------
# Semantic Scholar (optional; strict unauthenticated rate limits)
# ----------------------------------------------------------------------------

def s2_search(f: Fetcher, query: str, limit: int = 20) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    url = build_url(f"{S2}/paper/search", {"query": query, "limit": limit,
                                           "fields": "title,year,externalIds,citationCount,publicationTypes,abstract,authors,venue"})
    headers = {"x-api-key": os.environ["S2_API_KEY"]} if os.environ.get("S2_API_KEY") else None
    data = f.get_json(url, headers)
    hits = data.get("data", [])
    meta = {"db": "semanticscholar", "url": url, "query": query, "count": data.get("total"), "returned": len(hits)}
    out = []
    for h in hits:
        ext = h.get("externalIds") or {}
        out.append(new_record(
            source="semanticscholar", doi=norm_doi(ext.get("DOI")), pmid=ext.get("PubMed"), title=h.get("title"),
            authors=[a.get("name") for a in (h.get("authors") or []) if a.get("name")], year=h.get("year"), journal=h.get("venue"),
            pub_types=h.get("publicationTypes") or [], abstract=h.get("abstract"), abstract_source="s2" if h.get("abstract") else None,
            cited_by_count=h.get("citationCount"), url=f"https://www.semanticscholar.org/paper/{h.get('paperId')}" if h.get("paperId") else None,
        ))
    return out, meta


def _redact(url: str) -> str:
    return re.sub(r"(api_key=)[^&]+", r"\1<redacted>", url)


# ----------------------------------------------------------------------------
# Scite public tallies (free, no key). Advisory only: an independent evaluation
# (Bakker et al. 2023, doi:10.18060/26528) found low recall for "contrasting"
# citations, so a zero count is NOT evidence of consensus.
# ----------------------------------------------------------------------------

SCITE = "https://api.scite.ai"


def scite_tally(f: Fetcher, doi: str) -> dict[str, Any] | None:
    doi = norm_doi(doi)
    if not doi:
        return None
    try:
        data = f.get_json(f"{SCITE}/tallies/{doi}")
    except Exception:
        return None
    if not isinstance(data, dict) or "total" not in data:
        return None
    return {"supporting": data.get("supporting"), "contrasting": data.get("contradicting", data.get("contrasting")),
            "mentioning": data.get("mentioning"), "total": data.get("total"),
            "caveat": "citation-statement classifier; contrasting recall ~0.45 in vendor data and lower in independent evaluation"}
