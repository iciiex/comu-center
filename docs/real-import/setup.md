# Real-import spike — setup and run

MODE: P · branch `real-import-spike` (both repos) · everything below is isolated from the demo
(`kiloos-demo`, port 8090, volume `kiloos-data`).

## Layout

```
kilos-demo/
  spike/
    comu-center/          git worktree, branch real-import-spike   (backend)
    sales-quest-arena/    git worktree, branch real-import-spike   (frontend)
    Dockerfile, docker-compose.yml, .dockerignore, spike.ps1       (spike infra, compose project "kiloos-spike")
    e2e/ri-acceptance.mjs                                           (real-browser acceptance)
```

The demo working trees (`kilos-demo/comu-center`, `kilos-demo/sales-quest-arena`) stay on `kiloos-demo`.

## Start the isolated prototype (Docker Desktop only)

```powershell
cd kilos-demo\spike
.\spike.ps1 up        # http://localhost:8091 - own image, DB /data/spike/kiloos-spike.db, volume spike-data
.\spike.ps1 reset     # delete ONLY the spike volume and start clean
.\spike.ps1 test      # ruff + pytest + vitest + tsc + build, in Docker
.\spike.ps1 down
```

Sign in as **Administrator** (account picker), then open the tab **Real import (spike)** (visible only when
`KILOOS_REAL_IMPORT=1`, which only the spike image sets).

## Walk-through

1. *Import center*: **Download synthetic workbook** (real layout, fictional data) or **Choose .xlsx workbook**
   (the real workbook; it is only read, and stored once under its SHA-256).
2. *Import & preview*: inspect sheets, set the period (Jalali, default Shahrivar 1405, editable), **Validate & stage**,
   review rejected rows, mapping issues and the pseudonymised preview, then **Confirm import**.
3. *Mappings*: branch-group definitions, customer groups, employee vs visitor assignments (all UNCONFIRMED).
4. *Rules & runs*: PROPOSED rule sets, **Run on this batch**, results, **Trace** (run id, import batch id, rule version,
   exact input records).
5. *Reconciliation*: import level (base vs derived sheet, the 55.583-carton gap) and calculation level.
6. *Summary*: brand by organizational level. *Decision register*: BD-01 to BD-14.

Uploading the same file again opens the existing batch; validate, confirm and run repeat as no-ops.

## Command line and tests

```powershell
# opt-in tests against the real file (skipped otherwise); the file is mounted read-only
docker run --rm -v "<path>\workbook.xlsx:/wb/workbook.xlsx:ro" -e KILOOS_REAL_WORKBOOK=/wb/workbook.xlsx kiloos-spike-test pytest tests/test_realimport_real_workbook.py
# aggregates-only import into the spike volume
.\spike.ps1 import-real "<path>\workbook.xlsx"
# real-browser acceptance (needs a folder with node_modules/playwright; uses installed Chrome); run after .\spike.ps1 reset
$env:PW_DIR="<folder>"; node e2e\ri-acceptance.mjs ["<path>\workbook.xlsx"]
```

## Configuration (environment)

| Variable | Meaning |
|---|---|
| `KILOOS_REAL_IMPORT=1` | registers `/api/v1/ri/*` (absent means 404) |
| `KILOOS_REAL_IMPORT_DIR` | workbook store (files named `<sha256>.xlsx`) |
| `KILOOS_REAL_IMPORT_MAX_BYTES` | upload limit, default 25 MB |
| `KILOOS_PSEUDONYM_KEY` | HMAC key for `V-`, `E-`, `C-` pseudonyms (throw-away value in the spike compose file) |

## Data protection

The raw layer of the spike database contains the workbook's personal values (visitor keys embed names; personnel and
customer codes). It lives only in the `spike-data` Docker volume. No API response, log, screenshot, fixture or commit
exposes it (see `tests/test_realimport.py::test_no_raw_personal_value_in_any_api_response`). Remove it with
`.\spike.ps1 reset` or `docker volume rm kiloos-spike_spike-data`.
