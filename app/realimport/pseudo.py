"""Deterministic pseudonyms so personal identifiers never leave the isolated database.

``V-`` visitor key, ``E-`` employee (person), ``C-`` customer. HMAC-SHA256 with a secret key:
the same input always gives the same pseudonym (joins and idempotency keep working) but the
pseudonym cannot be reversed or brute-forced without the key.

``scrub`` is a last-line guard used by the API layer: given the known raw values of a batch it
refuses to serialise a payload that still contains one of them.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Iterable
from typing import Any

PREFIXES = {"visitor": "V", "employee": "E", "customer": "C"}


def pseudonym(kind: str, norm_value: str, key: str) -> str:
    prefix = PREFIXES[kind]
    digest = hmac.new(key.encode(), f"{kind}|{norm_value}".encode(), hashlib.sha256).hexdigest()
    return f"{prefix}-{digest[:10].upper()}"


class PiiLeak(RuntimeError):
    """A response payload contained a raw personal value (programming error, never shipped)."""


def _strings(node: Any):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield str(k)
            yield from _strings(v)
    elif isinstance(node, (list, tuple)):
        for v in node:
            yield from _strings(v)


def assert_clean(payload: Any, raw_values: Iterable[str], *, min_len: int = 4) -> None:
    """Raise ``PiiLeak`` if a raw personal value reached the payload.

    Numeric-looking values (customer / personnel codes) are compared against whole string values
    only, so a count such as 27946 can never cause a false alarm; non-numeric values (visitor keys,
    which embed names) are also matched as substrings of any string.
    """
    exact, fuzzy = set(), []
    for value in raw_values:
        value = str(value).strip()
        if len(value) < min_len:
            continue
        exact.add(value)
        if not value.replace(".", "").isdigit():
            fuzzy.append(value)
    for text in _strings(payload):
        if text in exact or (len(text) >= min_len and any(v in text for v in fuzzy)):
            raise PiiLeak("a raw personal value reached an API response")
