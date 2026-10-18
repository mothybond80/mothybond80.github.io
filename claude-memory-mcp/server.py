"""Claude Memory MCP server.

Hermes-style persistent memory and a self-improving skill library for Claude,
shared by every MCP client that connects to it: Claude Code, Claude Desktop and,
through a remote connector, claude.ai and the Claude mobile apps.

Memory is two small, capped Markdown files that Claude curates itself:

  USER.md    who the user is: preferences, style, role, people, recurring context
  MEMORY.md  Claude's own notes: environment facts, conventions, lessons learned

Skills are procedures Claude writes down after finishing a complex task and then
improves each time it uses them. Each lives in skills/<name>/SKILL.md (the same
format Claude Code uses), with every previous version kept for rollback.

Configuration (environment variables):
  CLAUDE_MEMORY_DIR            Storage folder. Default ~/.claude-memory
  CLAUDE_MEMORY_LIMIT          MEMORY.md character cap. Default 5000
  CLAUDE_MEMORY_USER_LIMIT     USER.md character cap. Default 2500
  CLAUDE_MEMORY_TOKEN          HTTP mode only: require "Authorization: Bearer <token>"
  CLAUDE_MEMORY_ALLOWED_HOSTS  HTTP mode only: comma-separated Host headers to accept
                               when running behind a proxy (e.g. "example.ts.net")

Run as an MCP server over stdio:        python server.py
Run as a Streamable HTTP server:        python server.py serve --port 8765
Print the snapshot (SessionStart hook): python server.py snapshot
"""

from __future__ import annotations

import argparse
import contextlib
import hmac
import json
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Iterator
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

try:  # POSIX file locking; the server targets macOS and Linux.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

ENTRY_SEP = "\n§\n"
_SEP_LINE = re.compile(r"^[ \t]*§[ \t]*$", re.M)  # a line holding only "§" separates entries
DEFAULT_DIR = Path.home() / ".claude-memory"
DEFAULT_MEMORY_LIMIT = 5000
DEFAULT_USER_LIMIT = 2500
SKILL_BODY_LIMIT = 20000
DESCRIPTION_LIMIT = 300
HISTORY_KEEP = 10
STALE_DAYS = 30
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SKILL_SECTIONS = ("## When to use", "## Procedure", "## Pitfalls", "## Verification")

Target = Literal["memory", "user"]
FILE_NAMES = {"memory": "MEMORY.md", "user": "USER.md"}
TITLES = {"memory": "Your notes (MEMORY.md)", "user": "About the user (USER.md)"}


class StoreError(Exception):
    """A request the store refuses, with a message written for the model."""


# ---------------------------------------------------------------------------
# Content safety
# ---------------------------------------------------------------------------

# Characters that render as nothing but can hide instructions. The zero-width
# joiner (U+200D) is left out because emoji sequences use it.
_INVISIBLE = re.compile("[​‌‎‏‪-‮⁠-⁤﻿\U000e0000-\U000e007f]")

_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("a private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("an AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("an AWS secret key", re.compile(r"aws_secret_access_key\s*[=:]", re.I)),
    ("an API key", re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}")),
    ("a GitHub token", re.compile(r"\b(?:ghp|gho|ghs|ghu|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}")),
    ("a Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("a Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("a bearer token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}")),
    (
        "a password or secret value",
        re.compile(
            r"\b(?:password|passwd|passcode|secret|api[_ -]?key|access[_ -]?token|client[_ -]?secret)\b"
            r"\s*(?:is|=|:)\s*\S{6,}",
            re.I,
        ),
    ),
]

_INJECTION_PATTERNS = [
    re.compile(r"\b(?:ignore|disregard|forget)\s+(?:all\s+|any\s+)?(?:the\s+|your\s+)?(?:previous|prior|above|earlier|system)\s+(?:instructions|prompts?|rules)", re.I),
    re.compile(r"\bnew\s+system\s+prompt\b", re.I),
    re.compile(r"</?\s*system\s*>", re.I),
    re.compile(r"\bdo\s+not\s+(?:tell|inform|show)\s+the\s+user\b", re.I),
    re.compile(r"\bexfiltrat", re.I),
]


