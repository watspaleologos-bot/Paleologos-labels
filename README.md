# Paleologos Production — Railway PWA v1.11.1

Read-only Railway/PWA mirror of the factory production flow.

Required Railway variables:
- `SYNC_TOKEN`: copy from the local Tracking Service -> REMOTE SYNC TOKEN.
- `DASHBOARD_PASSWORD`: password used to open the remote dashboard.

Optional:
- `DASHBOARD_SECRET_KEY`: explicit Flask session key. If omitted it is derived from the two values above.

The remote service has no endpoint that modifies local production state. The local PC remains the source of truth.

## v1.9.1
- Official Stroma logo used for 192×192 and 512×512 PWA/app icons.
- Manifest and service-worker cache updated so the new icon is used after reinstall.

## v1.9.4
- Added `Τελευταία ώρα` after Barcode in the production-flow tables.
- Ready and Warehouse show the READY timestamp; Delivered shows the delivery timestamp, matching the desktop flow window.
- Supports the normalized `last_status_at` field from local v1.9.4 and falls back to existing `ready_at` / `delivered_at` fields for compatibility.

## v1.9.5
- Clickable sortable headers in all production-flow tabs: Σε παραγωγή, Έτοιμα, Παραδόθηκαν σήμερα, Αποθήκη.
- First click sorts ascending (▲), second click descending (▼).
- Sort choice is kept separately per tab and survives the dashboard's automatic refreshes.
- Sorting supports Greek text and numeric-aware values for dimensions, dates, barcodes and timestamps.

## v1.10.0
- Added a new `Ιστορικό` tab inside Ροή Παραγωγής.
- Monthly calendar shows per day: green `Έτοιμα` counts and blue `Παραδόθηκαν` counts; tapping a day filters the detailed history below.
- History filters: day, month, year, custom from/to range, all dates, plus Ready/Delivered event type.
- Detailed rows include actual status timestamp, customer, retail name, type, dimensions, production date and barcode, with sortable headers.
- History sync is incremental and read-only. Railway keeps a canonical in-memory mirror keyed by barcode and uses a local status-event cursor, so normal traffic sends only changed units.
- After a Railway restart/redeploy, the local PC automatically rebuilds missing history from the source database. No Railway database is required and local production remains independent of Internet/Railway availability.

## v1.10.1
- Production History calendar redesigned for compact desktop/mobile use.
- Day cells now show only a green dot + READY count and a blue dot + DELIVERED count; the long labels were removed from each cell.
- Future dates show only the day number, with no counts/dots and no history-click action.
- Mobile calendar cells were reduced substantially so the full month fits much more comfortably on one phone screen.

## v1.11.1
- Added a first `#` column to Σε παραγωγή, Έτοιμα, Παραδόθηκαν σήμερα and Αποθήκη.
- Row numbering is visual only and is recalculated from `1..N` after the active tab's current sorting, so it always matches the visible order.
- The Ιστορικό tab is unchanged and has no row-number column.
