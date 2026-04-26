# to run locally:
you can use `run.md` to run the script

# 🌊 Atlas
### Tighza, Morocco
---

## Table of Contents

1. [What this project does](#what-this-project-does)
2. [Why Morocco / Ounila?](#why-morocco--ounila)
3. [Team roles](#team-roles)
4. [Repository structure](#repository-structure)
5. [Quick start — run the whole system](#quick-start--run-the-whole-system)
6. [Data sources](#data-sources)
7. [The pipeline, step by step](#the-pipeline-step-by-step)
   - [Stage 1 — Hydrology (Person A)](#stage-1--hydrology-person-a)
   - [Stage 2 — Data science (Person B)](#stage-2--data-science-person-b)
   - [Stage 3 — Frontend (Person C)](#stage-3--frontend-person-c)
8. [Shared config](#shared-config)
9. [Sync points and handoffs](#sync-points-and-handoffs)
10. [GitHub issues checklist](#github-issues-checklist)
11. [Outputs and what they mean](#outputs-and-what-they-mean)
12. [Scientific methods](#scientific-methods)
13. [Limitations and caveats](#limitations-and-caveats)

---

## What this project does

This system answers one question for emergency planners:

> **"If it rains hard tonight, which roads close, which villages get cut off, and what should we do first?"**

It does this in four stages:

```
RAIN DATA + TERRAIN
       ↓
  [Stage 1] Hydrology model
  Converts rainfall into flood depth maps
  for 4 scenarios: T10, T50, T100, T500 year
       ↓
  [Stage 2] Risk engine
  Overlays flood depths with buildings,
  roads, and population to score risk
       ↓
  [Stage 3] Web dashboard
  Interactive map showing which areas flood,
  which roads close, and what actions to take
       ↓
  PLANNERS MAKE DECISIONS
```

The final output is a **live web app** where a planner can:
- Switch between flood scenarios (10-year, 100-year, 500-year events)
- See which buildings, roads, and critical infrastructure are at risk
- Check which communities lose road access
- View a ranked action list (what to do, in what order)
- Download a PDF report for offline use
- Submit field observations from community members

---

## Why Morocco / Ounila?

The Ounila River drains the Anti-Atlas and High Atlas mountains near Tighza, Morocco. It is a **semi-arid flash flood catchment** — meaning it is normally dry, but extreme rainfall events cause rapid, dangerous flooding with little warning.

This type of catchment is common across North Africa and is **significantly underserved by existing flood tools**, most of which are built for European or North American river systems with dense gauge networks. Our system works with globally available free data — no local gauge data required.

Morocco has recorded devastating flash floods in this region. The Ounila valley (near Aït Benhaddou) is also home to villages, agricultural land, and tourist infrastructure that are all exposed.

---

## Team roles

| Person | Role | Primary tools |
|--------|------|---------------|
| **Person A** | Hydrology & modelling | QGIS, WhiteboxTools, Python (SCS-CN), HEC-RAS |
| **Person B** | Data science & risk engine | Python, rasterio, geopandas, osmnx, FastAPI |
| **Person C** | Frontend & decision interface | React, Mapbox GL JS, Recharts, jsPDF |

All three work in parallel. The only real dependency is that Person B needs depth rasters from Person A — which arrive on Day 2 morning. Until then, Person B runs everything on mock rasters.

---

## Repository structure

```
flood-ounila/
│
├── config.py                    ← SHARED: bounding box, paths, constants
├── requirements.txt             ← Python dependencies
├── README.md                    ← this file
│
├── data/
│   ├── raw/                     ← original downloaded files (gitignored)
│   ├── processed/               ← cleaned intermediates (gitignored for large files)
│   └── outputs/                 ← final outputs (geojsons, rasters, jsons)
│
├── hydrology/                   ← Person A
│   ├── morphometric_params.json ← catchment area, slope, Tc
│   ├── cn_value.json            ← SCS Curve Number
│   ├── hms_python/
│   │   ├── rainfall_frequency.py   ← GEV fit → T10/50/100/500 depths
│   │   └── run_hms.py              ← SCS-CN rainfall-runoff → hydrographs
│   └── ras/
│       └── hand_approximation.py   ← HAND fallback if RAS unavailable
│
├── data_science/                ← Person B
│   ├── exposure/
│   │   └── exposure_analysis.py    ← depth rasters → building risk scores
│   ├── risk/
│   │   └── risk_index.py           ← composite risk index (CRI)
│   ├── network/
│   │   └── network_analysis.py     ← road passability + isolation zones
│   └── api/
│       ├── main.py                 ← FastAPI server (9 endpoints)
│       ├── early_warning.py        ← rainfall → alert level
│       ├── citizen.py              ← community observations (SQLite)
│       ├── citizen_fusion.py       ← merge model + citizen signals
│       └── action_generator.py     ← rule-based action cards
│
└── frontend/
    └── flood-app/               ← Person C (React/Vite app)
        ├── src/
        │   ├── App.tsx              ← main map interface
        │   ├── api.ts               ← typed API service + mock stubs
        │   └── components/
        │       ├── ScenarioBar.tsx  ← T10/T50/T100/T500 switcher
        │       ├── SidePanel.tsx    ← metrics dashboard
        │       ├── CitizenForm.tsx  ← community observation form
        │       ├── ActionCards.tsx  ← planner action list
        │       └── PDFExport.tsx    ← report generator
        └── .env                     ← MAPBOX_TOKEN (never commit)
```

---

## Quick start — run the whole system

### Prerequisites

- Python 3.11+, conda or venv
- QGIS 3.x with WhiteboxTools plugin
- HEC-RAS 6.5 (optional — there is a fallback)
- Node.js 18+ and npm

### Step 1 — Clone and set up Python

```bash
git clone https://github.com/your-team/flood-ounila.git
cd flood-ounila

conda create -n flood python=3.11
conda activate flood
pip install -r requirements.txt
```

### Step 2 — Download the data (see Data sources section below)

Put downloaded files in `data/raw/`. The config file tells all scripts where to find them.

### Step 3 — Run the hydrology model

```bash
# After catchment delineation in QGIS (see Stage 1 below):
python hydrology/hms_python/rainfall_frequency.py   # produces rainfall_depths.json
python hydrology/hms_python/run_hms.py              # produces hydrograph_T*.csv
```

After HEC-RAS runs, depth rasters go to `data/outputs/depth_T*.tif`.

### Step 4 — Run the data science pipeline

```bash
python data_science/exposure/exposure_analysis.py    # produces exposure_T*.geojson
python data_science/risk/risk_index.py               # produces cri_T100.tif
python data_science/network/network_analysis.py      # produces road_passability_T*.geojson
python data_science/api/action_generator.py          # produces action_cards.json
```

### Step 5 — Start the API server

```bash
cd data_science/api
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

API is now live at `http://localhost:8000`. Visit `http://localhost:8000/docs` to see all endpoints.

### Step 6 — Start the frontend

```bash
cd frontend/flood-app
cp .env.example .env            # add your Mapbox token
npm install
npm run dev
```

App is now live at `http://localhost:5173`.

---

## Data sources

All data is **free and openly available**. No accounts required except Mapbox (free tier).

| Dataset | What it's used for | Where to download |
|---------|-------------------|-------------------|
| **Copernicus DEM GLO-30** (30m) | Terrain for delineation and flood routing | [browser.dataspace.copernicus.eu](https://browser.dataspace.copernicus.eu) |
| **ESA WorldCover 2021** (10m) | Land use for Curve Number calculation | [esa-worldcover.org/en/download](https://esa-worldcover.org/en/download) |
| **SoilGrids 250m** (ISRIC) | Soil texture → hydrological soil groups | [soilgrids.org](https://soilgrids.org) |
| **GHCN-Daily** (NOAA) | Historical daily rainfall at Ouarzazate station | [ncei.noaa.gov/cdo-web/search](https://www.ncei.noaa.gov/cdo-web/search) — station MA000060681 |
| **ERA5-Land** (ECMWF) | Fallback rainfall if GHCN has gaps | [cds.climate.copernicus.eu](https://cds.climate.copernicus.eu) |
| **OpenStreetMap** via osmnx | Buildings, roads, hospitals, schools | Downloaded automatically by `download_osm.py` |
| **WorldPop Morocco 2020** (100m) | Population exposure | [hub.worldpop.org/geodata/listing?id=76](https://hub.worldpop.org/geodata/listing?id=76) |
| **Copernicus EMS** | Flood validation (if available for site) | [emergency.copernicus.eu/mapping/list-of-activations-rapid](https://emergency.copernicus.eu/mapping/list-of-activations-rapid) |
| **Open-Meteo API** | Live rainfall forecast (no API key) | [open-meteo.com](https://open-meteo.com) — called automatically by the API |
| **Mapbox** | Basemap (satellite-streets) | [mapbox.com](https://mapbox.com) — free tier, 50k loads/month |

### Downloading the DEM (most important — do this first)

1. Go to [browser.dataspace.copernicus.eu](https://browser.dataspace.copernicus.eu)
2. Search "Copernicus DEM GLO-30"
3. Draw a bounding box: N=31.70, S=31.40, E=-6.95, W=-7.35
4. Download as GeoTIFF
5. Save to `data/raw/dem_ounila.tif`

**SRTM fallback:** If Copernicus DEM is unavailable, use SRTM 30m from [earthexplorer.usgs.gov](https://earthexplorer.usgs.gov) — search tile `n31_w008` or `n31_w007`.

---

## The pipeline, step by step

---

### Stage 1 — Hydrology (Person A)

**Goal:** Turn raw terrain and rainfall data into four flood depth maps — one for each return period scenario.

#### Step A1 — Catchment delineation (QGIS, ~90 min)

This figures out exactly which area of land drains into the Ounila outlet. Every drop of rain that falls inside this boundary eventually flows through our study point.

1. Open QGIS. Go to **Plugins → Manage → search WhiteboxTools → Install**.
2. Load `data/raw/dem_ounila.tif`.
3. **WhiteboxTools → BreachDepressions** — fixes artificial flat spots and pits in the terrain that would block water flow.
   - Input: `dem_ounila.tif`
   - Output: `data/processed/dem_conditioned.tif`
4. **WhiteboxTools → D8Pointer** — for each grid cell, calculates which direction water flows.
   - Input: `dem_conditioned.tif`
   - Output: `data/processed/d8pointer.tif`
5. **WhiteboxTools → D8FlowAccumulation** — counts how many cells drain through each point (high values = rivers).
   - Input: `d8pointer.tif`
   - Output: `data/processed/flowacc.tif`
6. **WhiteboxTools → ExtractStreams** — keeps only cells with flow accumulation > 200 (= rivers).
   - Input: `flowacc.tif`, threshold: `200`
   - Output: `data/processed/streams.tif`
7. Click the outlet point on the map. The outlet is where the Ounila gorge opens into the plain — approximately **31.52°N, 7.10°W**.
8. **WhiteboxTools → SnapPourPoint** — snaps your clicked point to the exact stream cell.
9. **WhiteboxTools → Watershed** — traces back from the outlet to find every cell that drains to it.
   - Output: `data/processed/catchment_raster.tif`
10. **Raster → Polygonize** — converts the raster to a polygon.
    - Output: `data/processed/catchment_boundary.geojson` ← **push to GitHub immediately**
11. Vectorize streams → `data/processed/stream_network.geojson` ← **push to GitHub immediately**

Both GeoJSONs are needed by Person B and Person C. Push them the moment they exist.

#### Step A2 — Morphometric parameters (QGIS / Python, ~30 min)

Measure these values and save to `hydrology/morphometric_params.json`:

| Parameter | How to measure | Why it matters |
|-----------|---------------|----------------|
| Area A (km²) | QGIS field calculator: `$area / 1000000` | Sets the scale of peak flows |
| Channel length L (m) | Measure longest flow path from divide to outlet | Controls time of concentration |
| Elevation drop H (m) | DEM value at headwater − DEM value at outlet | Used with L to get slope |
| Mean slope S (m/m) | `H / L` | Controls flow speed |
| Time of concentration Tc (min) | `0.0078 × (L_feet ^ 0.77) / (S_ftft ^ 0.385)` | How long before the flood peak arrives |

Save as:
```json
{
  "area_km2": 245.0,
  "channel_length_m": 38000,
  "elevation_drop_m": 1200,
  "slope_mm": 0.032,
  "tc_min": 87.4
}
```

#### Step A3 — Curve Number calculation (QGIS, ~60 min)

The SCS Curve Number (CN) is a single number from 0–100 that describes how much rainfall becomes runoff vs soaks into the ground. High CN (rocky, urban) = more runoff. Low CN (forest, wetland) = more absorption.

For Ounila, the dominant land cover is **bare rock and sparse scrub** — expect CN around 75–85.

1. Clip ESA WorldCover to the catchment boundary: **Raster → Extraction → Clip by mask layer**
2. Derive Hydrological Soil Group (A/B/C/D) from SoilGrids texture fractions:
   - Clay > 40% → Group D (least infiltration)
   - Clay 27–40%, sand < 20% → Group C
   - Clay 7–27%, sand 28–45% → Group B
   - Otherwise → Group A (most infiltration)
3. Look up CN from USDA NEH Part 630 Table 9-1:

| Land cover (WorldCover class) | Soil A | Soil B | Soil C | Soil D |
|-------------------------------|--------|--------|--------|--------|
| Tree cover (10) | 30 | 55 | 70 | 77 |
| Shrubland (20) | 35 | 56 | 70 | 77 |
| Grassland (30) | 39 | 61 | 74 | 80 |
| Cropland (40) | 67 | 78 | 85 | 89 |
| Built-up (50) | 77 | 85 | 90 | 92 |
| **Bare/sparse (60)** | **77** | **86** | **91** | **94** |
| Water (80) | 98 | 98 | 98 | 98 |

4. Compute area-weighted average: `CN = sum(CN_i × Area_i) / Total_Area`
5. Save to `hydrology/cn_value.json`:
```json
{
  "weighted_cn": 80,
  "antecedent_moisture": "AMC_II"
}
```

#### Step A4 — Rainfall frequency analysis (Python, ~45 min)

Fits a statistical distribution to historical daily rainfall records to estimate the 10-, 50-, 100-, and 500-year return period rainfall depths.

```bash
python hydrology/hms_python/rainfall_frequency.py
```

This produces `data/processed/rainfall_depths.json`:
```json
{
  "T10": 52.3,
  "T50": 78.1,
  "T100": 91.4,
  "T500": 124.7
}
```

These are the 24-hour rainfall depths (in mm) that statistically occur once every 10, 50, 100, or 500 years.

If GHCN has insufficient data for Ouarzazate, use ERA5-Land:
```bash
pip install cdsapi
# Then set up ~/.cdsapirc with your CDS key
# Edit rainfall_frequency.py to use ERA5 mode
```

#### Step A5 — Rainfall-runoff model (Python, ~2 hrs)

This replaces the HEC-HMS graphical interface entirely. The SCS-CN method is a closed-form equation — no GUI needed, and the Python version is more transparent and reproducible.

```bash
python hydrology/hms_python/run_hms.py
```

What the script does, in plain terms:
1. Takes the 24-hour rainfall depth for each scenario
2. Subtracts initial losses (water absorbed before runoff begins)
3. Converts remaining rain to runoff depth using the Curve Number
4. Shapes that runoff into a flood hydrograph (discharge over time) using the SCS Unit Hydrograph method
5. The peak of that hydrograph is the design flow that goes into HEC-RAS

Outputs: `data/outputs/hydrograph_T10.csv`, `hydrograph_T50.csv`, `hydrograph_T100.csv`, `hydrograph_T500.csv`

Each CSV looks like:
```
time_min,discharge_m3s
0,0.0
15,12.4
30,67.8
45,134.2
60,89.1
...
```

**Push these CSVs immediately.** Person B needs the peak discharge values to configure alert thresholds.

#### Step A6 — HEC-RAS 2D flood routing (HEC-RAS GUI, ~4 hrs)

This routes the hydrographs across the terrain to produce actual flood depth and velocity maps. This is the most compute-intensive step.

1. Open HEC-RAS 6.5. New project → save in `hydrology/ras/`
2. Open RAS Mapper
3. **Create New RAS Terrain** → import `dem_ounila.tif`
4. **2D Flow Area** → draw a polygon covering the river valley + 300m buffer each side
5. **Mesh generation**: set cell size to 20m in the channel, 40m on the floodplain
6. **Manning's n** values (roughness) by land cover:
   - Bare rock / gravel channel: 0.025
   - Sparse scrubland: 0.040
   - Dense palm/tamarisk: 0.080
   - Active water channel: 0.030
7. **Boundary conditions**:
   - Upstream: flow hydrograph → import from `hydrograph_T*.csv`
   - Downstream: normal depth, slope = S from morphometric params
8. **Run unsteady flow**: 48 hours, 5-minute timestep
9. Repeat for all four scenarios
10. **Export** from RAS Mapper:
    - `data/outputs/depth_T10.tif`, `depth_T50.tif`, `depth_T100.tif`, `depth_T500.tif`
    - `data/outputs/velocity_T10.tif`, `velocity_T50.tif`, `velocity_T100.tif`, `velocity_T500.tif`

**If HEC-RAS is unavailable or compute time is too long:** use the HAND approximation:
```bash
python hydrology/ras/hand_approximation.py
```
This uses Height Above Nearest Drainage to approximate flood extent — less accurate but fast.

#### Step A7 — Validation

How well does the model reproduce a real flood?

1. Download a Sentinel-1 SAR image from a past flood event at [scihub.copernicus.eu](https://scihub.copernicus.eu) or [asf.alaska.edu](https://asf.alaska.edu)
2. In QGIS: threshold your T100 depth raster at 0.1m → binary flood/no-flood polygon
3. Compute the **F score** (Bates & De Roo 2000):
   - A = area both model and satellite show as flooded
   - B = area only model shows as flooded
   - C = area only satellite shows as flooded
   - **F = A / (A + B + C)** — target > 0.5 (acceptable), > 0.65 (good)

Save to `hydrology/validation_results.json`.

---

### Stage 2 — Data science (Person B)

**Goal:** Take the depth/velocity rasters and turn them into risk scores, evacuation analysis, and an API that serves everything to the frontend.

#### Step B1 — Download supporting data (pre-work)

```bash
python data_science/download_osm.py    # buildings, roads, amenities
# manually download WorldPop from hub.worldpop.org → data/raw/worldpop_morocco.tif
```

Note: Tighza/Ounila is rural. OSM coverage is sparse. The pipeline handles this — even a handful of tagged buildings will work. If a village has no tagged buildings, add its centre point manually as a GeoJSON feature.

#### Step B2 — Exposure analysis

For each building in the flood zone, the script computes:

- **Depth** at the building centroid (sampled from the raster)
- **Velocity** at the building centroid
- **Hazard Rating (HR)** using the HR Wallingford formula: `HR = depth × (velocity + 0.5) + 0.5`
- **Vulnerability class**: critical (hospital/school) → weight 3.0; residential → 2.0; commercial → 1.0
- **Risk score**: `HR × vulnerability weight`

```bash
python data_science/exposure/exposure_analysis.py
```

Outputs: `data/outputs/exposure_T10.geojson`, `exposure_T50.geojson`, `exposure_T100.geojson`, `exposure_T500.geojson`

**While waiting for real rasters from Person A:** run on mock rasters. The code is identical — just a different input file path.

#### Step B3 — Composite Risk Index

Combines three layers into a single risk score per grid cell:

```
CRI = 0.5 × Physical Hazard + 0.3 × Population Exposure + 0.2 × Vulnerability
```

- **Physical Hazard (H):** depth reclassified 0–1 (0.3m=low, 1m=medium, 2m=high, >2m=extreme) combined with velocity hazard rating
- **Exposure (E):** WorldPop population density, normalised 0–1
- **Vulnerability (V):** proxy based on land cover and building age (rural semi-arid = 0.3)

Weights from Papathoma-Köhle et al. (2019).

```bash
python data_science/risk/risk_index.py
```

Output: `data/outputs/cri_T100.tif`

#### Step B4 — Road and evacuation analysis

For each road segment, samples the maximum flood depth from the raster and classifies it:

| Condition | Threshold | Classification |
|-----------|-----------|----------------|
| Cars passable | depth < 0.3m | Green |
| Emergency vehicles only | depth < 0.6m | Orange |
| All vehicles impassable | depth ≥ 0.6m | Red |

Then uses network analysis (osmnx + networkx) to find isolated communities — villages or districts that lose all road connections to the rest of the network.

```bash
python data_science/network/network_analysis.py
```

Outputs:
- `data/outputs/road_passability_T*.geojson` — each road edge with depth + passability status
- `data/outputs/evacuation_summary.json` — number of isolated communities per scenario

#### Step B5 — Action generator

Reads the exposure, network, and risk outputs and generates a ranked list of recommended actions for planners:

| Condition | Recommended action | Priority |
|-----------|-------------------|----------|
| Hospital + depth > 0.3m | Pre-plan evacuation route, install flood barrier | CRITICAL |
| Road = last route out | Install early warning gauge upstream | HIGH |
| Village + pop > 200 + depth > 1m | Issue evacuation order at T=X alert | HIGH |
| Bridge + depth > 1m + velocity > 2 m/s | Close bridge, assess structural risk | MEDIUM |

```bash
python data_science/api/action_generator.py
```

Output: `data/outputs/action_cards.json`

#### Step B6 — FastAPI backend

Serves all outputs to the frontend. Start the server:

```bash
cd data_science/api
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

All endpoints:

| Method | Endpoint | Returns |
|--------|----------|---------|
| GET | `/scenarios` | List of available return periods |
| GET | `/exposure/{scenario}` | GeoJSON of flooded buildings with risk scores |
| GET | `/roads/{scenario}` | GeoJSON of roads with passability status |
| GET | `/risk` | CRI raster (GeoTIFF) |
| GET | `/alert` | Current alert level from live rainfall forecast |
| GET | `/citizen` | All community observations as GeoJSON |
| POST | `/citizen` | Submit a new community observation |
| GET | `/action_cards` | Ranked action recommendations |
| GET | `/docs` | Auto-generated API documentation |

The `/alert` endpoint calls Open-Meteo (no API key required) and maps the forecast rainfall to one of four alert levels using thresholds derived from the HEC-HMS runs.

#### Step B7 — Citizen fusion (Day 3)

Merges community observations with the model output to produce a fused risk map:

```
Fused risk = 0.7 × model CRI + 0.3 × citizen signal
```

Where citizen signal = count of observations × mean severity, normalised 0–1. Cells where community reports significantly exceed model predictions are flagged for planners.

```bash
python data_science/api/citizen_fusion.py
```

---

### Stage 3 — Frontend (Person C)

**Goal:** An interactive web app that makes all the model outputs accessible to a non-technical planner.

#### Step C1 — Setup

```bash
cd frontend/flood-app
cp .env.example .env
# Edit .env: VITE_MAPBOX_TOKEN=pk.eyJ1...  (get free token at mapbox.com)
# Edit .env: VITE_API_URL=http://localhost:8000
npm install
npm run dev
```

#### Step C2 — What the app contains

**Map (main view)**
- Basemap: Mapbox satellite-streets — shows the dramatic Anti-Atlas gorge
- Center: 31.52°N, 7.10°W, zoom 11
- Layers:
  - Catchment boundary (white dashed outline)
  - Flood hazard zones (yellow → orange → red → dark red by depth)
  - Buildings (colour by risk score)
  - Roads (green = passable, orange = emergency only, red = impassable)
  - Stream network (blue lines)
  - Critical assets (hospital cross, school icon, fire station — flashing if at risk)
  - Citizen observations (circles sized by severity)

**Scenario switcher** — four buttons: T10, T50, T100, T500. Clicking any button reloads all map layers for that scenario.

**Alert banner** — pulls live forecast from the API. Colour matches EU Flood Directive levels (green/yellow/orange/red).

**Side panel (right, 320px)**
- Current alert level + forecast rainfall
- Metric cards: buildings flooded, population exposed, roads impassable, critical assets at risk
- Bar chart comparing all four scenarios
- Top-10 at-risk assets table — clicking any row flies the map to that location

**Citizen observation form** — click anywhere on the map to open a form. Fields: event type, severity (1–3), description. Submits to the API.

**Action cards panel** — fetched from `/action_cards`. Cards sorted by priority (CRITICAL → HIGH → MEDIUM). Each card has a "locate on map" button.

**PDF export** — generates a 4-page report:
- Page 1: Key statistics and alert level
- Page 2: Map screenshot
- Page 3: Top-10 risk assets table
- Page 4: Methodology summary and data sources

#### Step C3 — Working with mock data

Until the real API is running, `api.ts` returns mock data for all calls. This lets the entire UI be built and tested independently. When Person B's server goes live:

1. Set `VITE_API_URL=http://localhost:8000` in `.env`
2. Restart the dev server
3. The mock stubs are automatically bypassed

If you hit a CORS error: make sure Person B has `CORSMiddleware` enabled in `main.py` (it is in the template — just double-check).

---

## Shared config

**`config.py`** — import this in every Python script. Never hardcode coordinates or paths.

```python
BBOX = {
    "north": 31.70,
    "south": 31.40,
    "east": -6.95,
    "west": -7.35
}

OUTLET_LAT  = 31.52    # update after delineation if needed
OUTLET_LON  = -7.10

CRS_PROJ    = "EPSG:32629"   # UTM Zone 29N — correct for Morocco
CRS_GEO     = "EPSG:4326"   # WGS84 geographic

SCENARIOS   = [10, 50, 100, 500]

DATA_RAW    = "data/raw"
DATA_PROC   = "data/processed"
DATA_OUT    = "data/outputs"

API_PORT    = 8000
```

---

## Sync points and handoffs

There are four scheduled sync moments where one person hands something to another. Outside these moments, everyone works fully independently.

### Sync 0 — Pre-work check (tonight, before sleeping)
All three confirm:
- DEM downloaded and opens in QGIS ✓
- Python environment installs without errors ✓
- React app runs on localhost:3000 ✓
- GitHub repo cloned, folder structure created ✓

### Sync 1 — Day 1, 12:00
Person A pushes:
- `data/processed/catchment_boundary.geojson`
- `data/processed/stream_network.geojson`

Person B: loads catchment boundary for spatial clipping  
Person C: loads both layers onto the map

### Sync 2 — Day 1, 14:00
Person A pushes:
- `data/outputs/hydrograph_T*.csv`
- `data/outputs/peak_discharges.json`

Person B: reads peak discharge values → calibrates alert thresholds in `early_warning.py`

### Sync 3 — Day 2, 10:00 ← main handoff
Person A pushes:
- `data/outputs/depth_T10.tif`, `depth_T50.tif`, `depth_T100.tif`, `depth_T500.tif`
- `data/outputs/velocity_T10.tif`, etc.

Person B: runs real exposure pipeline (replaces mock). Produces real GeoJSONs within ~2 hours.  
Person C: begins connecting to real API endpoints as they come online.

### Sync 4 — Day 2, 16:00 ← integration milestone
Person B's API is fully live on `:8000`  
Person C: swaps all mock stubs for real endpoints, runs integration test  
All three: walkthrough the full demo together, identify any broken connections

---

## GitHub issues checklist

Use this as your task board. Assign each issue at the start.

**Person A — Hydrology**
- [ ] #1 Download DEM (COP-DEM GLO-30) for Ounila bbox
- [ ] #2 Download ESA WorldCover 2021 clipped to bbox
- [ ] #3 Download SoilGrids HSG raster for bbox
- [ ] #4 Download GHCN-Daily rainfall (Ouarzazate station MA000060681)
- [ ] #5 Catchment delineation in QGIS via WhiteboxTools
- [ ] #6 Compute morphometric parameters (A, L, S, Tc)
- [ ] #7 Compute SCS Curve Number raster + weighted average
- [ ] #8 Fit GEV to rainfall → T10/T50/T100/T500 depths
- [ ] #9 `run_hms.py` — SCS-CN rainfall-runoff → 4× hydrograph CSVs
- [ ] #31 HEC-RAS 2D setup + 4× scenario runs
- [ ] #32 Export depth_T*.tif + velocity_T*.tif
- [ ] #33 Validation: F score vs Sentinel-1

**Person B — Data science**
- [ ] #10 Python conda environment + requirements.txt
- [ ] #11 Download OSM buildings, roads, amenities
- [ ] #12 Download WorldPop Morocco 2020
- [ ] #13 `exposure_analysis.py` skeleton on mock rasters
- [ ] #14 `exposure_analysis.py` on real depth rasters *(depends on #32)*
- [ ] #15 `risk_index.py` — composite CRI
- [ ] #16 `network_analysis.py` — road passability + isolation
- [ ] #17 `early_warning.py` — rainfall → alert level
- [ ] #18 `main.py` — FastAPI with all 9 endpoints
- [ ] #19 `citizen.py` — SQLite observation store
- [ ] #34 `citizen_fusion.py` — fuse model + citizen signals
- [ ] #35 `action_generator.py` — rule-based action cards

**Person C — Frontend**
- [ ] #20 React/Vite scaffold + Mapbox setup
- [ ] #21 `api.ts` — typed service module with mock stubs
- [ ] #22 Scenario switcher + hazard zone layer (mock)
- [ ] #23 Building markers + popups + road layer (mock)
- [ ] #24 Critical assets icons layer
- [ ] #25 Side panel — metric cards + Recharts bar chart
- [ ] #26 Citizen observation form + map-click handler
- [ ] #27 Citizen layer on map + discrepancy toggle
- [ ] #28 Swap mock stubs for real API *(depends on #18)*
- [ ] #29 Action cards panel + filter UI
- [ ] #30 jsPDF export — 4-page report
- [ ] #36 Methodology panel

---

## Outputs and what they mean

| File | Type | Created by | What it means |
|------|------|------------|---------------|
| `catchment_boundary.geojson` | GeoJSON polygon | A | The area of land that drains to the Ounila outlet |
| `stream_network.geojson` | GeoJSON lines | A | Rivers and streams within the catchment |
| `hydrograph_T100.csv` | CSV | A | Discharge over time for a 1-in-100-year storm |
| `peak_discharges.json` | JSON | A | Peak flow (m³/s) for each return period |
| `depth_T100.tif` | GeoTIFF raster | A | Flood water depth in metres, 100-year scenario |
| `velocity_T100.tif` | GeoTIFF raster | A | Water velocity in m/s, 100-year scenario |
| `exposure_T100.geojson` | GeoJSON points | B | Buildings in flood zone with risk scores |
| `road_passability_T100.geojson` | GeoJSON lines | B | Roads coloured by passability |
| `cri_T100.tif` | GeoTIFF raster | B | Composite risk index (0–1), T100 scenario |
| `evacuation_summary.json` | JSON | B | Number of isolated communities per scenario |
| `action_cards.json` | JSON | B | Ranked planner actions with asset locations |
| `rainfall_depths.json` | JSON | A | 24h rainfall (mm) per return period |
| `cn_value.json` | JSON | A | SCS Curve Number for the catchment |

---

## Scientific methods

**Rainfall-runoff:** SCS Curve Number method (USDA National Engineering Handbook, Part 630, Ch. 9). Implemented directly in Python — equivalent to HEC-HMS GUI but reproducible and version-controlled.

**Design storm frequency:** Generalised Extreme Value (GEV) distribution fitted to annual maximum daily rainfall using maximum likelihood estimation (scipy.stats.genextreme).

**Flood routing:** HEC-RAS 2D unsteady flow solver, solving the 2D shallow water equations on an unstructured mesh (Brunner 2016). Fallback: HAND-based inundation approximation.

**Hazard rating:** HR Wallingford formula — `HR = d × (v + 0.5) + DF` where d = depth, v = velocity, DF = debris factor 0.5 for rocky catchment (Defra/EA FD2321).

**Composite risk:** `CRI = 0.5×H + 0.3×E + 0.2×V` following Papathoma-Köhle et al. (2019), International Journal of Disaster Risk Reduction.

**Road passability thresholds:** FHWA Hydraulic Engineering Circular HIF-12-024 (Federal Highway Administration).

**Validation metric:** F score (Bates & De Roo 2000, Journal of Hydrology 236:54–77) — F = A / (A + B + C) where A = correctly predicted flood area.

**Citizen signal fusion:** Weighted average following Poser & Dransch (2010), Natural Hazards and Earth System Sciences — 70% model, 30% community observations.

**Alert levels:** EU Floods Directive 2007/60/EC four-colour framework (green/yellow/orange/red).

---

## Limitations and caveats

This is a **hackathon prototype**. It should not be used for operational flood management decisions without independent validation and professional engineering review.

**Known limitations:**

- **SRTM/COP-DEM 30m resolution** smooths out narrow gorges — the Ounila valley may be underresolved in places. A 1m drone survey would significantly improve HEC-RAS accuracy.
- **SCS-CN method** is designed for temperate climates. In arid Morocco, infiltration behaviour during extreme events is less certain — the CN may need calibration against observed events.
- **OSM sparsity** in rural Ounila means building exposure counts are likely underestimates. Many structures are untagged.
- **No gauge data** — without a local stream gauge, we cannot calibrate the rainfall-runoff model. The GEV fit to Ouarzazate station data assumes stationarity.
- **HEC-RAS boundary conditions** assume normal flow at the downstream boundary — this is an approximation.
- The **500-year return period** is an extreme extrapolation from typically short rainfall records and should be treated with particular caution.
- **Validation** depends on the availability of Copernicus EMS or Sentinel-1 imagery for a documented flood event at this location.

Despite these limitations, the system provides a scientifically grounded first-order flood risk assessment that significantly exceeds what currently exists for this catchment.

---

*Built at [Hackathon Name], [Date]. Team: Person A, Person B, Person C.*