def scan(text: str) -> str | None:
    """Return why ``text`` must not be stored, or None if it is acceptable."""
    if _INVISIBLE.search(text):
        return "it contains invisible Unicode characters"
    for label, pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            return f"it looks like it contains {label}; never store credentials"
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return "it reads like an instruction aimed at overriding the assistant's rules"
    return None


def _check(text: str) -> None:
    reason = scan(text)
    if reason:
        raise StoreError(f"Refused: {reason}.")


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def _preview(text: str, n: int = 80) -> str:
    one = " ".join(text.split())
    return one if len(one) <= n else one[: n - 1] + "…"


def _parse_skill(text: str) -> tuple[dict[str, str], str]:
    """Split a SKILL.md into (frontmatter, body). Frontmatter is flat key: value lines."""
    meta: dict[str, str] = {}
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            for line in text[4:end].splitlines():
                key, sep, value = line.partition(":")
                if sep:
                    meta[key.strip()] = value.strip()
            return meta, text[end + 5 :].lstrip("\n")
    return meta, text


def _render_skill(meta: dict[str, str], body: str) -> str:
    order = ["name", "description", "version", "created", "updated"]
    lines = [f"{k}: {meta[k]}" for k in order if meta.get(k)]
    lines += [f"{k}: {v}" for k, v in meta.items() if k not in order and v]
    return "---\n" + "\n".join(lines) + "\n---\n\n" + body.strip() + "\n"


