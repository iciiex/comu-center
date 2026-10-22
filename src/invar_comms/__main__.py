"""CLI entry points: `python -m invar_comms health|config-check`."""

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
    print(f"unknown command {command!r}; expected 'health' or 'config-check'", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
