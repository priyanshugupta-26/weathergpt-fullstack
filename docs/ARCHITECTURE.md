# Architecture

```text
Weather / satellite / disaster / NWP APIs
                │
                ▼
      ingestion + validation workers
                │
        ┌───────┴────────┐
        ▼                ▼
   raw time-series     event store
        │                │
        ▼                ▼
 clean/features      disaster features
        │                │
        ├──────┬─────────┘
        ▼      ▼
 weather ML  disaster ML
        │      │
        └──┬───┘
           ▼
      FastAPI platform
  REST + WebSocket + auth
           │
     ┌─────┼──────────────┐
     ▼     ▼              ▼
  3D globe AI chat   alert/advisory UI
```

## Suggested production data layer

- PostgreSQL for users, configurations, alerts, metadata.
- TimescaleDB extension for dense temporal station/city data.
- PostGIS for geospatial hazard queries.
- Object storage + Zarr/NetCDF/Parquet for very large gridded model/satellite data.
- Redis for cache and fanout.

## Key backend modules to add next

- `ingestion/` scheduled connectors
- `pipelines/` cleaning + feature engineering
- `repositories/` Postgres/PostGIS access
- `inference/` model registry and versioning
- `llm/` tool-calling and RAG
- `notifications/` FCM, SMS, email, web push
- `nwp/` GFS/WRF adapters
- `gis/` tile/grid conversion and interpolation