class MemoryStore:
    def __init__(
        self,
        root: Path | str | None = None,
        memory_limit: int | None = None,
        user_limit: int | None = None,
    ) -> None:
        env_root = os.environ.get("CLAUDE_MEMORY_DIR")
        self.root = Path(root or env_root or DEFAULT_DIR).expanduser()
        self.limits = {
            "memory": memory_limit or int(os.environ.get("CLAUDE_MEMORY_LIMIT") or DEFAULT_MEMORY_LIMIT),
            "user": user_limit or int(os.environ.get("CLAUDE_MEMORY_USER_LIMIT") or DEFAULT_USER_LIMIT),
        }
        self.skills_dir = self.root / "skills"
        self.archive_dir = self.skills_dir / ".archive"

    # -- plumbing ------------------------------------------------------------

    @contextlib.contextmanager
    def _lock(self) -> Iterator[None]:
        self.root.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            os.chmod(self.root, 0o700)
        with open(self.root / ".lock", "a") as fh:
            if fcntl:
                fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl:
                    fcntl.flock(fh, fcntl.LOCK_UN)

    def _log(self, action: str, **detail: Any) -> None:
        record = {"ts": _now().isoformat(timespec="seconds"), "action": action, **detail}
        fd = os.open(self.root / "log.jsonl", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _path(self, target: str) -> Path:
        if target not in FILE_NAMES:
            raise StoreError('target must be "memory" or "user".')
        return self.root / FILE_NAMES[target]

    # -- memory --------------------------------------------------------------

    def entries(self, target: str) -> list[str]:
        path = self._path(target)
        if not path.exists():
            return []
        raw = path.read_text(encoding="utf-8")
        return [e.strip() for e in _SEP_LINE.split(raw) if e.strip()]

    def _write_entries(self, target: str, entries: list[str]) -> None:
        text = ENTRY_SEP.join(entries) + "\n" if entries else ""
        _atomic_write(self._path(target), text)

    @staticmethod
    def _size(entries: list[str]) -> int:
        return len(ENTRY_SEP.join(entries))

    def usage(self, target: str) -> dict[str, int]:
        return {"used": self._size(self.entries(target)), "limit": self.limits[target]}

    def _clean(self, content: str) -> str:
        content = (content or "").strip()
        if not content:
            raise StoreError("content is empty.")
        if any(line.strip() == "§" for line in content.splitlines()):
            raise StoreError('content cannot contain a line that is just "§" (it separates entries).')
        _check(content)
        return content

    def _full_error(self, target: str, entries: list[str], needed: int) -> StoreError:
        listing = "\n".join(f"- {_preview(e, 120)}" for e in entries)
        return StoreError(
            f"{FILE_NAMES[target]} is full ({self._size(entries):,}/{self.limits[target]:,} chars; "
            f"this change needs {needed:,}). Consolidate first: merge or shorten entries with "
            f"memory_replace, or drop stale ones with memory_remove. Current entries:\n{listing}"
        )

    def _match_one(self, target: str, entries: list[str], old_text: str) -> int:
        old_text = (old_text or "").strip()
        if not old_text:
            raise StoreError("old_text is empty; give a short unique piece of the entry to change.")
        exact = [i for i, e in enumerate(entries) if e == old_text]
        if len(exact) == 1:
            return exact[0]
        hits = [i for i, e in enumerate(entries) if old_text in e]
        if not hits:
            hits = [i for i, e in enumerate(entries) if old_text.lower() in e.lower()]
        if not hits:
            raise StoreError(f"No entry in {FILE_NAMES[target]} contains {old_text!r}.")
        if len(hits) > 1:
            listing = "\n".join(f"- {_preview(entries[i], 120)}" for i in hits)
            raise StoreError(f"{old_text!r} matches {len(hits)} entries; use a longer, unique piece:\n{listing}")
        return hits[0]

    def add(self, target: str, content: str) -> dict[str, Any]:
        content = self._clean(content)
        with self._lock():
            entries = self.entries(target)
            if content in entries:
                return {"ok": True, "status": "already stored", **self.usage(target)}
            new = entries + [content]
            if self._size(new) > self.limits[target]:
                raise self._full_error(target, entries, self._size(new) - self._size(entries))
            self._write_entries(target, new)
            self._log("memory_add", target=target, content=content)
            return {"ok": True, "status": "added", **self.usage(target)}

    def replace(self, target: str, old_text: str, new_content: str) -> dict[str, Any]:
        new_content = self._clean(new_content)
        with self._lock():
            entries = self.entries(target)
            i = self._match_one(target, entries, old_text)
            before = entries[i]
            new = entries[:i] + [new_content] + entries[i + 1 :]
            new = list(dict.fromkeys(new))  # replacing into a duplicate merges them
            if self._size(new) > self.limits[target]:
                raise self._full_error(target, entries, self._size(new) - self._size(entries))
            self._write_entries(target, new)
            self._log("memory_replace", target=target, before=before, after=new_content)
            return {"ok": True, "status": "replaced", "before": before, **self.usage(target)}

    def remove(self, target: str, old_text: str) -> dict[str, Any]:
        with self._lock():
            entries = self.entries(target)
            i = self._match_one(target, entries, old_text)
            removed = entries.pop(i)
            self._write_entries(target, entries)
            self._log("memory_remove", target=target, removed=removed)
            return {"ok": True, "status": "removed", "removed": removed, **self.usage(target)}

    # -- skills --------------------------------------------------------------

    def _skill_dir(self, name: str, archived: bool = False) -> Path:
        if not NAME_RE.match(name or ""):
            raise StoreError(
                "Skill names are lowercase letters, digits and hyphens, up to 64 characters "
                "(e.g. 'month-end-bank-reconciliation')."
            )
        return (self.archive_dir if archived else self.skills_dir) / name

    def _require(self, name: str) -> Path:
        d = self._skill_dir(name)
        if not (d / "SKILL.md").exists():
            if (self._skill_dir(name, archived=True) / "SKILL.md").exists():
                raise StoreError(f"Skill {name!r} is archived. Restore it with skill_restore first.")
            raise StoreError(f"No skill named {name!r}. Call skill_list to see what exists.")
        return d

    @staticmethod
    def _clean_description(description: str) -> str:
        description = " ".join((description or "").split())
        if not description:
            raise StoreError("description is empty. Say in one line when this skill should be used.")
        if len(description) > DESCRIPTION_LIMIT:
            raise StoreError(f"description is {len(description)} chars; keep it under {DESCRIPTION_LIMIT}.")
        _check(description)
        return description

    @staticmethod
    def _clean_body(body: str) -> str:
        body = (body or "").strip()
        if not body:
            raise StoreError("body is empty.")
        if len(body) > SKILL_BODY_LIMIT:
            raise StoreError(f"body is {len(body):,} chars; keep skills under {SKILL_BODY_LIMIT:,}.")
        _check(body)
        return body

    @staticmethod
    def _stats(d: Path) -> dict[str, Any]:
        try:
            return json.loads((d / ".stats.json").read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {"uses": 0, "last_used": None}

    def _summary(self, d: Path, archived: bool = False) -> dict[str, Any]:
        meta, _body = _parse_skill((d / "SKILL.md").read_text(encoding="utf-8"))
        stats = self._stats(d)
        last = max(filter(None, [meta.get("created"), meta.get("updated"), (stats.get("last_used") or "")[:10]]), default="")
        if archived:
            status = "archived"
        else:
            try:
                age = (date.today() - date.fromisoformat(last)).days
            except ValueError:
                age = 0
            status = "stale" if age > STALE_DAYS else "active"
        return {
            "name": d.name,
            "description": meta.get("description", ""),
            "version": int(meta.get("version") or 1),
            "updated": meta.get("updated"),
            "uses": stats.get("uses", 0),
            "last_used": stats.get("last_used"),
            "status": status,
        }

    def skills(self, include_archived: bool = False) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        if self.skills_dir.exists():
            for d in sorted(self.skills_dir.iterdir()):
                if d.is_dir() and not d.name.startswith(".") and (d / "SKILL.md").exists():
                    out.append(self._summary(d))
        if include_archived and self.archive_dir.exists():
            for d in sorted(self.archive_dir.iterdir()):
                if d.is_dir() and (d / "SKILL.md").exists():
                    out.append(self._summary(d, archived=True))
        return out

    def skill_view(self, name: str) -> dict[str, Any]:
        d = self._require(name)
        text = (d / "SKILL.md").read_text(encoding="utf-8")
        with self._lock():
            stats = self._stats(d)
            stats["uses"] = int(stats.get("uses", 0)) + 1
            stats["last_used"] = _now().isoformat(timespec="seconds")
            _atomic_write(d / ".stats.json", json.dumps(stats))
        files = sorted(
            str(p.relative_to(d)) for p in d.rglob("*")
            if p.is_file() and p.name != "SKILL.md" and not any(part.startswith(".") for part in p.relative_to(d).parts)
        )
        return {"name": name, "content": text, "other_files": files, "uses": stats["uses"]}

    def _history_save(self, d: Path, meta: dict[str, str]) -> None:
        hist = d / ".history"
        hist.mkdir(exist_ok=True)
        shutil.copy2(d / "SKILL.md", hist / f"v{int(meta.get('version') or 1)}.md")
        versions = sorted(hist.glob("v*.md"), key=lambda p: int(p.stem[1:]))
        for old in versions[:-HISTORY_KEEP]:
            old.unlink()

    def skill_create(self, name: str, description: str, body: str) -> dict[str, Any]:
        description = self._clean_description(description)
        body = self._clean_body(body)
        with self._lock():
            d = self._skill_dir(name)
            if (d / "SKILL.md").exists():
                raise StoreError(f"Skill {name!r} already exists. Improve it with skill_update instead.")
            if (self._skill_dir(name, archived=True) / "SKILL.md").exists():
                raise StoreError(f"An archived skill is called {name!r}. Restore it or pick another name.")
            today = date.today().isoformat()
            meta = {"name": name, "description": description, "version": "1", "created": today, "updated": today}
            _atomic_write(d / "SKILL.md", _render_skill(meta, body))
            self._log("skill_create", name=name, description=description)
        result: dict[str, Any] = {"ok": True, "status": "created", "name": name, "version": 1}
        missing = [s for s in SKILL_SECTIONS if s.lower() not in body.lower()]
        if missing:
            result["note"] = "Consider adding these sections next time you update it: " + ", ".join(missing)
        return result

    def skill_update(
        self,
        name: str,
        description: str | None = None,
        body: str | None = None,
        old_text: str | None = None,
        new_text: str | None = None,
    ) -> dict[str, Any]:
        if body is not None and old_text is not None:
            raise StoreError("Pass either body (full rewrite) or old_text/new_text (targeted edit), not both.")
        if old_text is not None and new_text is None:
            raise StoreError("old_text needs new_text (use an empty string to delete the passage).")
        if description is None and body is None and old_text is None:
            raise StoreError("Nothing to change: pass description, body, or old_text with new_text.")
        with self._lock():
            d = self._require(name)
            meta, current = _parse_skill((d / "SKILL.md").read_text(encoding="utf-8"))
            new_body = current
            if body is not None:
                new_body = self._clean_body(body)
            elif old_text is not None:
                count = current.count(old_text)
                if count == 0:
                    raise StoreError(f"old_text was not found in skill {name!r}. Call skill_view to see the exact text.")
                if count > 1:
                    raise StoreError(f"old_text appears {count} times in {name!r}; include more surrounding text.")
                new_body = self._clean_body(current.replace(old_text, new_text or "", 1))
            new_meta = dict(meta)
            if description is not None:
                new_meta["description"] = self._clean_description(description)
            if new_body == current and new_meta == meta:
                return {"ok": True, "status": "unchanged", "name": name, "version": int(meta.get("version") or 1)}
            self._history_save(d, meta)
            version = int(meta.get("version") or 1) + 1
            new_meta.update(version=str(version), updated=date.today().isoformat())
            _atomic_write(d / "SKILL.md", _render_skill(new_meta, new_body))
            self._log("skill_update", name=name, version=version)
            return {"ok": True, "status": "updated", "name": name, "version": version}

    def skill_rollback(self, name: str, version: int) -> dict[str, Any]:
        with self._lock():
            d = self._require(name)
            src = d / ".history" / f"v{int(version)}.md"
            if not src.exists():
                kept = sorted(int(p.stem[1:]) for p in (d / ".history").glob("v*.md")) if (d / ".history").exists() else []
                raise StoreError(f"Version {version} of {name!r} is not kept. Available: {kept or 'none'}.")
            meta, current = _parse_skill((d / "SKILL.md").read_text(encoding="utf-8"))
            old_meta, old_body = _parse_skill(src.read_text(encoding="utf-8"))
            self._history_save(d, meta)
            new_version = int(meta.get("version") or 1) + 1
            new_meta = dict(meta)
            new_meta.update(
                description=old_meta.get("description", meta.get("description", "")),
                version=str(new_version),
                updated=date.today().isoformat(),
            )
            _atomic_write(d / "SKILL.md", _render_skill(new_meta, old_body))
            self._log("skill_rollback", name=name, to=int(version), version=new_version)
            return {"ok": True, "status": f"restored v{int(version)} as v{new_version}", "name": name, "version": new_version}

    def skill_archive(self, name: str) -> dict[str, Any]:
        with self._lock():
            d = self._require(name)
            dest = self._skill_dir(name, archived=True)
            if dest.exists():
                dest = dest.with_name(f"{name}-{_now().strftime('%Y%m%d%H%M%S')}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(d), str(dest))
            self._log("skill_archive", name=name)
            return {"ok": True, "status": "archived", "name": name}

    def skill_restore(self, name: str) -> dict[str, Any]:
        with self._lock():
            src = self._skill_dir(name, archived=True)
            if not (src / "SKILL.md").exists():
                raise StoreError(f"No archived skill named {name!r}.")
            dest = self._skill_dir(name)
            if dest.exists():
                raise StoreError(f"An active skill is already called {name!r}.")
            shutil.move(str(src), str(dest))
            self._log("skill_restore", name=name)
            return {"ok": True, "status": "restored", "name": name}

    # -- snapshot ------------------------------------------------------------

    def snapshot(self) -> str:
        parts = [f"# Claude memory (loaded {_now().strftime('%Y-%m-%d %H:%M UTC')})"]
        for target in ("user", "memory"):
            entries = self.entries(target)
            u = self.usage(target)
            parts.append(f"\n## {TITLES[target]} · {u['used']:,}/{u['limit']:,} chars")
            parts.append(ENTRY_SEP.join(entries) if entries else "(empty)")
        skills = self.skills()
        parts.append(f"\n## Skills ({len(skills)}) · call skill_view(name) before doing one of these tasks")
        if skills:
            for s in skills:
                flag = " [stale: check it still holds]" if s["status"] == "stale" else ""
                parts.append(f"- {s['name']}: {s['description']}{flag}")
        else:
            parts.append("(none yet)")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# MCP server and tools
# ---------------------------------------------------------------------------

INSTRUCTIONS = """\
This server is your persistent memory and skill library. It is shared by every place the user talks \
to you (Claude Code, the Claude apps and claude.ai), so what you save here follows them everywhere.

At the start of every conversation, before your first answer, call memory_view once and treat what \
it returns as things you already know. Do not mention doing so unless asked.

MEMORY: two small, capped stores.
- user: who the user is. Preferences, communication style, role, businesses, people they mention, \
recurring context.
- memory: your own notes. Facts about their setup and tools, conventions, decisions, lessons learned.
Save with memory_add as soon as you learn something durable that will matter in a future \
conversation: a stated preference, a correction, a fact about their setup, a decision made. Write \
each entry as one short, self-contained fact. When the user corrects you, save the correction. Do not \
save things that only matter to this conversation, things easy to look up, or anything already \
stored. When a store is full, consolidate with memory_replace or memory_remove, then add.
Never store passwords, API keys, tokens, bank details, or patient-identifiable or clinical information.

SKILLS: procedures that get better with use.
- Before a multi-step task, check the skill list from memory_view. If one fits, call skill_view and \
follow it.
- After finishing a complex or repeatable workflow (about five or more steps, a tricky fix, or \
something the user is likely to ask for again), save it with skill_create while the details are \
fresh. Structure the body as: ## When to use, ## Procedure, ## Pitfalls, ## Verification.
- If a skill turned out wrong, incomplete or out of date, fix it straight away with skill_update. \
Prefer small old_text/new_text edits.
- Archive skills that no longer apply with skill_archive.
Briefly tell the user whenever you save or change a memory or a skill."""

mcp = MCPServer("claude-memory", instructions=INSTRUCTIONS)

_READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
_WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)
_DELETE = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False)


def store() -> MemoryStore:
    return MemoryStore()


def _dumps(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)


def _run(fn, *args: Any, **kwargs: Any) -> str:
    try:
        return _dumps(fn(*args, **kwargs))
    except StoreError as exc:
        return _dumps({"ok": False, "error": str(exc)})
    except Exception as exc:  # noqa: BLE001
        return _dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"})


@mcp.tool(annotations=_READ)
def memory_view() -> str:
    """Load your persistent memory: what you know about the user, your own notes, and your skill list.

    Call this once at the start of every conversation, before answering.
    """
    try:
        return store().snapshot()
    except Exception as exc:  # noqa: BLE001
        return _dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"})


@mcp.tool(annotations=_WRITE)
def memory_add(target: Target, content: str) -> str:
    """Save one durable fact to memory.

    target: "user" for facts about the user (preferences, style, role, people),
            "memory" for your own notes (setup, conventions, decisions, lessons).
    content: one short, self-contained fact. No secrets or patient-identifiable data.
    """
    return _run(store().add, target, content)


@mcp.tool(annotations=_WRITE)
def memory_replace(target: Target, old_text: str, new_content: str) -> str:
    """Rewrite one memory entry, e.g. to correct it or to merge two entries into one.

    old_text: a short piece of the existing entry that identifies it uniquely.
    new_content: the full replacement entry.
    """
    return _run(store().replace, target, old_text, new_content)


@mcp.tool(annotations=_DELETE)
def memory_remove(target: Target, old_text: str) -> str:
    """Delete one memory entry that is wrong or no longer useful.

    old_text: a short piece of the entry that identifies it uniquely.
    """
    return _run(store().remove, target, old_text)


@mcp.tool(annotations=_READ)
def skill_list(include_archived: bool = False) -> str:
    """List saved skills with description, version, use count and status (active, stale or archived)."""
    return _run(lambda: {"skills": store().skills(include_archived)})


@mcp.tool(annotations=_WRITE)
def skill_view(name: str) -> str:
    """Open a skill's full instructions before doing the task it covers. Records that the skill was used."""
    return _run(store().skill_view, name)


@mcp.tool(annotations=_WRITE)
def skill_create(name: str, description: str, body: str) -> str:
    """Save a reusable procedure after finishing a complex or repeatable task.

    name: lowercase-with-hyphens, e.g. "invisalign-case-submission".
    description: one line saying when to use it (this is what appears in the skill list).
    body: Markdown with sections ## When to use, ## Procedure, ## Pitfalls, ## Verification.
    """
    return _run(store().skill_create, name, description, body)


@mcp.tool(annotations=_WRITE)
def skill_update(
    name: str,
    description: str | None = None,
    body: str | None = None,
    old_text: str | None = None,
    new_text: str | None = None,
) -> str:
    """Improve a skill. The previous version is kept and can be restored with skill_rollback.

    Either replace one passage (old_text -> new_text, preferred) or rewrite the whole body.
    description can be changed on its own or together with either.
    """
    return _run(store().skill_update, name, description, body, old_text, new_text)


@mcp.tool(annotations=_WRITE)
def skill_rollback(name: str, version: int) -> str:
    """Restore an earlier version of a skill. It becomes the newest version; nothing is lost."""
    return _run(store().skill_rollback, name, version)


@mcp.tool(annotations=_WRITE)
def skill_archive(name: str) -> str:
    """Retire a skill that no longer applies. It is moved aside, not deleted, and can be restored."""
    return _run(store().skill_archive, name)


@mcp.tool(annotations=_WRITE)
def skill_restore(name: str) -> str:
    """Bring an archived skill back into the active list."""
    return _run(store().skill_restore, name)


# ---------------------------------------------------------------------------
# HTTP mode
# ---------------------------------------------------------------------------


class BearerAuth:
    """Minimal ASGI middleware requiring a static bearer token on every HTTP request."""

    def __init__(self, app: Any, token: str, open_paths: tuple[str, ...] = ("/health",)) -> None:
        self.app = app
        self.expected = f"Bearer {token}".encode()
        self.open_paths = open_paths

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] == "http" and scope.get("path") not in self.open_paths:
            got = dict(scope.get("headers") or []).get(b"authorization", b"")
            if not hmac.compare_digest(got, self.expected):
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"application/json"), (b"www-authenticate", b"Bearer")]})
                await send({"type": "http.response.body", "body": b'{"error":"unauthorized"}'})
                return
        await self.app(scope, receive, send)


