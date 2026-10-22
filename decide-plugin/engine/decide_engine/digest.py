"""Compact, read-once Markdown digest of an evidence pack for the appraising agents.

A 100-record pack is ~0.5 MB of JSON; an agent that explores it with ad-hoc
scripts spends many turns and minutes. The digest puts everything the
appraiser needs in one file in a fixed order: header (question, searches,
warnings, contract), then records grouped by relevance tier, with full
abstracts for tier A, truncated abstracts for tier B and titles only for C.
Nothing is interpreted here; it is a view of the pack.
"""

from __future__ import annotations

import json
from typing import Any


def _fmt_record(r: dict[str, Any], abstract_chars: int | None) -> str:
    c = r.get("classification", {})
    flags = []
    if r.get("is_retracted"):
        flags.append("RETRACTED")
    if r.get("integrity_flags"):
        flags.append("flags: " + ", ".join(r["integrity_flags"]))
    if r.get("linked_from_pmid"):
        flags.append(f"linked commentary on PMID {r['linked_from_pmid']}")
    ids = " ".join(x for x in [f"PMID {r['pmid']}" if r.get("pmid") else "", f"doi:{r['doi']}" if r.get("doi") else ""] if x)
    authors = r.get("authors") or []
    first = authors[0] if authors else "?"
    head = (f"### [{r['ref']}] {first}{' et al.' if len(authors) > 1 else ''} ({r.get('year') or '?'}). {r.get('title') or '(no title)'}\n"
            f"- design: {c.get('study_type')} ({c.get('basis')}); n-guess: {c.get('sample_size_guess')} ({c.get('sample_size_basis')})\n"
            f"- journal: {r.get('journal') or '?'}; cited by: {r.get('cited_by_count')}; {ids}\n")
    if r.get("scite_tally"):
        t = r["scite_tally"]
        head += f"- scite tally (advisory): supporting {t.get('supporting')}, contrasting {t.get('contrasting')}, mentioning {t.get('mentioning')}\n"
    if flags:
        head += "- **" + "; ".join(flags) + "**\n"
    if abstract_chars is not None:
        ab = (r.get("abstract") or "").strip()
        if not ab:
            head += "- abstract: NOT AVAILABLE (title only)\n"
        else:
            if abstract_chars and len(ab) > abstract_chars:
                ab = ab[:abstract_chars].rsplit(" ", 1)[0] + " [...truncated]"
            head += f"- abstract ({r.get('abstract_source')}): {ab}\n"
    return head


def digest(pack: dict[str, Any], tier_b_chars: int = 700, max_c: int = 60, max_a: int | None = None, b_titles_only: bool = False) -> str:
    """quick mode (pack["mode"] == "quick") defaults to a smaller view: at most 30 tier A records with
    full abstracts (the pack is already ranked synthesis-first), tier B as titles only, tier C counted
    only. Deep mode shows everything. Linked commentary records are always shown in full."""
    if pack.get("mode") == "quick":
        max_a = 30 if max_a is None else max_a
        b_titles_only = True
        max_c = min(max_c, 15)
    q = pack["question"]
    out = [f"# Evidence pack digest\n", f"**Neutral question:** {q['neutral']}\n",
           f"- exposure: {q['exposure']}; outcome: {q['outcome']}; population: {q.get('population') or 'not specified'}; domains: {', '.join(q['domains'])}",
           f"- mode: {pack['mode']}; built: {pack['built_at']}; pack_hash: {pack['pack_hash']}",
           f"- records: {pack['n_records']} (tier A {pack['relevance_tiers']['A']}, B {pack['relevance_tiers']['B']}, C {pack['relevance_tiers']['C']})"]
    if pack.get("evidence_gap"):
        out.append(f"\n**EVIDENCE GAP:** {pack.get('evidence_gap_note')}")
    pc = pack.get("population_coverage")
    if pc and pc.get("warning"):
        out.append(f"\n**POPULATION COVERAGE WARNING:** {pc['warning']}")
    out.append("\n## Searches actually run\n")
    out.append("| db | label | hits | retrieved | query |\n|---|---|---|---|---|")
    for s in pack["searches"]:
        out.append(f"| {s.get('db')} | {s.get('label')} | {s.get('count')} | {s.get('returned')} | {str(s.get('query'))[:160]} |")
    if pack.get("errors"):
        out.append("\n**Not searched / errors:** " + "; ".join(pack["errors"]))
    if pack.get("retracted_or_flagged"):
        out.append("\n**Retracted or integrity-flagged records:** " + ", ".join(pack["retracted_or_flagged"]))
    if pack.get("overlap_warnings"):
        out.append("\n## Overlap warnings between syntheses\n")
        for o in pack["overlap_warnings"]:
            out.append(f"- {o['a_title'][:80]} <-> {o['b_title'][:80]}: {o['shared_refs']} shared references (containment {o['containment']}). {o['note']}")
    out.append("\n## Domain guidance\n")
    for d, g in pack["domain_guidance"].items():
        out.append(f"- **{d}**: preferred {', '.join(g['preferred_designs'])}; weak {', '.join(g['weak_designs'])}; tools: {'; '.join(g['appraisal_tools'])}; watch for: {'; '.join(g['watch_for'])}")
    out.append("\n## Appraiser contract\n")
    out.append("```json\n" + json.dumps(pack["appraiser_contract"], indent=1) + "\n```")
    recs = pack["records"]
    ra = [r for r in recs if r["relevance"]["tier"] == "A"]
    shown_a = ra if max_a is None else (ra[:max_a] + [r for r in ra[max_a:] if r.get("linked_from_pmid")])
    out.append(f"\n## Tier A records (exposure in title, outcome present) - full abstracts: {len(shown_a)} of {len(ra)}\n")
    for r in shown_a:
        out.append(_fmt_record(r, 0))
    if len(shown_a) < len(ra):
        out.append(f"\n### Further tier A records not shown in full ({len(ra) - len(shown_a)}; titles only, see pack.json)\n")
        for r in ra:
            if r not in shown_a:
                out.append(f"- [{r['ref']}] {r.get('year') or '?'} {r.get('classification', {}).get('study_type')}: {r.get('title')}")
    rb = [r for r in recs if r["relevance"]["tier"] == "B"]
    if b_titles_only:
        out.append(f"\n## Tier B records (exposure and outcome present) - titles only: {len(rb)}\n")
        for r in rb:
            out.append(f"- [{r['ref']}] {r.get('year') or '?'} {r.get('classification', {}).get('study_type')}: {r.get('title')}" + (" **RETRACTED**" if r.get("is_retracted") else ""))
    else:
        out.append(f"\n## Tier B records (exposure and outcome present) - truncated abstracts: {len(rb)}\n")
        for r in rb:
            out.append(_fmt_record(r, tier_b_chars))
    rs = [r for r in recs if r["relevance"]["tier"] == "C"]
    out.append(f"\n## Tier C records (lexically off-topic; titles only): {len(rs)}\n")
    for r in rs[:max_c]:
        c = r.get("classification", {})
        out.append(f"- [{r['ref']}] {r.get('year') or '?'} {c.get('study_type')}: {r.get('title')}" + (" **RETRACTED**" if r.get("is_retracted") else ""))
    if len(rs) > max_c:
        out.append(f"- ... {len(rs) - max_c} more tier C records omitted (see pack.json)")
    return "\n".join(out) + "\n"
