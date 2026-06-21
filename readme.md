# 🌊 Atlas — Flash Flood Decision Support System
### Tighza / Ounila Valley, Morocco · Cassini Hackathon

<img width="834" height="522" alt="image" src="https://github.com/user-attachments/assets/936222e1-dd6c-4680-a00e-98d453e86905" />


A full-stack flood risk platform that answers one question for emergency planners:

> **"If it rains hard tonight, which roads close, which villages get cut off, and what should we do first?"**

---

## How it works

```
Terrain (DEM) + Rainfall data
         ↓
   [hydrology/]  — SCS-CN rainfall-runoff model
   Produces flood depth maps for T10 / T50 / T100 / T500 scenarios
         ↓
   [Exposure_Person_B/]  — Risk engine (FastAPI)
   Overlays depths with buildings, roads, population → risk scores + action cards
         ↓
   [frontend/flood-app/]  — React dashboard
   Interactive map: hazard zones, road passability, live alerts, PDF export
```

---

## Folder Structure

```
Cassini-MountainMapping/
│
├── hydrology/                        # Hydrological modelling pipeline
│   ├── hms_python/
│   │   ├── rainfall_frequency.py     # GEV fit → T10/50/100/500 rainfall depths
│   │   └── run_hms.py                # SCS-CN → flood hydrographs
│   └── ras/
│       └── hand_approximation.py     # HAND fallback if HEC-RAS unavailable
│
├── Exposure_Person_B/                # Risk engine + REST API
│   ├── exposure_analysis.py          # Depth rasters → building hazard ratings
│   ├── risk_index.py                 # Composite Risk Index (CRI) raster
│   ├── network_analysis.py           # Road passability + community isolation
│   ├── early_warning.py              # Live rainfall → alert level
│   ├── action_generator.py           # Rule-based planner action cards
│   ├── citizen.py                    # Community observation store (SQLite)
│   ├── citizen_fusion.py             # Merge model + citizen signals
│   └── main.py                       # FastAPI server (all endpoints)
│
├── frontend/flood-app/               # React/Vite web dashboard
│   └── src/
│       ├── App.tsx                   # Main map interface (Mapbox GL JS)
│       ├── api.ts                    # Typed API client + mock stubs
│       └── components/
│           ├── ScenarioBar.tsx       # T10/T50/T100/T500 switcher
│           ├── SidePanel.tsx         # Metrics dashboard + charts
│           ├── CitizenForm.tsx        # Field observation submission
│           ├── ActionCards.tsx       # Ranked planner actions
│           └── PDFExport.tsx         # 4-page report generator
│
├── requirements.txt                  # Python dependencies (pin to Anaconda env)
├── RUN.MD                            # Quick-start reference
└── README.md                         # This file
```

> **Note:** `data/` is gitignored. Raw and processed rasters/GeoJSONs live locally only.

---

## Prerequisites

| Tool | Version | Used for |
|---|---|---|
| Python | 3.11+ | All backend scripts |
| conda / venv | any | Environment management |
| Node.js | 18+ | Frontend |
| npm or pnpm | any | Frontend package management |
| QGIS | 3.x + WhiteboxTools plugin | Catchment delineation (manual step) |
| HEC-RAS | 6.5 (optional) | 2D flood routing (Python fallback available) |

---

## Quickstart

### 1 — Clone and set up Python

```bash
git clone https://github.com/damandogra/Cassini-MountainMapping.git
cd Cassini-MountainMapping

conda create -n flood python=3.11
conda activate flood
pip install -r requirements.txt
```

### 2 — Run the hydrology pipeline

```bash
# After catchment delineation in QGIS (produces catchment_boundary.geojson):
python hydrology/hms_python/rainfall_frequency.py   # → data/processed/rainfall_depths.json
python hydrology/hms_python/run_hms.py              # → data/outputs/hydrograph_T*.csv
# Then run HEC-RAS (or the HAND fallback):
python hydrology/ras/hand_approximation.py          # → data/outputs/depth_T*.tif
```

### 3 — Run the risk engine

