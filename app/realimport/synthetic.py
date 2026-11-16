"""Synthetic workbook in the *real layout* (fictional people, codes and numbers).

Used by tests and by the UI so the prototype can be demonstrated without any real personal data.
It deliberately reproduces the workbook's pathologies: Arabic/Persian letter variants, fractional and
negative cartons, duplicate business keys, a personnel code shared by two visitor keys, a '#N/A'
code, missing head codes, a swapped factor header, a derived sheet with integer-cast net cartons,
a visitor missing from the roster and several kinds of rejected rows.
"""

from __future__ import annotations

import io
import random
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from openpyxl import Workbook

from app.realimport import profile as P

MONTH = "شهریور"
BRANCHES = ["تهران نمونه", "کرج", "بوشهر"]
KARAJ_ARABIC = "كرج"  # Arabic kaf: same branch, different code points (audit §H defect 1)
LINES = {"1": "لاين يک", "2": "لاین دو", "G": "لاين G"}
CUSTOMER_GROUPS = {"خرده یک": "خرده", "خرده دو": "خرده", "عمده یک": "عمده", "هورکا یک": "هورکا"}
SKUS = [("EFES", "AVE_900001", "Synthetic EFES A", "1"), ("EFES", "AVE_900002", "Synthetic EFES B", "0.5"),
        ("Matador", "AVE_900101", "Synthetic Matador A", "1"), ("Matador", "AVE_900102", "Synthetic Matador B", "1")]
NET_CHOICES = [12, 7.5, 5.833333333333333, 3.3333333333333335, 0, -2, 24, 18.25, 9.0]
STEPS = [70_000_000, 80_000_000, 100_000_000, 110_000_000]
THRESHOLDS = [Decimal("0.97"), Decimal("1.12"), Decimal("1.22"), Decimal("1.32")]
SALES_HEADERS = ["شعبه پخش", "ماه", "ویزیتور", "گروه مشتری", "کانال فروش", "کد مشتری", "برند", "نام کالا", "کد کالا",
                 "کارتن ناخالص منهای برگشتی (کارتن)", "کارتن خالص منهای برگشتی (کارتن)", "تعداد فاکتور (فاکتور)",
                 "کد", "نوع", "گروه", "ضریب", "نام", "تامین کننده", "سرپرست", "رئیس"]
DERIVED_EXTRA = ["گروه شعبه", "ضریب کارتن", "کارتن خالص تبدیلی", "کارتن ناخالص تبدیلی"]
ROSTER_HEADERS = ["شعبه ", "ویزیتور", "نام ویزیتور(بدون کد )", "نام سرپرست", "نام رئیس ", "لاین فروش", "نوع فروشنده", "st",
                  "کد پرسنلی ویزیتور", "تاریخ استخدام", "کد پرسنلی سرپرست", "کد پرسنلی رئیس", "نوع", "Column1", "بیس "]
MANAGER_HEADERS = [None, "ماه", "تامین کننده", "برند", "شعبه", "لاین", "سطح", " مدیر", "مدیرکل", "معاون منطقه", "کد پرسنلی مدیر",
                   "کد پرسنلی مدیرکل", "هدف  ماه", "فروش قطعی", "تحقق قطعی", "ارفاق", "مبلغ", "پله 1", "پله 2", "پله 3", "پله 4"]


