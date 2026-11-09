#!/usr/bin/env python3
"""Install the Kiloos agent kit into a product repository.

Creates (idempotently):
    <target>/AGENTS.md
    <target>/.agent/...            roles, playbooks, templates, context
    <target>/docs/...              documentation skeleton + decision registries

Existing files are preserved unless --force is given.

Usage:
    python3 tools/bootstrap.py --target ../kiloos-club
    python3 tools/bootstrap.py --target . --force
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parent.parent

DOC_DIRS = [
    "product",
    "architecture",
    "architecture/decisions",
    "engineering",
    "delivery",
    "decisions",
    "operations",
    "quality",
    "handoffs",
]

SEED_OPEN_DECISIONS = KIT_ROOT / "context" / "open-decisions.seed.json"

DOCS_README = """# مستندات پروژه Kiloos Club

> ترتیب مطالعه: `../AGENTS.md` → `../.agent/CONTEXT.md` → `handoffs/current-state.md` → این فایل.

| # | موضوع | مسیر | وضعیت |
|---|---|---|---|
| 01 | Product Strategy & Scope | `product/strategy-and-scope.md` | منبع: Google Drive (نسخه ۰.۱) |
| 02 | Product Requirements | `product/prd.md` | در انتظار ایجاد |
| 03 | Solution Architecture | `architecture/solution-architecture.md` | در انتظار ایجاد |
| 04 | Technical Design & DB | `architecture/technical-design.md` | در انتظار ایجاد |
| 05 | Database ERD & SQL | `architecture/database-erd.md` | در انتظار ایجاد |
| 06 | Scoring Engine | `engineering/scoring-engine.md` | در انتظار ایجاد |
| 06-A | Scoring Rule Matrix | `engineering/scoring-rule-matrix.md` | در انتظار ایجاد |
| 07 | API Specification | `engineering/api-spec.md` | در انتظار ایجاد |
| 08 | UX/UI Specification | `product/ux-ui-spec.md` | در انتظار ایجاد |
| 09 | Admin Panel Specification | `product/admin-panel-spec.md` | در انتظار ایجاد |
| 10 | QA & Test Strategy | `quality/qa-test-strategy.md` | در انتظار ایجاد |
| 11 | DevOps & Deployment | `architecture/deployment-architecture.md` | در انتظار ایجاد |
| 12 | Execution Plan | `delivery/execution-plan.md` | در انتظار ایجاد |
| 13 | Open Decisions | `decisions/open-decisions.md` | seed شده |
| — | Decision Log | `decisions/decision-log.md` | seed شده |
| — | Current State | `handoffs/current-state.md` | seed شده |

## قواعد

- مستندات باید واقعیت فعلی را نشان دهند؛ اختلاف با کد پنهان نمی‌شود.
- تنها راه «مصوب» کردن یک تصمیم، ثبت `APPROVED` در `decisions/decision-log.md` است.
- هر تغییر کد، سند متأثر خود را در همان تغییر به‌روز می‌کند (جدول در `AGENTS.md` §12).
"""

DECISION_LOG = """# Decision Log

> فقط تصمیم‌های ثبت‌شده اینجا می‌توانند `APPROVED` باشند.
> قالب هر ورودی: `## D-XXX — عنوان` با `Status`, `Date`, `Approved by`, `Related`.

## قالب

```markdown
## D-001 — عنوان تصمیم

- Status: APPROVED | PROPOSED | SUPERSEDED
- Date: YYYY-MM-DD
- Approved by:
- Owners:
- Related: OD-xx / ADR-xxx / EP-xx

**Decision:** …
**Rationale:** …
**Consequences:** …
**Affected docs:**
```

## تصمیم‌های ثبت‌شده

<!-- از اینجا شروع کن -->
"""

STRATEGY_STUB = """# Product Strategy & Scope (پروژه Kiloos Club)

> **منبع اصلی:** Google Drive → «Kiloos Club — Product Strategy & Scope» نسخه ۰.۱ (شامل اسناد ۰۱ تا ۱۲).
> این فایل نقطه ورود repo است، نه جایگزین سند اصلی.

## خلاصه قابل اتکا
`../../.agent/CONTEXT.md` — دانش فشرده و شناسه‌دار محصول (محدوده، قوانین، داده، امتیازدهی، فازها).

## قاعده
هر عدد/سیاست در سند اصلی که تأیید نشده، `PROPOSED` است. تصمیم‌های باز:
`../decisions/open-decisions.md`.

