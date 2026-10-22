"""Optional MCP wrapper over the decide engine, for agents such as Hermes that
speak MCP rather than running a CLI. Exposes the *deterministic* layer only;
appraisal is done by the calling model following the contract in the pack.

Install (optional extra):   uv pip install -e ".[mcp]"
Run (stdio):                python mcp_server.py
Hermes config (~/.hermes/config.yaml, mcp_servers section) example in ../hermes/README.md
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from decide_engine.fetch import Fetcher  # noqa: E402
from decide_engine.pack import asker_block, build_pack  # noqa: E402
from decide_engine.question import parse_question, search_strategy, _clean_concept, framing_hash  # noqa: E402
from decide_engine.verify import verify_citation  # noqa: E402

try:
    from mcp.server.fastmcp import FastMCP  # mcp 1.x
except ImportError:  # pragma: no cover
    from mcp.server.mcpserver import MCPServer as FastMCP  # mcp 2.x naming

RUNS = Path(os.environ.get("DECIDE_RUNS_DIR", Path.home() / ".decide"))
mcp = FastMCP("decide-engine")


@mcp.tool()
def decide_parse(question: str) -> dict[str, Any]:
    """Neutralise a possibly leading question into a direction-free research question, PICO
    and search strategy. Returns no information about the asker's framing."""
    pq = parse_question(question)
    d = pq.to_dict()
    for k in ("raw", "cleaned", "asker_direction"):
        d.pop(k, None)
    return {"parsed": d, "search_strategy": search_strategy(pq)}


@mcp.tool()
def decide_search(question: str, mode: str = "quick", exposure: str = "", outcome: str = "", population: str = "") -> dict[str, Any]:
    """Build an evidence pack (PubMed, OpenAlex, Crossref, Europe PMC) for the neutralised question.
    Writes pack.json (+ pack.asker.json kept separate) under DECIDE_RUNS_DIR and returns a summary
    with the file path. The caller must then appraise the pack following its appraiser_contract,
    in a context that has not seen the asker's wording."""
    pq = parse_question(question)
    if exposure or outcome or population:
        if exposure:
            pq.exposure = _clean_concept(exposure)
        if outcome:
            pq.outcome = _clean_concept(outcome)
        if population:
            pq.population = population
        pq.framing_hash = framing_hash(pq)
    f = Fetcher()
    pack = build_pack(question, mode=mode, fetcher=f, pq=pq)
    run = RUNS / f"{pack['built_at'].replace(':', '').replace('-', '')}-{pq.framing_hash}"
    run.mkdir(parents=True, exist_ok=True)
    (run / "pack.json").write_text(json.dumps(pack, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (run / "pack.asker.json").write_text(json.dumps(asker_block(pq), indent=1), encoding="utf-8")
    return {"pack_file": str(run / "pack.json"), "neutral_question": pq.neutral_question, "n_records": pack["n_records"],
            "relevance_tiers": pack["relevance_tiers"], "study_type_counts": pack["study_type_counts"],
            "retracted_or_flagged": pack["retracted_or_flagged"], "errors": pack["errors"], "pack_hash": pack["pack_hash"]}


@mcp.tool()
def decide_pack_records(pack_file: str, tiers: str = "AB", max_records: int = 60, with_abstracts: bool = True) -> dict[str, Any]:
    """Return records from an evidence pack (for appraisal), filtered by relevance tier."""
    pack = json.loads(Path(pack_file).read_text(encoding="utf-8"))
    recs = [r for r in pack["records"] if r["relevance"]["tier"] in tiers][:max_records]
    keep = ("ref", "title", "authors", "year", "journal", "doi", "pmid", "classification", "relevance", "is_retracted", "integrity_flags",
            "cited_by_count", "scite_tally", "has_full_text_oa", "url") + (("abstract", "abstract_source") if with_abstracts else ())
    return {"question": pack["question"], "domain_guidance": pack["domain_guidance"], "searches": pack["searches"], "errors": pack["errors"],
            "overlap_warnings": pack["overlap_warnings"], "appraiser_contract": pack["appraiser_contract"],
            "records": [{k: r.get(k) for k in keep} for r in recs]}


@mcp.tool()
def decide_verify(citations: list[dict[str, Any]], pack_file: str = "") -> list[dict[str, Any]]:
    """Verify citations ({title, year, first_author, doi, pmid}) against Crossref/PubMed/OpenAlex,
    including retraction status. Verdicts: verified | resolved_by_search | title_mismatch | not_found | retracted."""
    f = Fetcher()
    recs = json.loads(Path(pack_file).read_text(encoding="utf-8")).get("records", []) if pack_file else None
    out = []
    for c in citations:
        r = verify_citation(f, c, recs)
        res = r.get("resolved") or {}
        out.append({"verdict": r["verdict"], "via": r.get("via"), "title_similarity": r.get("title_similarity"), "checks": r["checks"],
                    "claimed": r["claimed"], "resolved": {k: res.get(k) for k in ("title", "authors", "year", "journal", "doi", "pmid", "is_retracted")} if res else None})
    return out


@mcp.tool()
def decide_lock(file: str) -> dict[str, str]:
    """SHA-256 of a file, used to lock the evidence appraisal before decision analysis."""
    import hashlib
    return {"file": file, "sha256": hashlib.sha256(Path(file).read_bytes()).hexdigest()}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
