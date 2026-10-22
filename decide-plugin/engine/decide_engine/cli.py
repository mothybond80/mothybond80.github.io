"""Command-line interface. All commands print JSON to stdout unless --md.

  decide-engine parse  "question"                       neutralise + strategy (no network)
  decide-engine plan   "question" [--mode quick|deep]   URLs the search would need (no network)
  decide-engine search "question" [--mode] [--out F]    build the evidence pack
  decide-engine digest pack.json [--out digest.md]      compact Markdown view for the appraiser
  decide-engine verify (--doi D | --pmid P | --title T [--year Y --author A]) | --file citations.json
  decide-engine lock   FILE                              sha256 of a file (evidence-lock)
  decide-engine cache-put URL FILE                       store a response fetched elsewhere
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from .fetch import Fetcher
from .pack import asker_block, build_pack
from .question import parse_question, search_strategy
from .sources import OPENALEX, PUBMED, build_url
from .verify import verify_citation


def _fetcher(args: argparse.Namespace) -> Fetcher:
    kw = {}
    if getattr(args, "cache_dir", None):
        kw["cache_dir"] = Path(args.cache_dir)
    if getattr(args, "offline", False):
        kw["offline"] = True
    return Fetcher(**kw)


def cmd_parse(args: argparse.Namespace) -> int:
    pq = parse_question(args.question)
    out = {"parsed": pq.to_dict(), "search_strategy": search_strategy(pq)}
    if args.hide_asker:
        out["parsed"].pop("raw", None)
        out["parsed"].pop("asker_direction", None)
        out["parsed"].pop("cleaned", None)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    """List the first-round URLs so they can be fetched by another tool and cached."""
    from .pack import MODE_LIMITS
    pq = parse_question(args.question)
    s = search_strategy(pq)
    lim = MODE_LIMITS[args.mode]
    urls = []
    for label, key, n in (("pubmed_reviews", "reviews", lim["pubmed_reviews"]), ("pubmed_trials", "trials", lim["pubmed_trials"]),
                          ("pubmed_observational", "observational", lim["pubmed_obs"])):
        if n:
            urls.append({"label": label, "url": build_url(f"{PUBMED}/esearch.fcgi", {"db": "pubmed", "term": s["pubmed"][key], "retmode": "json", "retmax": n, "sort": "relevance"})})
    import time
    yr = time.gmtime().tm_year - 3
    urls.append({"label": "pubmed_recent", "url": build_url(f"{PUBMED}/esearch.fcgi", {"db": "pubmed", "term": s["pubmed"]["recent_any"], "retmode": "json", "retmax": lim["pubmed_recent"], "sort": "pub_date", "mindate": f"{yr}/01/01", "datetype": "pdat"})})
    from .sources import OA_SELECT
    f = _fetcher(args)
    urls.append({"label": "openalex_most_cited", "url": build_url(f"{OPENALEX}/works", {"search": s["openalex"]["query"], "per-page": lim["openalex"], "select": OA_SELECT, "mailto": f.mailto, "sort": "cited_by_count:desc"})})
    print(json.dumps({"framing_hash": pq.framing_hash, "note": "After caching these, run `search --offline`; it will list further URLs (efetch, openalex works) it still needs.", "urls": urls}, indent=2))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    f = _fetcher(args)
    pq = parse_question(args.question)
    if args.exposure or args.outcome or args.population:
        # LLM-corrected PICO overrides the heuristic. Direction words are still stripped.
        from .question import _clean_concept, framing_hash
        if args.exposure:
            pq.exposure = _clean_concept(args.exposure)
        if args.outcome:
            pq.outcome = _clean_concept(args.outcome)
        if args.population:
            pq.population = args.population
        pq.neutral_question = f"What is the effect of {pq.exposure} on {pq.outcome}" + (f" in {pq.population}" if pq.population else "") + ", and in which direction?"
        pq.framing_hash = framing_hash(pq)
        pq.notes.append("PICO overridden by caller")
    pack = build_pack(args.question, mode=args.mode, fetcher=f, pq=pq)
    missing = pack["missing_urls"]
    out = Path(args.out) if args.out else None
    if out:
        out.write_text(json.dumps(pack, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        ask = out.with_name(out.stem + ".asker.json")
        ask.write_text(json.dumps(asker_block(pq), indent=1), encoding="utf-8")
        from .digest import digest
        dg = out.with_name("digest.md")
        dg.write_text(digest(pack), encoding="utf-8")
        summary = {k: pack[k] for k in ("mode", "question", "n_records", "relevance_tiers", "study_type_counts", "retracted_or_flagged", "errors", "pack_hash", "fetch_log_summary", "optional_missing_urls")}
        summary["overlap_warnings"] = len(pack["overlap_warnings"])
        summary["pack_file"] = str(out)
        summary["asker_file"] = str(ask)
        summary["digest_file"] = str(dg)
        summary["missing_urls"] = missing
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(pack, indent=1, ensure_ascii=False, default=str))
    return 0 if not missing else 3


def cmd_verify(args: argparse.Namespace) -> int:
    f = _fetcher(args)
    items = []
    if args.file:
        items = json.loads(Path(args.file).read_text(encoding="utf-8"))
        if isinstance(items, dict):
            items = items.get("citations", [])
    else:
        items = [{"doi": args.doi, "pmid": args.pmid, "title": args.title, "year": args.year, "first_author": args.author}]
    pack_records = None
    if args.pack:
        pack_records = json.loads(Path(args.pack).read_text(encoding="utf-8")).get("records", [])
    results = [verify_citation(f, c, pack_records) for c in items]
    slim = []
    for r in results:
        res = r.get("resolved") or {}
        slim.append({"verdict": r["verdict"], "via": r.get("via"), "title_similarity": r.get("title_similarity"), "checks": r["checks"],
                     "claimed": r["claimed"],
                     "resolved": {k: res.get(k) for k in ("title", "authors", "year", "journal", "doi", "pmid", "pub_types", "is_retracted", "abstract")} if res else None})
    print(json.dumps(slim, indent=2, ensure_ascii=False, default=str))
    if any(r["verdict"] == "unverifiable_offline" for r in results):
        return 3
    return 0 if all(r["verdict"] in ("verified", "resolved_by_search") for r in results) else 2


def cmd_digest(args: argparse.Namespace) -> int:
    from .digest import digest
    pack = json.loads(Path(args.pack).read_text(encoding="utf-8"))
    md = digest(pack, tier_b_chars=args.tier_b_chars, max_c=args.max_c)
    out = Path(args.out) if args.out else Path(args.pack).with_name("digest.md")
    out.write_text(md, encoding="utf-8")
    print(json.dumps({"digest": str(out), "chars": len(md), "records": pack["n_records"], "tiers": pack["relevance_tiers"]}))
    return 0


def cmd_lock(args: argparse.Namespace) -> int:
    h = hashlib.sha256(Path(args.file).read_bytes()).hexdigest()
    print(json.dumps({"file": args.file, "sha256": h}))
    return 0


def cmd_cache_put(args: argparse.Namespace) -> int:
    f = _fetcher(args)
    body = Path(args.file).read_text(encoding="utf-8")
    f.put(args.url, body)
    print(json.dumps({"cached": args.url, "key": f.key(args.url), "bytes": len(body)}))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="decide-engine", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cache-dir", default=os.environ.get("DECIDE_CACHE_DIR"))
    p.add_argument("--offline", action="store_true", help="never touch the network; fail on uncached URLs")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("parse"); s.add_argument("question"); s.add_argument("--hide-asker", action="store_true"); s.set_defaults(fn=cmd_parse)
    s = sub.add_parser("plan"); s.add_argument("question"); s.add_argument("--mode", choices=["quick", "deep"], default="quick"); s.set_defaults(fn=cmd_plan)
    s = sub.add_parser("search"); s.add_argument("question"); s.add_argument("--mode", choices=["quick", "deep"], default="quick")
    s.add_argument("--out"); s.add_argument("--exposure"); s.add_argument("--outcome"); s.add_argument("--population"); s.set_defaults(fn=cmd_search)
    s = sub.add_parser("verify"); s.add_argument("--file"); s.add_argument("--doi"); s.add_argument("--pmid"); s.add_argument("--title")
    s.add_argument("--year", type=int); s.add_argument("--author"); s.add_argument("--pack", help="evidence pack whose PubMed records may resolve identifiers offline"); s.set_defaults(fn=cmd_verify)
    s = sub.add_parser("digest", help="write a compact Markdown view of a pack for the appraising agents")
    s.add_argument("pack"); s.add_argument("--out"); s.add_argument("--tier-b-chars", type=int, default=700); s.add_argument("--max-c", type=int, default=60); s.set_defaults(fn=cmd_digest)
    s = sub.add_parser("lock"); s.add_argument("file"); s.set_defaults(fn=cmd_lock)
    s = sub.add_parser("cache-put"); s.add_argument("url"); s.add_argument("file"); s.set_defaults(fn=cmd_cache_put)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
