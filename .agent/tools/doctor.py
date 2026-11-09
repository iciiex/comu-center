#!/usr/bin/env python3
"""Health check for a repository operated by the Kiloos agent kit.

Checks structure, decision discipline, handoff freshness, doc links,
sample-data labeling and high-confidence secret patterns.

Usage:
    python3 .agent/tools/doctor.py --root .
    python3 .agent/tools/doctor.py --root . --strict   # warnings fail too
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ALLOWED_STATES = {"APPROVED", "PROPOSED", "ASSUMPTION", "OPEN", "IMPLEMENTED", "DEPRECATED"}

ROLES = [
    "01-product-ba.md",
    "02-architect.md",
    "03-backend.md",
    "04-frontend-mobile.md",
    "05-qa.md",
    "06-devops.md",
    "07-integrator-lead.md",
]
PLAYBOOKS = [
    "prototype-9-days.md",
    "vertical-slice.md",
    "scoring-and-rules.md",
    "sales-import.md",
    "review-and-handoff.md",
]
TEMPLATES = [
    "current-state.md",
    "handoff.md",
    "adr.md",
    "open-decision.md",
    "slice-plan.md",
    "pr.md",
]
DOC_FILES = [
    "docs/README.md",
    "docs/decisions/decision-log.md",
    "docs/decisions/open-decisions.md",
    "docs/handoffs/current-state.md",
]
SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
    ".next", ".nuxt", "coverage", ".mypy_cache", ".ruff_cache", ".pytest_cache",
    "target", "vendor", ".idea", ".vscode",
}
TEXT_EXT = {
    ".md", ".json", ".py", ".ts", ".tsx", ".js", ".jsx", ".dart", ".sql",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh", ".env", ".txt", ".html",
}
SECRET_PATTERNS = [
    ("private key block", re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY")),
    ("github token", re.compile(r"ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}")),
    ("openai-style key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("aws access key", re.compile(r"AKIA[0-9A-Z]{16}")),
]

issues: list[tuple[str, str]] = []  # (level, message)


def ok(msg: str) -> None:
    issues.append(("OK", msg))


def warn(msg: str) -> None:
    issues.append(("WARN", msg))


def fail(msg: str) -> None:
    issues.append(("FAIL", msg))


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def strip_fences(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.S)


def check_structure(root: Path) -> None:
    required = ["AGENTS.md", *DOC_FILES]
    required += [f".agent/roles/{name}" for name in ROLES]
    required += [f".agent/playbooks/{name}" for name in PLAYBOOKS]
    required += [f".agent/templates/{name}" for name in TEMPLATES]
    required += [".agent/CONTEXT.md", ".agent/MASTER_PROMPT.fa.md"]

    missing = [rel for rel in required if not (root / rel).is_file()]
    if missing:
        for rel in missing:
            fail(f"missing: {rel}")
        fail("run: python3 tools/bootstrap.py --target <repo>")
    else:
        ok(f"structure complete ({len(required)} required files)")


def split_blocks(text: str) -> list[tuple[str, str]]:
    """Split markdown into (heading, body) blocks on level-2 headings."""
    blocks: list[tuple[str, str]] = []
    heading = ""
    body: list[str] = []
    for line in strip_fences(text).splitlines():
        if line.startswith("## "):
            if heading:
                blocks.append((heading, "\n".join(body)))
            heading = line[3:].strip()
            body = []
        else:
            body.append(line)
    if heading:
        blocks.append((heading, "\n".join(body)))
    return blocks


def field(body: str, name: str) -> str:
    match = re.search(rf"^-\s*{re.escape(name)}\s*:\s*(.*)$", body, flags=re.M)
    return match.group(1).strip() if match else ""


def check_open_decisions(root: Path) -> None:
    path = root / "docs/decisions/open-decisions.md"
    if not path.is_file():
        return
    text = read(path)
    blocks = [(h, b) for h, b in split_blocks(text) if re.match(r"^OD-\d+", h)]
    if not blocks:
        fail("open-decisions.md: no OD-xx blocks found")
        return

    ids = {re.match(r"^(OD-\d+)", h).group(1) for h, _ in blocks}  # type: ignore[union-attr]
    for heading, body in blocks:
        od_id = re.match(r"^(OD-\d+)", heading).group(1)  # type: ignore[union-attr]
        status = field(body, "Status")
        if status not in ALLOWED_STATES:
            fail(f"{od_id}: invalid status '{status or 'missing'}'")
        elif status == "APPROVED":
            log = read(root / "docs/decisions/decision-log.md")
            if od_id not in log:
                fail(f"{od_id} marked APPROVED but not referenced in decision-log.md")

    seed_path = root / ".agent/context/open-decisions.seed.json"
    if seed_path.is_file():
        try:
            seed = json.loads(read(seed_path))
        except json.JSONDecodeError:
            warn("seed open-decisions.json is not valid JSON")
            seed = {}
        expected = {od["id"] for od in seed.get("open_decisions", [])}
        missing = sorted(expected - ids)
        if missing:
            fail(f"open-decisions.md missing seeded decisions: {', '.join(missing)}")
    ok(f"open decisions: {len(blocks)} blocks, statuses valid")


def check_decision_log(root: Path) -> None:
    path = root / "docs/decisions/decision-log.md"
    if not path.is_file():
        return
    blocks = [(h, b) for h, b in split_blocks(read(path)) if re.match(r"^D-\d+", h)]
    approved = 0
    for heading, body in blocks:
        status = field(body, "Status")
        if status and status not in {"APPROVED", "PROPOSED", "SUPERSEDED", "DEPRECATED"}:
            fail(f"decision-log '{heading}': invalid status '{status}'")
        if status == "APPROVED":
            approved += 1
            if not field(body, "Approved by"):
                fail(f"decision-log '{heading}': APPROVED without 'Approved by'")
            if not re.search(r"\d{4}-\d{2}-\d{2}", field(body, "Date")):
                fail(f"decision-log '{heading}': APPROVED without ISO date")
    ok(f"decision log: {len(blocks)} entries ({approved} approved)")


def check_current_state(root: Path, max_age_days: int) -> None:
    path = root / "docs/handoffs/current-state.md"
    if not path.is_file():
        return
    text = read(path)
    for heading in ("Working features", "In progress", "Known issues",
                    "Next recommended tasks", "Tests and verification"):
        if f"## {heading}" not in text:
            warn(f"current-state.md missing section: {heading}")

    match = re.search(r"Last updated:\s*(\d{4}-\d{2}-\d{2})", text)
    if not match:
        warn("current-state.md: 'Last updated' is not an ISO date")
        return
    try:
        updated = datetime.strptime(match.group(1), "%Y-%m-%d").date()
    except ValueError:
        warn("current-state.md: unparsable 'Last updated'")
        return
    age = (date.today() - updated).days
    if age > max_age_days:
        warn(f"current-state.md is {age} days old (limit {max_age_days})")
    elif age < 0:
        warn("current-state.md is dated in the future")
    else:
        ok(f"current-state.md fresh ({age} days)")


def check_doc_links(root: Path) -> None:
    readme = root / "docs/README.md"
    if not readme.is_file():
        return
    text = read(readme)
    broken: list[str] = []
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        target = target.strip()
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        clean = target.split("#", 1)[0]
        if not clean:
            continue
        if not (readme.parent / clean).exists():
            broken.append(target)
    if broken:
        for target in broken:
            fail(f"docs/README.md broken link: {target}")
    else:
        ok("docs/README.md links resolve")


def check_sample_labeling(root: Path) -> None:
    checked = 0
    for path in root.rglob("*.json"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.stat().st_size > 2_000_000:
            continue
        try:
            data = json.loads(read(path))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("sample") is True:
            checked += 1
            if str(data.get("status", "")).upper() == "APPROVED":
                fail(f"{path.relative_to(root)}: sample data must not be APPROVED")
    if checked:
        ok(f"sample labeling: {checked} sample file(s) checked")


def check_secrets(root: Path) -> None:
    hits: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_EXT or path.stat().st_size > 2_000_000:
            continue
        text = read(path)
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                hits.append(f"{path.relative_to(root)}: {label}")
    if hits:
        for hit in hits:
            fail(f"possible secret — {hit}")
    else:
        ok("no high-confidence secret patterns")


def check_mode_declared(root: Path) -> None:
    text = read(root / "docs/handoffs/current-state.md")
    match = re.search(r"^- Mode:\s*(P|H|S)\b", text, flags=re.M)
    if match:
        ok(f"mode declared: {match.group(1)}")
    else:
        warn("current-state.md: mode (P/H/S) not declared")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Health check for a Kiloos-agent repository.")
    parser.add_argument("--root", default=".", help="Repository root (default: .)")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    parser.add_argument("--max-state-age", type=int, default=21, help="Handoff max age in days")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory")
        return 2

    check_structure(root)
    check_open_decisions(root)
    check_decision_log(root)
    check_current_state(root, args.max_state_age)
    check_doc_links(root)
    check_sample_labeling(root)
    check_secrets(root)
    check_mode_declared(root)

    print(f"Kiloos agent doctor — {root}\n")
    for level, message in issues:
        print(f"[{level:<4}] {message}")

    failures = sum(1 for level, _ in issues if level == "FAIL")
    warnings = sum(1 for level, _ in issues if level == "WARN")
    passes = sum(1 for level, _ in issues if level == "OK")
    print(f"\nSummary: {passes} ok · {warnings} warn · {failures} fail")

    if failures or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
