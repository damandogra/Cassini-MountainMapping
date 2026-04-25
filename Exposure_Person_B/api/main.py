"""
api/main.py
===========
Issue #18 — FastAPI backend serving all 9 endpoints.

All endpoints:
  GET  /scenarios         → list of available return periods
  GET  /exposure/{ts}     → GeoJSON of flooded buildings
  GET  /roads/{ts}        → GeoJSON of roads with passability
  GET  /risk/{ts}         → CRI raster stats (GeoTIFF served as stream)
  GET  /alert             → current alert level (live Open-Meteo)
  GET  /citizen           → all community observations as GeoJSON
  POST /citizen           → submit a new observation
  GET  /action_cards      → ranked planner actions
  GET  /docs              → auto-generated Swagger UI (FastAPI built-in)

Start:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Path setup — allow running from the api/ subdirectory or project root
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _ROOT)

import config

# Late imports of project modules (same path tricks applied above)
from scripts import e_citizen as citizen_store
from scripts import g_action_generator
from scripts import d_early_warning


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Ounila Flood Decision System API",
    description=(
        "Flood risk data for the Ounila River catchment, Tighza, Morocco. "
        "Provides scenario exposure, road passability, risk index, live early "
        "warning, and community observations."
    ),
    version="1.0.0",
)

# CORS — allow the React frontend (Vite default port) and any localhost origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure DB exists on startup
citizen_store.init_db()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ObservationIn(BaseModel):
    lat:         float = Field(..., ge=-90,  le=90,  description="Latitude (WGS84)")
    lon:         float = Field(..., ge=-180, le=180, description="Longitude (WGS84)")
    event_type:  str   = Field(..., description="One of: flooding, road_blocked, structure_damage, evacuation_needed, infrastructure_damage, other")
    severity:    int   = Field(..., ge=1,   le=3,   description="1=minor, 2=moderate, 3=severe")
    description: str   = Field("",  description="Free-text description")
    reporter:    str   = Field("anonymous")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _valid_scenario(ts: str) -> str:
    """Normalise and validate a scenario key (e.g. 't100' → 'T100')."""
    ts_up = ts.upper()
    if ts_up not in config.SCENARIOS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown scenario '{ts}'. Valid: {list(config.SCENARIOS.keys())}",
        )
    return ts_up


def _load_geojson(path: str) -> dict:
    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail=f"Data file not found: {os.path.basename(path)}. "
                   "Run the analysis pipeline first.",
        )
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/scenarios", summary="List available flood scenarios")
def get_scenarios():
    """
    Returns the list of return-period scenarios that have been processed.
    A scenario is 'available' if its exposure GeoJSON exists in outputs/.
    """
    available = []
    for ts, info in config.SCENARIOS.items():
        exposure_path = os.path.join(config.DATA_OUT, f"exposure_{ts}.geojson")
        available.append({
            "id":            ts,
            "label":         info["label"],
            "return_period": info["return_period"],
            "available":     os.path.exists(exposure_path),
        })
    return {"scenarios": available}


@app.get("/exposure/{scenario}", summary="Flooded buildings for a scenario")
def get_exposure(scenario: str):
    """
    GeoJSON FeatureCollection of buildings within the flood extent,
    with depth_m, velocity_ms, hazard_score, risk_level, and is_critical fields.
    """
    ts   = _valid_scenario(scenario)
    path = os.path.join(config.DATA_OUT, f"exposure_{ts}.geojson")
    return JSONResponse(_load_geojson(path))


@app.get("/roads/{scenario}", summary="Road passability for a scenario")
def get_roads(scenario: str):
    """
    GeoJSON FeatureCollection of road segments with flood_depth_m, status
    (passable / emergency_only / impassable), and color (green / orange / red).
    """
    ts   = _valid_scenario(scenario)
    path = os.path.join(config.DATA_OUT, f"road_passability_{ts}.geojson")
    return JSONResponse(_load_geojson(path))


@app.get("/risk/{scenario}", summary="CRI raster stats for a scenario")
def get_risk(scenario: str, fused: bool = Query(False, description="Use citizen-fused CRI if available")):
    """
    Returns JSON summary stats for the Composite Risk Index raster.
    Set ?fused=true to get the citizen-signal-fused version.

    To download the raw GeoTIFF, use /risk/{scenario}/download.
    """
    ts = _valid_scenario(scenario)
    prefix = "cri_fused" if fused else "cri"
    summary_path = os.path.join(config.DATA_OUT, "cri_summary.json")

    if os.path.exists(summary_path):
        with open(summary_path) as f:
            all_summary = json.load(f)
        if ts in all_summary:
            return all_summary[ts]

    raise HTTPException(
        status_code=404,
        detail="CRI summary not found. Run 03_risk_index.py first.",
    )


@app.get("/risk/{scenario}/download", summary="Download CRI GeoTIFF")
def download_risk(scenario: str, fused: bool = Query(False)):
    """Stream the CRI raster GeoTIFF file."""
    ts     = _valid_scenario(scenario)
    prefix = "cri_fused" if fused else "cri"
    path   = os.path.join(config.DATA_OUT, f"{prefix}_{ts}.tif")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="CRI raster not found.")
    return FileResponse(path, media_type="image/tiff",
                        filename=f"{prefix}_{ts}.tif")


@app.get("/alert", summary="Current early warning alert level")
def get_current_alert():
    """
    Fetches the 24-hour rainfall forecast from Open-Meteo for the Ounila
    catchment centroid and returns the EU Floods Directive alert level.

    Alert levels: green → yellow → orange → red
    """
    return d_early_warning.get_alert()


@app.get("/citizen", summary="Community observations as GeoJSON")
def get_citizen_observations(
    event_type:   Optional[str] = Query(None, description="Filter by event type"),
    min_severity: int           = Query(1,    ge=1, le=3, description="Minimum severity"),
):
    """
    Returns all community observations as a GeoJSON FeatureCollection.
    Optionally filter by event_type and minimum severity.
    """
    return citizen_store.as_geojson(
        event_type=event_type,
        min_severity=min_severity,
    )


@app.post("/citizen", summary="Submit a community observation", status_code=201)
def post_citizen_observation(obs: ObservationIn):
    """
    Submit a new community observation.

    event_type must be one of:
      flooding, road_blocked, structure_damage,
      evacuation_needed, infrastructure_damage, other

    severity: 1=minor, 2=moderate, 3=severe
    """
    try:
        obs_id = citizen_store.add_observation(
            lat=obs.lat,
            lon=obs.lon,
            event_type=obs.event_type,
            severity=obs.severity,
            description=obs.description,
            reporter=obs.reporter,
        )
        return {"status": "created", "id": obs_id}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/action_cards", summary="Ranked planner action cards")
def get_action_cards(
    scenario: str = Query(
        "T100",
        description="Scenario to generate actions for (T10/T50/T100/T500)"
    ),
):
    """
    Returns a ranked list of recommended actions for emergency planners.
    Priority order: CRITICAL → HIGH → MEDIUM.

    Reads from data/outputs/action_cards.json if it exists,
    otherwise generates on-the-fly (slower, ~1 s).
    """
    ts = _valid_scenario(scenario)

    # Try cached file first
    cached_path = os.path.join(config.DATA_OUT, "action_cards.json")
    if os.path.exists(cached_path):
        with open(cached_path) as f:
            cards = json.load(f)
        # Filter to requested scenario
        cards = [c for c in cards if c.get("scenario") == ts]
        if cards:
            return {"scenario": ts, "count": len(cards), "cards": cards}

    # Generate on-the-fly
    cards = g_action_generator.generate_action_cards(ts)
    return {"scenario": ts, "count": len(cards), "cards": cards}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok", "service": "ounila-flood-api"}