```bash
python Exposure_Person_B/exposure_analysis.py       # → exposure_T*.geojson
python Exposure_Person_B/risk_index.py              # → cri_T100.tif
python Exposure_Person_B/network_analysis.py        # → road_passability_T*.geojson
python Exposure_Person_B/action_generator.py        # → action_cards.json
```

### 4 — Start the API

```bash
cd Exposure_Person_B
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# Docs available at http://localhost:8000/docs
```

### 5 — Start the frontend

```bash
cd frontend/flood-app
cp .env.example .env
# Edit .env:
#   VITE_MAPBOX_TOKEN=pk.eyJ1...   (free at mapbox.com)
#   VITE_API_URL=http://localhost:8000

npm install       # or: pnpm install
npm run dev       # → http://localhost:5173
```

> The frontend works **without the backend** — `api.ts` returns mock data until `VITE_API_URL` is set and the server is running.

---

## API Endpoints

| Method | Endpoint | Returns |
|---|---|---|
| GET | `/scenarios` | Available return periods |
| GET | `/exposure/{scenario}` | GeoJSON — buildings with risk scores |
| GET | `/roads/{scenario}` | GeoJSON — roads with passability status |
| GET | `/risk` | CRI raster (GeoTIFF) |
| GET | `/alert` | Live alert level from Open-Meteo forecast |
| GET | `/citizen` | Community observations (GeoJSON) |
| POST | `/citizen` | Submit a new observation |
| GET | `/action_cards` | Ranked planner action recommendations |
| GET | `/docs` | Auto-generated Swagger UI |

---

## Data Sources (all free)

| Dataset | Purpose | Where |
|---|---|---|
| Copernicus DEM GLO-30 (30m) | Terrain / flood routing | [dataspace.copernicus.eu](https://browser.dataspace.copernicus.eu) |
| ESA WorldCover 2021 (10m) | Land use → Curve Number | [esa-worldcover.org](https://esa-worldcover.org/en/download) |
| SoilGrids 250m | Soil texture → HSG | [soilgrids.org](https://soilgrids.org) |
| GHCN-Daily (NOAA) | Historical rainfall (Ouarzazate) | Station `MA000060681` |
| OpenStreetMap via osmnx | Buildings, roads, amenities | Auto-downloaded |
| WorldPop Morocco 2020 | Population exposure | [hub.worldpop.org](https://hub.worldpop.org) |
| Open-Meteo API | Live rainfall forecast | No key required, auto-called |
| Mapbox | Basemap | Free tier (50k loads/month) |

---

## Environment Variables

| Variable | Where | Description |
|---|---|---|
| `VITE_MAPBOX_TOKEN` | `frontend/flood-app/.env` | Mapbox public token |
| `VITE_API_URL` | `frontend/flood-app/.env` | Backend URL (default: `http://localhost:8000`) |

---

## Key Technical Choices

- **Rainfall-runoff:** SCS Curve Number method (USDA NEH Part 630) — implemented in pure Python, no GUI needed.
- **Flood routing:** HEC-RAS 2D unsteady solver; HAND approximation available as a fallback.
- **Hazard rating:** HR Wallingford formula — `HR = depth × (velocity + 0.5) + 0.5`
- **Composite risk:** `CRI = 0.5 × Hazard + 0.3 × Exposure + 0.2 × Vulnerability`
- **Road thresholds:** < 0.3m passable · 0.3–0.6m emergency only · > 0.6m impassable
- **Citizen fusion:** 70% model CRI + 30% normalised community signal
- **Alert levels:** EU Floods Directive 4-colour framework (green / yellow / orange / red)

---

## Limitations

This is a hackathon prototype — **not for operational use without independent engineering review.**

- DEM at 30m resolution smooths narrow gorges; a drone survey would improve accuracy.
- SCS-CN is calibrated for temperate climates; arid Morocco behaviour under extreme events is less certain.
- OSM coverage in rural Ounila is sparse — building counts are likely underestimates.
- No local stream gauge data — rainfall-runoff model is uncalibrated.
- The 500-year return period is a significant statistical extrapolation.

---

*Built at the Cassini Hackathon. Study area: Ounila River, Anti-Atlas / High Atlas, Morocco (bbox: 31.40–31.70°N, 7.35–6.95°W).*