## آخرین تطبیق
YYYY-MM-DD
"""


def write_if_allowed(path: Path, content: str, force: bool, stats: dict[str, list[str]]) -> None:
    if path.exists() and not force:
        stats["skipped"].append(str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    stats["created"].append(str(path))


def copy_tree(src: Path, dst: Path, force: bool, stats: dict[str, list[str]]) -> None:
    for item in sorted(src.rglob("*")):
        if item.is_dir():
            continue
        target = dst / item.relative_to(src)
        if target.exists() and not force:
            stats["skipped"].append(str(target))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        stats["created"].append(str(target))


def render_open_decisions(seed: dict) -> str:
    lines = [
        "# Open Decisions & Business Questions",
        "",
        "> وضعیت‌های مجاز: `APPROVED` · `PROPOSED` · `ASSUMPTION` · `OPEN` · `IMPLEMENTED` · `DEPRECATED`.",
        "> تصمیم کسب‌وکار را به‌جای کارفرما نهایی نکن. هر فرض موقت باید کم‌ریسک و قابل بازگشت باشد.",
        "",
        f"منبع seed: `{seed.get('source', '')}` — تولید: {seed.get('generated_at', '')}",
        "",
    ]
    for od in seed.get("open_decisions", []):
        lines += [
            f"## {od['id']} — {od['topic']}",
            "",
            f"- Status: {od.get('status', 'OPEN')}",
            f"- Owner: {od.get('owner', '')}",
            f"- Needed by: {od.get('needed_by', '')}",
            f"- Impact: {', '.join(od.get('impact', []))}",
            "",
            f"**سؤال:** {od.get('question', '')}",
            "",
            f"**فرض موقت فعلی (ASSUMPTION):** {od.get('assumption', '—')}",
            "",
            "**تصمیم نهایی:** —",
            "",
            "---",
            "",
        ]
    arches = seed.get("open_architecture_decisions", [])
    if arches:
        lines += ["## تصمیم‌های باز معماری", ""]
        lines += [f"- [ ] {item}" for item in arches]
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install the Kiloos agent kit into a repository.")
    parser.add_argument("--target", required=True, help="Target repository root")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args(argv)

    if not (KIT_ROOT / "AGENTS.md").is_file():
        print(f"error: kit root not found at {KIT_ROOT} (missing AGENTS.md)")
        print("run this script from the original kit folder, not from .agent/tools")
        return 2

    target = Path(args.target).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)

    stats: dict[str, list[str]] = {"created": [], "skipped": []}
    today = date.today().isoformat()

    # 1. Master contract at repo root (auto-read by coding agents)
    write_if_allowed(target / "AGENTS.md", (KIT_ROOT / "AGENTS.md").read_text(encoding="utf-8"), args.force, stats)

    # 2. Portable kit copy
    agent_dir = target / ".agent"
    for name in ("CONTEXT.md", "MASTER_PROMPT.fa.md"):
        write_if_allowed(agent_dir / name, (KIT_ROOT / name).read_text(encoding="utf-8"), args.force, stats)
    for sub in ("roles", "playbooks", "templates", "context", "tools"):
        copy_tree(KIT_ROOT / sub, agent_dir / sub, args.force, stats)

    # 3. Docs skeleton
    for rel in DOC_DIRS:
        (target / "docs" / rel).mkdir(parents=True, exist_ok=True)

    write_if_allowed(target / "docs" / "README.md", DOCS_README, args.force, stats)
    write_if_allowed(target / "docs" / "decisions" / "decision-log.md", DECISION_LOG, args.force, stats)
    write_if_allowed(
        target / "docs" / "product" / "strategy-and-scope.md",
        STRATEGY_STUB.replace("YYYY-MM-DD", today),
        args.force,
        stats,
    )

    seed = json.loads(SEED_OPEN_DECISIONS.read_text(encoding="utf-8"))
    write_if_allowed(
        target / "docs" / "decisions" / "open-decisions.md",
        render_open_decisions(seed),
        args.force,
        stats,
    )

    current_state = (KIT_ROOT / "templates" / "current-state.md").read_text(encoding="utf-8")
    current_state = current_state.replace(
        "<!-- YYYY-MM-DD / تاریخ شمسی -->",
        f"{today} (۱۸ آبان ۱۴۰۵)",
    )
    write_if_allowed(target / "docs" / "handoffs" / "current-state.md", current_state, args.force, stats)

    print(f"Kiloos agent kit → {target}")
    print(f"  created: {len(stats['created'])}")
    print(f"  skipped (exists): {len(stats['skipped'])}")
    print("\nNext:")
    print("  1) Read AGENTS.md and .agent/CONTEXT.md")
    print("  2) python3 .agent/tools/doctor.py --root .")
    print("  3) Declare MODE: P and start the first vertical slice")
    return 0


if __name__ == "__main__":
    sys.exit(main())
