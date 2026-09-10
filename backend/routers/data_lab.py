"""WeatherGPT Data & Learning Lab REST API Router.
Handles endpoints for database statistics, paginated observations, side-panel feature inspection,
39-feature schema inspection, data quality, growth trends, CSV export, and live ingestion triggers.
"""

from typing import Any
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Response
from fastapi.responses import PlainTextResponse

from backend.services.data_lab import data_lab_service
from backend.ml.ingestion import ingestion_service, PILOT_LOCATIONS

router = APIRouter(prefix="/api/data", tags=["Data & Learning Lab"])


@router.get("/stats")
def get_data_stats():
    """Returns real-time database summary statistics."""
    return data_lab_service.get_top_summary_stats()


@router.get("/observations")
def get_observations(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=5, le=100),
    location: str | None = Query(None),
    provider: str | None = Query(None),
    start: str | None = Query(None),
    end: str | None = Query(None),
    data_type: str | None = Query(None),
    quality: str | None = Query(None),
    search: str | None = Query(None),
):
    """Returns server-side paginated observations with filtering."""
    return data_lab_service.get_paginated_observations(
        page=page,
        page_size=page_size,
        location=location,
        provider=provider,
        start=start,
        end=end,
        data_type=data_type,
        quality=quality,
        search=search,
    )


@router.get("/observations/{obs_id}")
def get_observation_detail(obs_id: int):
    """Returns side-panel feature inspection comparing used vs unused features."""
    try:
        return data_lab_service.get_observation_feature_inspection(obs_id)
    except ValueError as err:
        raise HTTPException(404, str(err))


@router.get("/features")
def get_feature_catalog():
    """Returns full 39-feature schema in exact order with current live sample values."""
    return data_lab_service.get_feature_catalog()


@router.get("/providers")
def get_providers():
    """Returns provider breakdown, record counts, and reliability status."""
    return data_lab_service.get_data_quality_breakdown().get("provider_distribution", {})


@router.get("/quality")
def get_quality_report():
    """Returns data quality breakdown, missingness by feature, and validation stats."""
    return data_lab_service.get_data_quality_breakdown()


@router.get("/growth")
def get_growth_chart_data():
    """Returns cumulative observation growth series and model training milestones."""
    return data_lab_service.get_database_growth()


@router.get("/locations")
def get_monitoring_locations():
    """Returns list of all active stations across India contributing observations."""
    return data_lab_service.get_contributing_locations()


@router.get("/export")
def export_dataset_csv(
    location: str | None = Query(None),
    provider: str | None = Query(None),
    start: str | None = Query(None),
    end: str | None = Query(None),
    data_type: str | None = Query(None),
    limit: int = Query(5000, ge=1, le=10000),
):
    """Streams a filtered CSV export of the observational dataset."""
    csv_content = data_lab_service.export_csv(
        location=location,
        provider=provider,
        start=start,
        end=end,
        data_type=data_type,
        limit=limit,
    )
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=weathergpt_observations_dataset.csv"
        },
    )


@router.post("/trigger-ingestion")
async def trigger_live_ingestion(location: str = Query("Patna")):
    """Trigger an immediate real observation fetch for judge demo."""
    # Find matching pilot location
    loc = next((p for p in PILOT_LOCATIONS if p["name"].lower() == location.lower()), PILOT_LOCATIONS[0])
    count = await ingestion_service.ingest_live_location(loc["latitude"], loc["longitude"])
    stats = data_lab_service.get_top_summary_stats()
    return {
        "status": "ingested",
        "location": loc["name"],
        "rows_added": count,
        "total_observations": stats["total_observations"],
        "latest_observation": stats["latest_observation"],
    }
