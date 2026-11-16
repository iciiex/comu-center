# Business Decision Register (real-import spike)

Source of truth in the application: `app/realimport/decisions.seed.json`, loaded into `ri_business_decisions` and served
read-only at `GET /api/v1/ri/decisions` and in the *Decision register* tab. A decision becomes CONFIRMED through the
business owner, never through the UI. Status words: `OPEN` (no assumption), `ASSUMPTION`, `PROPOSED`, `CONFIRMED`.

| ID | Question | Current assumption | Impact | Status | Required approver |
|---|---|---|---|---|---|
| BD-01 | Month/year of the workbook | Shahrivar 1405 (Jalali), editable in the import configuration | period of all data | CONFIRMED | Business owner |
| BD-02 | Authoritative branch-group definition (four coexist) | none; two lookup schemes imported, UNCONFIRMED | supervisor/head ladders, Karaj | OPEN | Sales operations + Finance |
| BD-03 | Approved thresholds, step amounts, rates | manager ladder 0.97/1.12/1.22/1.32 plus per-row amounts as PROPOSED rule sets | every reward (indicative only) | PROPOSED | Business owner / Finance |
| BD-04 | Target source and owner | targets read from the manager sheet, UNCONFIRMED | achievement | OPEN | Sales planning |
| BD-05 | Carton basis: fractional base sheet or integer-cast derived sheet | base sheet default (configurable) | 55.583 cartons, 294 keys | ASSUMPTION | Sales operations |
| BD-06 | Coverage of zero/negative-purchase customers | not implemented | seller retail matrix | OPEN | Sales operations |
| BD-07 | Duplicate business keys (5) | keep all rows, flagged | small carton differences | ASSUMPTION | Sales operations |
| BD-08 | VIP employee vs visitor-code reward aggregation (76 shared codes) | employee and assignment modelled separately; no seller reward yet | VIP seller rewards | OPEN | Sales operations + HR |
| BD-09 | Manager relief (ارفاق) and manual corrections | not modelled; workbook figures kept as references | 16 of 47 manager input figures differ | OPEN | Finance |
| BD-10 | Manager/head hierarchy and missing identifiers | codes imported as-is; gaps listed | head/supervisor roll-ups | OPEN | HR + Sales operations |
| BD-11 | Matador league and HQ rewards | out of scope | large manual amounts in the workbook | OPEN | Management |
| BD-12 | Monetary sales value availability | no carton to Rial conversion | Rial-based demo dashboards | OPEN | Finance |
| BD-13 | May real names or codes appear on screens or demos? | no: pseudonyms only | privacy, demo safety | ASSUMPTION | Data protection owner |
| BD-14 | Customer-group main groups; manager line labels (e.g. 1-2) to sales lines | literal parsing, UNCONFIRMED | which sales feed which target | ASSUMPTION | Sales operations |

Nothing in the prototype is marked APPROVED; the database schema cannot store an approved rule set.
