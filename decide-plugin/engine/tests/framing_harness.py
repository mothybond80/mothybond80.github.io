#!/usr/bin/env python3
"""Framing-resistance harness for the deterministic layer.

For each of the seven test subjects, parses several framings and (optionally)
builds the evidence pack for each, then reports whether the framing hash,
search strategy and pack hash are identical. Usage:

  python3 tests/framing_harness.py            # parse-level only, no network
  python3 tests/framing_harness.py --packs    # also build packs (network or cache)
  python3 tests/framing_harness.py --packs --offline --cache-dir tests/fixtures/cache
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from decide_engine.fetch import Fetcher  # noqa: E402
from decide_engine.pack import build_pack  # noqa: E402
from decide_engine.question import parse_question, search_strategy  # noqa: E402
from tests.test_question import SUBJECTS  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packs", action="store_true")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--cache-dir")
    ap.add_argument("--mode", default="quick")
    a = ap.parse_args()
    rows = []
    all_ok = True
    for name, spec in SUBJECTS.items():
        parsed = [parse_question(q) for q, _ in spec["framings"]]
        fh = {p.framing_hash for p in parsed}
        st = {json.dumps(search_strategy(p), sort_keys=True) for p in parsed}
        ph: set[str] = set()
        n = None
        err = ""
        if a.packs:
            for p in parsed:
                f = Fetcher(cache_dir=Path(a.cache_dir) if a.cache_dir else Fetcher.cache_dir, offline=a.offline)
                try:
                    pk = build_pack(p.raw, mode=a.mode, fetcher=f, pq=p)
                    ph.add(pk["pack_hash"])
                    n = pk["n_records"]
                    if pk["missing_urls"]:
                        err = f"{len(pk['missing_urls'])} essential URLs missing"
                except Exception as e:  # noqa: BLE001
                    err = repr(e)[:60]
        ok = len(fh) == 1 and len(st) == 1 and (not a.packs or len(ph) == 1)
        all_ok &= ok
        rows.append((name, len(spec["framings"]), len(fh), len(st), len(ph) if a.packs else "-", n if a.packs else "-", "PASS" if ok else "FAIL", err,
                     parsed[0].exposure, parsed[0].outcome, parsed[0].population or ""))
    print("| subject | framings | distinct framing hashes | distinct strategies | distinct pack hashes | records | result | note | exposure | outcome | population |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print("| " + " | ".join(str(x) for x in r) + " |")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
