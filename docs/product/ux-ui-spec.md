# UX/UI Specification (prototype)

- Status: **PARTIAL** — implemented screens are listed below; the full spec is doc 08.
- Mode: P

## Implemented
- Login (demo picker) → Home (wallet, rank, missions, recent activity)
- Missions list → Mission detail → Submit with photo → Submission status (timeline + why-this-score)
- My points (balance + history) → Leaderboard (period, rank, tie-break note)
- Admin: review queue (tabs) → Review screen → approve/reject with reason
- Admin: missions list → create/edit form → publish/archive

## UX rules applied
- Mobile-first, RTL, Persian digits, Jalali dates for display.
- States: loading is server-rendered; empty and error states implemented; unauthorized → 403 page.
- Sample data is labeled in the persistent demo strip and with «نمونه» pills.

## Gaps
- No skeleton/loading transitions (server-rendered).
- No offline behaviour.
- No profile screen (nav has 4 items).
- Date input in admin is Gregorian (documented).

## Next
Align the eventual mobile app (Flutter/React Native, stack `OPEN`) with these flows; keep the
copy short and the primary CTA singular per screen.
