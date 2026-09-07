# Paleologos Production Remote Dashboard v1.9.0

Read-only Railway/PWA mirror of the factory production flow.

Required Railway variables:
- `SYNC_TOKEN`: copy from the local Tracking Service -> REMOTE SYNC TOKEN.
- `DASHBOARD_PASSWORD`: password used to open the remote dashboard.

Optional:
- `DASHBOARD_SECRET_KEY`: explicit Flask session key. If omitted it is derived from the two values above.

The remote service has no endpoint that modifies local production state.
