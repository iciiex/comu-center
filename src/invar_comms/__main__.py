"""CLI: `python -m invar_comms health|config-check|db-init|serve|worker|kb-import`."""

from __future__ import annotations

import sys

from . import __version__
from .config import load_settings
from .domain.errors import ValidationError


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else "health"
    if command == "health":
        print(f"ok invar-comms {__version__}")
        return 0
    if command == "config-check":
        try:
            settings = load_settings()
        except ValidationError as exc:
            print(f"configuration error: {exc}", file=sys.stderr)
            return 2
        print(settings.redacted_summary())
        print("configuration: valid")
        return 0
    if command == "db-init":
        try:
            settings = load_settings()
        except ValidationError as exc:
            print(f"configuration error: {exc}", file=sys.stderr)
            return 2
        from .adapters.sqlite_store import SqliteStore

        with SqliteStore(settings.sqlite_path) as store:
            print(f"sqlite store ready: {settings.sqlite_path}")
            print(f"tables: {', '.join(store.table_names())}")
        return 0
    if command == "kb-import":
        # Usage: kb-import <file.json> <product_id> <approver_id>
        if len(args) != 4:
            print("usage: kb-import <file.json> <product_id> <approver_id>",
                  file=sys.stderr)
            return 2
        try:
            settings = load_settings()
        except ValidationError as exc:
            print(f"configuration error: {exc}", file=sys.stderr)
            return 2
        import json
        from datetime import UTC, datetime
        from pathlib import Path

        from .adapters.sqlite_store import SqliteKnowledgeStore, SqliteStore
        from .domain.knowledge import (
            ApprovalStatus,
            KnowledgeDocument,
            Sensitivity,
        )

        path = Path(args[1])
        try:
            raw_items = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"cannot read knowledge file: {exc}", file=sys.stderr)
            return 2
        if not isinstance(raw_items, list) or not raw_items:
            print("knowledge file must be a non-empty JSON list", file=sys.stderr)
            return 2
        now = datetime.now(UTC)
        imported = 0
        try:
            with SqliteStore(settings.sqlite_path) as store:
                knowledge = SqliteKnowledgeStore(store)
                for item in raw_items:
                    knowledge.add(KnowledgeDocument(
                        document_id=str(item["document_id"]),
                        version=int(item.get("version", 1)),
                        product_id=args[2],
                        title=str(item["title"]),
                        content=str(item["content"]),
                        source=str(item.get("source", f"kb-import:{path.name}")),
                        status=ApprovalStatus.APPROVED,
                        sensitivity=Sensitivity(
                            str(item.get("sensitivity", "public_faq"))),
                        updated_at=now,
                        approved_by=args[3],
                        approved_at=now,
                    ))
                    imported += 1
        except Exception as exc:  # noqa: BLE001 - CLI boundary: report, exit non-zero
            print(f"kb-import failed: {exc}", file=sys.stderr)
            return 2
        print(f"kb-import: approved and stored {imported} document(s) "
              f"for product {args[2]!r} by {args[3]!r}")
        return 0
    if command in {"serve", "worker"}:
        try:
            settings = load_settings()
        except ValidationError as exc:
            print(f"configuration error: {exc}", file=sys.stderr)
            return 2
        from .wiring import build_stack

        try:
            stack = build_stack(settings)
        except ValidationError as exc:
            print(f"configuration error: {exc}", file=sys.stderr)
            return 2
        try:
            if command == "worker":
                processed = stack.worker.drain()
                print(f"worker: processed {processed} job(s)")
                return 0
            from .adapters.http_api import build_server

            server = build_server(settings, stack.outbox, stack.store)
            print(
                f"listening on http://{settings.http_host}:{settings.http_port} "
                f"(live_messaging=False, ai_send_enabled={settings.ai_send_enabled})"
            )
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            return 0
        finally:
            stack.store.close()
    print(
        f"unknown command {command!r}; expected 'health', 'config-check', "
        "'db-init', 'serve', 'worker' or 'kb-import'",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
