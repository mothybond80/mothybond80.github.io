"""gzip every plain .json entry in a decide-engine cache directory (fixtures stay readable by Fetcher)."""
import gzip, sys
from pathlib import Path
d = Path(sys.argv[1])
for p in sorted(d.glob("*.json")):
    gz = p.with_suffix(".json.gz")
    gz.write_bytes(gzip.compress(p.read_bytes(), 9))
    p.unlink()
    print("compressed", p.name, "->", gz.stat().st_size, "bytes")
