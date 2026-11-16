"""Deterministic .xlsx bytes: openpyxl stamps the current time into docProps/core.xml and into every
zip entry header, so two identical workbooks generated a second apart hash differently (which broke
duplicate-file detection tests and would create duplicate fixture uploads). Pin all timestamps."""

from __future__ import annotations

import io
import re
import zipfile

FIXED = (2026, 11, 1, 0, 0, 0)
_STAMP = re.compile(rb"(<dcterms:(?:created|modified)[^>]*>)[^<]*(</dcterms:(?:created|modified)>)")


def deterministic_xlsx(raw: bytes) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw)) as src, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in sorted(src.infolist(), key=lambda i: i.filename):
            data = src.read(info.filename)
            if info.filename == "docProps/core.xml":
                data = _STAMP.sub(rb"\g<1>2026-11-01T00:00:00Z\g<2>", data)
            entry = zipfile.ZipInfo(info.filename, date_time=FIXED)
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = info.external_attr
            dst.writestr(entry, data)
    return out.getvalue()
