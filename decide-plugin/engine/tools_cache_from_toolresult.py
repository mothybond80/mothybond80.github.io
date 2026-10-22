"""Store a Firecrawl/WebFetch tool-result file (JSON with rawHtml + metadata.sourceURL) in the engine cache."""
import json, sys
from pathlib import Path
from decide_engine.fetch import Fetcher
f = Fetcher()
for p in sys.argv[1:]:
    d = json.loads(Path(p).read_text())
    url = d["metadata"]["sourceURL"]; body = d["rawHtml"]
    f.put(url, body, d["metadata"].get("statusCode", 200))
    print("cached", url[:90], len(body))
