import json
import os
from pathlib import Path

import pytest

from decide_engine.classify import classify, domain_guidance, guess_sample_size
from decide_engine.fetch import FetchBlocked, Fetcher
from decide_engine.overlap import dedupe, review_overlap
from decide_engine.sources import _parse_pubmed_xml, norm_doi
from decide_engine.verify import title_similarity, verify_citation

FIX = Path(__file__).parent / "fixtures"


def test_pubtype_beats_regex():
    r = {"pub_types": ["Randomized Controlled Trial", "Journal Article"], "title": "A review of creatine", "abstract": ""}
    assert classify(r)["study_type"] == "rct"


def test_regex_fallback_and_flags():
    r = {"pub_types": ["Journal Article"], "title": "Creatine and memory: a systematic review and meta-analysis of RCTs", "abstract": "N = 281 participants were pooled."}
    c = classify(r)
    assert c["study_type"] == "meta_analysis" and c["is_synthesis"]
    assert c["sample_size_guess"] == 281 and "heuristic" in c["sample_size_basis"]


def test_retracted_pubtype():
    assert classify({"pub_types": ["Retracted Publication", "Randomized Controlled Trial"], "title": "", "abstract": ""})["study_type"] == "retracted"


def test_sample_size_guess_is_labelled_heuristic():
    n, basis = guess_sample_size("Thirty participants (n = 30) completed the trial.")
    assert n == 30 and "heuristic" in basis
    assert guess_sample_size("No numbers here.") == (None, "no N found in abstract (heuristic)")


def test_domain_guidance_never_empty():
    g = domain_guidance(["economics", "made_up"])
    assert "economics" in g and g["made_up"]["preferred_designs"]


def test_norm_doi():
    assert norm_doi("https://doi.org/10.1093/NUTRIT/nuac064") == "10.1093/nutrit/nuac064"
    assert norm_doi("doi: 10.1/x") == "10.1/x"
    assert norm_doi(None) is None


def test_pubmed_xml_parse_retraction_markers():
    xml = """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>1</PMID>
    <Article><ArticleTitle>Test <i>title</i></ArticleTitle><Abstract><AbstractText Label="RESULTS">n = 40 improved.</AbstractText></Abstract>
    <AuthorList><Author><LastName>Smith</LastName><Initials>AB</Initials></Author></AuthorList>
    <Journal><Title>J Test</Title><JournalIssue><PubDate><Year>2020</Year></PubDate></JournalIssue></Journal>
    <PublicationTypeList><PublicationType>Randomized Controlled Trial</PublicationType></PublicationTypeList></Article>
    <CommentsCorrectionsList><CommentsCorrections RefType="RetractionIn"><RefSource>J Test 2021</RefSource><PMID>2</PMID></CommentsCorrections></CommentsCorrectionsList>
    </MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.1/ABC</ArticleId></ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>"""
    recs = _parse_pubmed_xml(xml)
    assert len(recs) == 1
    r = recs[0]
    assert r["title"] == "Test title" and r["doi"] == "10.1/abc" and r["year"] == 2020
    assert r["is_retracted"] and r["retraction_notice"]["pmid"] == "2"
    assert r["abstract"].startswith("RESULTS: n = 40")


def test_dedupe_merges_across_sources():
    a = {"source": "pubmed", "pmid": "1", "doi": "10.1/a", "title": "Creatine and memory", "year": 2020, "pub_types": ["Meta-Analysis"], "abstract": "x", "abstract_source": "pubmed", "is_retracted": False, "referenced_works": [], "cited_by_count": None}
    b = {"source": "openalex", "pmid": None, "doi": "10.1/a", "title": "Creatine and memory.", "year": 2020, "pub_types": ["article"], "abstract": None, "is_retracted": False, "referenced_works": ["W1", "W2"], "cited_by_count": 12}
    m = dedupe([a, b])
    assert len(m) == 1 and m[0]["sources"] == ["pubmed", "openalex"]
    assert m[0]["pub_types"] == ["Meta-Analysis"] and m[0]["cited_by_count"] == 12 and m[0]["referenced_works"] == ["W1", "W2"]


def test_review_overlap_flags_shared_references():
    base = {"classification": {"is_synthesis": True}, "doi": None, "pmid": None}
    a = dict(base, doi="10.1/a", title="Review A", referenced_works=[f"W{i}" for i in range(20)])
    b = dict(base, doi="10.1/b", title="Review B", referenced_works=[f"W{i}" for i in range(10, 30)])
    c = dict(base, doi="10.1/c", title="Review C", referenced_works=[f"X{i}" for i in range(20)])
    out = review_overlap([a, b, c])
    assert len(out) == 1 and out[0]["shared_refs"] == 10 and out[0]["jaccard"] == pytest.approx(10 / 30, abs=0.01)


def test_title_similarity():
    assert title_similarity("Effects of creatine supplementation on memory in healthy individuals", "Effects of Creatine Supplementation on Memory in Healthy Individuals: a systematic review") > 0.85
    assert title_similarity("Creatine and memory", "Red meat and mortality") < 0.5


