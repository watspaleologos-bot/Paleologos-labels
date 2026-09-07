# Paleologos Production — Railway PWA v1.9.4

Read-only Railway/PWA mirror of the factory production flow.

Required Railway variables:
- `SYNC_TOKEN`: copy from the local Tracking Service -> REMOTE SYNC TOKEN.
- `DASHBOARD_PASSWORD`: password used to open the remote dashboard.

Optional:
- `DASHBOARD_SECRET_KEY`: explicit Flask session key. If omitted it is derived from the two values above.

The remote service has no endpoint that modifies local production state.

## v1.9.1
- Official Stroma logo used for 192×192 and 512×512 PWA/app icons.
- Manifest and service-worker cache updated so the new icon is used after reinstall.
## v1.9.4
- Added `Τελευταία ώρα` after Barcode in the production-flow tables.
- Ready and Warehouse show the READY timestamp; Delivered shows the delivery timestamp, matching the desktop flow window.
- Supports the normalized `last_status_at` field from local v1.9.4 and falls back to existing `ready_at` / `delivered_at` fields for compatibility.

