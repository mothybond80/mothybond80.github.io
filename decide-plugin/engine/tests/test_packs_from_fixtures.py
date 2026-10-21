"""End-to-end determinism and leak tests against recorded API responses."""
import json
from pathlib import Path

import pytest

from decide_engine.fetch import Fetcher
from decide_engine.pack import asker_block, build_pack
from decide_engine.question import parse_question

CACHE = Path(__file__).parent / "fixtures" / "cache"
FRAMINGS = {
    "creatine": ["Does creatine improve cognitive performance?", "Does creatine reduce cognitive performance?", "Isn't creatine actually great for brain function?"],
    "red_meat": ["Does red meat increase lifespan?", "Does red meat reduce lifespan?", "Isn't red meat actually good for longevity?"],
}
LEAK_WORDS = ("improve", "reduce cognitive", "great for", "good for", "isn't", "increase lifespan", "reduce lifespan", "actually")


def _pack(q: str):
    pq = parse_question(q)
    return build_pack(q, mode="quick", fetcher=Fetcher(cache_dir=CACHE, offline=True), pq=pq), pq


@pytest.mark.parametrize("subject", sorted(FRAMINGS))
def test_identical_packs_across_framings(subject):
    packs = [_pack(q) for q in FRAMINGS[subject]]
    hashes = {p["pack_hash"] for p, _ in packs}
    assert len(hashes) == 1
    assert all(not p["missing_urls"] for p, _ in packs), [p["missing_urls"] for p, _ in packs]
    assert packs[0][0]["n_records"] > 50
    assert packs[0][0]["relevance_tiers"]["A"] >= 10


@pytest.mark.parametrize("subject", sorted(FRAMINGS))
def test_pack_contains_no_asker_information(subject):
    for q in FRAMINGS[subject]:
        pack, pq = _pack(q)
        blob = json.dumps({k: v for k, v in pack.items() if k != "records"}).lower()
        assert q.lower() not in blob
        for w in LEAK_WORDS:
            assert w not in blob, (q, w)
        a = asker_block(pq)
        assert a["raw_question"] == q and a["asker_direction"] in ("benefit", "harm", "neutral")


def test_creatine_pack_finds_key_syntheses_and_flags_overlap():
    pack, _ = _pack("Does creatine improve cognitive performance?")
    dois = {r.get("doi") for r in pack["records"]}
    for doi in ("10.1093/nutrit/nuac064", "10.3389/fnut.2024.1424972", "10.1016/j.exger.2018.04.013", "10.1016/j.bbr.2024.114982"):
        assert doi in dois, doi
    # the double-counting letter about the 2023 memory meta-analysis must be present and kept
    assert any("double-counting" in (r.get("title") or "").lower() for r in pack["records"])
    assert pack["overlap_warnings"], "reference-list overlap between creatine syntheses should be flagged"
    top = [r for r in pack["records"][:12]]
    assert all(r["relevance"]["tier"] == "A" for r in top)
    assert all(r["classification"]["is_synthesis"] for r in top[:8])


def test_red_meat_pack_has_observational_designs():
    pack, _ = _pack("Does red meat increase lifespan?")
    assert pack["limits"]["pubmed_obs"] > 0, "nutrition questions must search observational designs even in quick mode"
    kinds = pack["study_type_counts"]
    assert kinds.get("cohort", 0) + kinds.get("longitudinal", 0) + kinds.get("cross_sectional", 0) >= 5
    assert any("burden of proof" in (r.get("title") or "").lower() for r in pack["records"])