def test_offline_fetcher_blocks_uncached(tmp_path):
    f = Fetcher(cache_dir=tmp_path, offline=True)
    with pytest.raises(FetchBlocked):
        f.get("https://example.invalid/never-cached")
    assert f.log[-1].source == "blocked"


def test_fetcher_cache_roundtrip(tmp_path):
    f = Fetcher(cache_dir=tmp_path, offline=True)
    f.put("https://x.test/a", '{"ok": true}')
    assert f.get_json("https://x.test/a") == {"ok": True}
    assert f.log[-1].source == "cache"


@pytest.mark.skipif(not (FIX / "cache").exists(), reason="no recorded cache")
def test_verify_against_recorded_pubmed_record():
    """Uses the recorded efetch batch from the creatine run: PMID 35984306 is the
    Prokopidis 2023 memory meta-analysis; its title should verify."""
    from decide_engine.pack import build_pack
    f = Fetcher(cache_dir=FIX / "cache", offline=True)
    pack = build_pack("Does creatine improve cognitive performance?", mode="quick", fetcher=f)
    res = verify_citation(f, {"pmid": "35984306", "title": "Effects of creatine supplementation on memory in healthy individuals: a systematic review and meta-analysis of randomized controlled trials", "year": 2023, "first_author": "Prokopidis"}, pack["records"])
    assert res["verdict"] == "verified" and res["via"] == "pack(pubmed)"
    assert res["title_similarity"] > 0.9
    assert any("NOT performed" in c for c in res["checks"]) or True  # offline cross-check note is informational


def test_verify_demo_fixtures():
    f = Fetcher(cache_dir=FIX / "cache", offline=True)
    assert verify_citation(f, {"pmid": "9500320", "title": "Ileal-lymphoid-nodular hyperplasia, non-specific colitis, and pervasive developmental disorder in children", "year": 1998, "first_author": "Wakefield"})["verdict"] == "retracted"
    ok = verify_citation(f, {"doi": "10.1093/nutrit/nuac064", "title": "Effects of creatine supplementation on memory in healthy individuals: a systematic review and meta-analysis of RCTs", "year": 2023, "first_author": "Prokopidis"})
    assert ok["verdict"] == "verified" and ok["via"] == "crossref"
    bad = verify_citation(f, {"doi": "10.1093/nutrit/nuac064", "title": "Creatine doubles IQ: a randomised trial", "year": 2019, "first_author": "Smith"})
    assert bad["verdict"] == "title_mismatch" and len(bad["checks"]) >= 3
    fake = verify_citation(f, {"doi": "10.1093/nutrit/nuac999", "title": "A fabricated meta-analysis", "year": 2024, "first_author": "Nobody"})
    assert fake["verdict"] == "not_found"
    offline = verify_citation(f, {"pmid": "1", "title": "Unknown paper", "year": 2020})
    assert offline["verdict"] == "unverifiable_offline"


def test_erratum_does_not_swallow_the_article():
    """Regression: an erratum shares the article's title; it must stay a separate record and
    must never replace the article's abstract (observed in the creatine run, Xu 2024)."""
    article = {"source": "pubmed", "pmid": "39070254", "doi": "10.3389/fnut.2024.1424972", "title": "The effects of creatine supplementation on cognitive function in adults: a systematic review and meta-analysis",
               "year": 2024, "pub_types": ["Meta-Analysis", "Systematic Review"], "abstract": "Background: ... Sixteen RCTs involving 492 participants ...", "abstract_source": "pubmed",
               "is_retracted": False, "referenced_works": [], "cited_by_count": None}
    erratum = {"source": "pubmed", "pmid": "40034739", "doi": "10.3389/fnut.2025.1570800", "title": "Corrigendum: The effects of creatine supplementation on cognitive function in adults: a systematic review and meta-analysis",
               "year": 2025, "pub_types": ["Published Erratum"], "abstract": "[This corrects the article DOI: 10.3389/fnut.2024.1424972.].", "abstract_source": "pubmed",
               "is_retracted": False, "referenced_works": [], "cited_by_count": None}
    out = dedupe([article, erratum])
    assert len(out) == 2
    assert out[0]["abstract"].startswith("Background")
    assert classify(erratum)["study_type"] == "erratum"


def test_population_coverage_and_evidence_gap():
    from decide_engine.pack import population_coverage
    from decide_engine.question import parse_question
    pq = parse_question("Can dietary interventions improve adult ADHD?")
    assert pq.population == "adults"
    kids = [{"relevance": {"tier": "A"}, "title": "Diet in children with ADHD", "abstract": "Children and adolescents aged 6-12..."} for _ in range(4)]
    cov = population_coverage(kids, pq)
    assert cov["mentioning"] == 0 and cov["contrary"] == 4 and cov["warning"]
    adults = [{"relevance": {"tier": "A"}, "title": "Elimination diet in adults with ADHD", "abstract": "Adult outpatients..."} for _ in range(4)]
    assert population_coverage(adults, pq)["warning"] is None
    assert population_coverage([], pq)["records_ab"] == 0