def build_http_app(host: str = "127.0.0.1", path: str = "/mcp") -> Any:
    from mcp.server.transport_security import TransportSecuritySettings
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    extra = [h.strip() for h in os.environ.get("CLAUDE_MEMORY_ALLOWED_HOSTS", "").split(",") if h.strip()]
    hosts = ["127.0.0.1", "127.0.0.1:*", "localhost", "localhost:*", "[::1]", "[::1]:*"]
    hosts += [h for e in extra for h in (e, f"{e}:*")]
    security = TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=hosts, allowed_origins=[])
    app = mcp.streamable_http_app(streamable_http_path=path, host=host, transport_security=security)

    async def health(_request: Any) -> Any:
        return JSONResponse({"ok": True, "server": "claude-memory"})

    app.router.routes.append(Route("/health", health))
    token = os.environ.get("CLAUDE_MEMORY_TOKEN")
    return BearerAuth(app, token) if token else app


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("stdio", help="run over stdio (default)")
    serve = sub.add_parser("serve", help="run as a Streamable HTTP server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--path", default="/mcp")
    sub.add_parser("snapshot", help="print the memory snapshot (for a Claude Code SessionStart hook)")
    args = parser.parse_args(argv)

    if args.cmd == "snapshot":
        sys.stdout.write(store().snapshot() + "\n")
    elif args.cmd == "serve":
        import uvicorn

        uvicorn.run(build_http_app(args.host, args.path), host=args.host, port=args.port, log_level="warning")
    else:
        mcp.run("stdio")


if __name__ == "__main__":
    main()
