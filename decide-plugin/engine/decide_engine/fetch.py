"""HTTP fetching with an on-disk cache, polite rate limiting and an offline mode.

The cache is the key to reproducibility and to running in sandboxes whose
network policy blocks the scholarly APIs: every request is keyed by the SHA-256
of its URL, so responses fetched by any other means (a browser, Firecrawl, a
colleague's machine) can be dropped into the cache directory and the engine
will run identically.

Nothing in this module ever sends credentials other than the optional
NCBI_API_KEY / OPENALEX_API_KEY / S2_API_KEY query/header values, which are
read from the environment and never logged.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

USER_AGENT = "decide-engine/0.1 (evidence-to-decision; mailto:{mail})"
DEFAULT_CACHE = Path(os.environ.get("DECIDE_CACHE_DIR", Path.home() / ".cache" / "decide-engine"))


class FetchBlocked(RuntimeError):
    """Raised in offline mode when a URL is not in the cache."""


@dataclass
class FetchLog:
    url: str
    status: int | None
    source: str  # "cache" | "network" | "blocked" | "error"
    seconds: float
    error: str | None = None


@dataclass
class Fetcher:
    cache_dir: Path = DEFAULT_CACHE
    offline: bool = False
    mailto: str = field(default_factory=lambda: os.environ.get("DECIDE_MAILTO", "unknown@example.org"))
    min_interval: float = 0.34  # NCBI allows 3 req/s without a key
    timeout: float = 30.0
    log: list[FetchLog] = field(default_factory=list)
    _last: float = 0.0

    # ------------------------------------------------------------------ cache
    @staticmethod
    def key(url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def cache_path(self, url: str) -> Path:
        return self.cache_dir / (self.key(url) + ".json")

    def _existing(self, url: str) -> Path | None:
        p = self.cache_path(url)
        if p.exists():
            return p
        g = p.with_suffix(".json.gz")
        return g if g.exists() else None

    def cached(self, url: str) -> bool:
        return self._existing(url) is not None

    def put(self, url: str, body: str, status: int = 200) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path(url).write_text(
            json.dumps({"url": url, "status": status, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "body": body}),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------ fetch
    def get(self, url: str, headers: dict[str, str] | None = None) -> str:
        """Return the response body for URL, from cache if present."""
        t0 = time.time()
        p = self._existing(url)
        if p is not None:
            raw = gzip.decompress(p.read_bytes()).decode("utf-8") if p.suffix == ".gz" else p.read_text(encoding="utf-8")
            data = json.loads(raw)
            self.log.append(FetchLog(url, data.get("status"), "cache", time.time() - t0))
            if (data.get("status") or 200) >= 400:
                raise urllib.error.HTTPError(url, data["status"], f"cached HTTP {data['status']}", hdrs=None, fp=None)
            return data["body"]
        if self.offline:
            self.log.append(FetchLog(url, None, "blocked", 0.0, "offline mode and not cached"))
            raise FetchBlocked(url)
        # polite rate limit
        wait = self.min_interval - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url)
        req.add_header("User-Agent", USER_AGENT.format(mail=self.mailto))
        req.add_header("Accept", "application/json")
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                status = resp.status
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            self._last = time.time()
            self.log.append(FetchLog(url, e.code, "error", time.time() - t0, f"HTTP {e.code}"))
            if e.code in (404, 410):  # a definite "does not exist" is worth remembering
                self.put(url, body, e.code)
            raise
        except Exception as e:  # URLError, timeout, proxy refusal
            self._last = time.time()
            self.log.append(FetchLog(url, None, "error", time.time() - t0, repr(e)))
            raise
        self._last = time.time()
        self.put(url, body, status)
        self.log.append(FetchLog(url, status, "network", time.time() - t0))
        return body

    def get_json(self, url: str, headers: dict[str, str] | None = None) -> Any:
        return json.loads(self.get(url, headers))


def build_url(base: str, params: dict[str, Any]) -> str:
    """Deterministic URL construction: sorted keys so cache keys are stable."""
    clean = {k: v for k, v in params.items() if v is not None and v != ""}
    return base + "?" + urllib.parse.urlencode(sorted(clean.items()), quote_via=urllib.parse.quote)
