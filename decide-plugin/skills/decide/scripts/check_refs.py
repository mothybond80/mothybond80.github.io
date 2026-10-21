#!/usr/bin/env python3
"""Cross-check [R#] references used in appraisal.md / challenge.md against pack.json
and emit citations.json for `decide-engine verify`."""
import json, re, sys
from pathlib import Path

run = Path(sys.argv[1])
pack = json.loads((run / "pack.json").read_text(encoding="utf-8"))
refs = {r["ref"]: r for r in pack["records"]}
if (run / "pack2.json").exists():
    for r in json.loads((run / "pack2.json").read_text(encoding="utf-8"))["records"]:
        refs.setdefault(r["ref"] + "'", r)
problems, used = [], set()
for name in ("appraisal.md", "appraisal.json", "challenge.md", "verdict.md"):
    p = run / name
    if not p.exists():
        continue
    for m in re.finditer(r"\bR(\d+)('(?![A-Za-z]))?", p.read_text(encoding="utf-8")):
        key = f"R{m.group(1)}{m.group(2) or ''}"
        if key in refs:
            used.add(key)
        else:
            problems.append(f"{name}: {key} is not in the pack")
cits = []
for k in sorted(used, key=lambda x: int(re.sub(r"\D", "", x))):
    r = refs[k]
    cits.append({"ref": k, "doi": r.get("doi"), "pmid": r.get("pmid"), "title": r.get("title"), "year": r.get("year"),
                 "first_author": (r.get("authors") or [None])[0]})
(run / "citations.json").write_text(json.dumps({"citations": cits}, indent=1), encoding="utf-8")
print(json.dumps({"refs_used": len(used), "unknown_refs": problems, "citations_file": str(run / "citations.json")}, indent=1))
sys.exit(1 if problems else 0)
