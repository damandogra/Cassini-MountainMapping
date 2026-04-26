# 🌊 Atlas
**Tighza, Morocco**

This project is a complete and operational decision-support system  developed during a 48-hour hackathon. The system processes raw terrain and precipitation data, runs a dynamic hydrological model, and provides an interactive dashboard.

---

## 🚀 System Architecture

The project is decoupled into three main modules, each managed in its own Git branch:

### 1. Branch: `data-extraction` (Hydrology & Data Sources)

**Goal:** Convert terrain and rainfall data into flood depth maps for 4 scenarios (return periods of 10, 50, 100, and 500 years).

- **Data Acquisition:**  
  Automated download of global datasets (Copernicus DEM, ESA WorldCover, SoilGrids, GHCN-Daily).


- **Hydrological Modeling:**  
  SCS Curve Number method and GEV distribution fitting for rainfall.  
  A custom Python engine (`run_hms.py`) generates design hydrographs.

- **Flood Routing:**  
  2D simulation to generate GeoTIFFs of flood depth and velocity.

---

### 2. Branch: `pipeline-backend` (Risk Engine & API)

**Goal:** Translate physical models into actionable risk metrics and serve them via a REST API.

- **Exposure Analysis:**  
  Overlay flood depths with buildings and roads (OpenStreetMap) to compute Hazard Rating.

- **Composite Risk Index (CRI):**  
  Computes a per-cell risk score combining hazard, population exposure, and vulnerability.

- **Network Isolation:**  
  Identifies communities that lose road access due to flooding.

- **FastAPI Backend:**  
  Serves GeoJSONs and statistics.  
  Endpoints:
  - `/exposure`
  - `/roads`
  - `/risk`
  - `/action_cards`

---

### 3. Branch: `frontend` (Decision Interface)

**Goal:** Provide a visual and interactive dashboard for emergency managers.

- **Tech Stack:**  
  React, Vite, Mapbox GL JS, Lucide, Typescript.

- **3D Map:**  
  Visualizes hazard zones, building risk levels, and infrastructure accessibility.

- **Dynamic Simulation:**  
  A slider simulates rainfall in real time and shows immediate impacts on the map.

- **Crowdsourced Intelligence:**  
  A form allows users to submit field observations that update the map and risk index in real time.

---


## ⚙️ Quick Start (Local Development)

### Backend & Pipeline

Checkout into the pipeline-backend branch

```bash
# Create environment
conda create -n flood python=3.11

# Activate environment
conda activate flood

# Install dependencies
pip install -r requirements.txt

# Run pipeline
python run_pipeline.py

# Run REST API
cd api
python -m uvicorn main:app --port 8000 --reload

```

### Frontend
``` bash
# Install dependencies
pnpm/npm install

# Configure .env
VITE_MAPBOX_TOKEN=your_mapbox_token
VITE_API_URL=http://localhost:8000

# Run
pnpm/npm run dev

```