def _round_away(value: float) -> int:
    return int(Decimal(repr(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _ladder(achievement: Decimal) -> int:
    reward = 0
    for threshold, amount in zip(THRESHOLDS, STEPS, strict=True):
        if achievement >= threshold:
            reward = amount
    return reward


def build_synthetic_workbook(seed: int = 7) -> tuple[bytes, dict[str, Any]]:
    rng = random.Random(seed)
    roster, seq = [], 0
    for b_index, branch in enumerate(BRANCHES):
        for letter, line in (("R", "1"), ("R", "2"), ("W", "G"), ("V", "1")):
            seq += 1
            roster.append({"branch": branch, "seq": seq, "letter": letter, "line": line, "code": 9_000_000 + seq,
                           "head": 7_000_000 + b_index if b_index == 0 else 0})
        if b_index < 2:  # a VIP selling through a second line: SAME personnel code, second visitor key
            seq += 1
            roster.append({"branch": branch, "seq": seq, "letter": "V", "line": "2", "code": 9_000_000 + seq - 1,
                           "head": 7_000_000 + b_index if b_index == 0 else 0})
    roster[2]["code"] = "#N/A"  # one visitor without a usable personnel code
    for r in roster:
        r["key"] = f"{r['seq']}-Demo Seller {r['seq']:03d}_{r['letter']}"

    rows: list[list[Any]] = []
    for r in roster:
        for c in range(6):
            brand, sku_code, sku_name, factor = SKUS[(r["seq"] + c) % len(SKUS)]
            branch = KARAJ_ARABIC if r["branch"] == "کرج" and c % 2 == 0 else r["branch"]
            net = rng.choice(NET_CHOICES)
            gross = net + rng.choice([0, 0, 1, 2])
            rows.append([branch, MONTH, r["key"], list(CUSTOMER_GROUPS)[c % 4], LINES[r["line"]],
                         5_000_000 + r["seq"] * 100 + c, brand, sku_name, sku_code, float(gross), float(net), rng.randint(1, 3),
                         r["code"], None, None, float(factor), f"Fictional Person {r['seq']:03d}", None, "Fictional Supervisor", None])
    valid_keys = len(rows)
    rows.append(list(rows[0][:9]) + [3.0, 4.5, 1] + list(rows[0][12:]))  # duplicate business key, different net
    orphan = list(rows[1])
    orphan[2] = "999-Demo Orphan_R"  # visitor absent from the roster
    rows.append(orphan)
    bad_month = list(rows[3]); bad_month[1] = "مهر"; rows.append(bad_month)  # noqa: E702
    no_customer = list(rows[4]); no_customer[5] = None; rows.append(no_customer)  # noqa: E702
    bad_net = list(rows[5]); bad_net[10] = "abc"; rows.append(bad_net)  # noqa: E702

    derived = [list(r) for r in rows]
    for d in derived:
        net = d[10]
        d[10] = float(_round_away(net)) if isinstance(net, float) else net
        d.extend([1 if d[0] in ("تهران نمونه",) else 2, d[15], d[10] if isinstance(d[10], float) else None, d[9]])
    rng.shuffle(derived)

    # manager sheet: targets + the figures a workbook would report (one row deliberately adjusted by hand)
    cells: dict[tuple[str, str], float] = {}
    for r in rows[: valid_keys + 2]:  # base rows + duplicate-key row + orphan-visitor row (all valid facts)
        branch = "کرج" if r[0] == KARAJ_ARABIC else r[0]
        if r[6] != "EFES":
            continue
        code = next(k for k, v in LINES.items() if v == r[4])
        cells[(branch, "1-2" if code in ("1", "2") else code)] = cells.get((branch, "1-2" if code in ("1", "2") else code), 0.0) + r[10]
    manager_rows, expected_rewards = [], {}
    for index, ((branch, group), total) in enumerate(sorted(cells.items())):
        target = float(max(1, round(total / rng.choice([0.9, 1.0, 1.15, 1.35]))))
        definitive = total + (3.5 if index == 1 else 0.0)
        achievement = Decimal(repr(definitive)) / Decimal(repr(target))
        reward = _ladder(achievement.quantize(Decimal("0.000001")))
        expected_rewards[f"{branch}|{group}"] = reward
        manager_rows.append([None, MONTH, "Synthetic supplier", "افس", branch, f" {group}" if index % 2 else group, "مدیر",
                             "Fictional Manager", "-", "Fictional Deputy", 8_100_000 + index, "-", target, definitive,
                             float(achievement), None, float(reward), *STEPS])

    wb = Workbook()
    ws = wb.active
    ws.title = "فروش"
    ws.append(SALES_HEADERS)
    for r in rows:
        ws.append(r)
    wd = wb.create_sheet("SalesData")
    wd.append(SALES_HEADERS + DERIVED_EXTRA)
    for r in derived:
        wd.append(r)
    wr = wb.create_sheet("تیم")
    wr.append(ROSTER_HEADERS)
    for r in roster:
        wr.append([r["branch"], r["key"], f"Fictional Person {r['seq']:03d}", "Fictional Supervisor", "Fictional Head", r["line"],
                   {"R": "خرده", "W": "عمده یا تعاونی", "V": "VIP"}[r["letter"]], 1, r["code"], "1398/12/05", 8_000_000 + r["seq"] % 3,
                   r["head"], r["letter"], r["branch"], None])
    wf = wb.create_sheet("ضرایب کارتنی")
    wf.append(["برند", "کد کالا", "نام کالا", "ضریب کارتن"])
    for brand, code, name, factor in SKUS:  # header labels swapped on purpose, as in the real sheet
        wf.append([brand, name, code, float(factor)])
    wf.append(["T-REX", "Synthetic Other", "AVE_900101", 0.25])  # same code, different factor
    wg = wb.create_sheet("گروه شعب")
    wg.append(["شعبه ", "گروه", "گروه 2"])
    for i, branch in enumerate(BRANCHES):
        wg.append([branch, 1 if i < 2 else 2, 1])
    wc = wb.create_sheet("CustomerGroup")
    wc.append(["گروه مشتری", "گروه اصلی"])
    for name, main in CUSTOMER_GROUPS.items():
        wc.append([name, main])
    wm = wb.create_sheet("مدیر افس")
    wm.append([])
    wm.append([None, "افس"])
    wm.append(MANAGER_HEADERS)
    for r in manager_rows:
        wm.append(r)
    wb.create_sheet(P.SYNTHETIC_MARKER_SHEET).append(["Synthetic fixture: fictional data only. Not Kiloos data."])
    buffer = io.BytesIO()
    wb.save(buffer)

    manifest = {
        "rows_primary": len(rows), "rows_derived": len(derived), "valid_primary": len(rows) - 3, "rejected_primary": 3,
        "duplicate_key_rows": 1, "branch_variants": 1, "roster_rows": len(roster),
        "expected_rewards": expected_rewards, "manager_rows": len(manager_rows), "adjusted_manager_rows": 1,
        "net_sum_primary": str(sum(Decimal(repr(r[10])) for r in rows[: valid_keys + 2] if isinstance(r[10], float))),
    }
    return buffer.getvalue(), manifest


def synthetic_workbook_bytes() -> bytes:
    return build_synthetic_workbook()[0]
