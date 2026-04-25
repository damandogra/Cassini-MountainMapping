"""
ISSUE 12 - AUTOMATIC PIPELINE
Ounila Flood System (Person B)

Runs full data acquisition pipeline:
- builds buffer study area
- downloads OSM layers
- exports clean GeoJSON outputs

Run:
    python run_pipeline.py
"""

import os
import geopandas as gpd
from shapely.geometry import Polygon
import osmnx as ox

# ----------------------------
# CONFIG
# ----------------------------

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
OUT_DIR = os.path.join(BASE_DIR, "data", "raw")

os.makedirs(OUT_DIR, exist_ok=True)

# 25 km buffer (expanded coverage)
BUFFER_M = 25000

# ----------------------------
# INPUT POLYGON (Ounila catchment)
# ----------------------------

coords = [
    [-7.152786, 31.281004], [-7.173386, 31.285698],
    [-7.185402, 31.28159], [-7.188835, 31.293033],
    [-7.171326, 31.29626], [-7.181625, 31.307407],
    [-7.172356, 31.31386], [-7.179909, 31.337616],
    [-7.175789, 31.351397], [-7.179222, 31.361658],
    [-7.165833, 31.368694], [-7.159996, 31.366935],
    [-7.14592, 31.370746], [-7.135277, 31.367228],
    [-7.118111, 31.37397], [-7.102661, 31.378074],
    [-7.061119, 31.370453], [-7.053223, 31.361951],
    [-7.039146, 31.363417], [-7.025414, 31.338202],
    [-7.002754, 31.336736], [-6.969452, 31.340255],
    [-6.971855, 31.328232], [-6.979065, 31.325006],
    [-6.990395, 31.313274], [-7.023354, 31.279537],
    [-7.03743, 31.278656], [-7.049446, 31.284525],
    [-7.059746, 31.277483], [-7.074509, 31.280417],
    [-7.082062, 31.268093], [-7.106094, 31.274842],
    [-7.108841, 31.28071], [-7.124977, 31.283644],
    [-7.14077, 31.280417], [-7.152786, 31.281004]
]

# ----------------------------
# STEP 1 — BUILD STUDY AREA
# ----------------------------

poly = Polygon(coords)

gdf = gpd.GeoDataFrame(index=[0], geometry=[poly], crs="EPSG:4326")

# project to meters (UTM 29N)
gdf_proj = gdf.to_crs(epsg=32629)

# expand buffer (15–25 km flood influence zone)
buffered = gdf_proj.buffer(BUFFER_M)

study_area = gpd.GeoSeries(buffered, crs=32629).to_crs(4326).iloc[0]

print("Study area created with", BUFFER_M / 1000, "km buffer")

# ----------------------------
# STEP 2 — OSM DOWNLOAD
# ----------------------------

def save_layer(gdf, name):
    """Safe writer with overwrite support"""
    path = os.path.join(OUT_DIR, name)
    if len(gdf) == 0:
        print(f"⚠️ Empty layer: {name}")
        return
    gdf = gdf.reset_index(drop=True)
    gdf.to_file(path, driver="GeoJSON")
    print("Saved:", path)

# ----------------------------
# BUILDINGS
# ----------------------------

print("\nDownloading buildings...")

buildings = ox.features_from_polygon(
    study_area,
    tags={"building": True}
)

save_layer(buildings, "osm_buildings.geojson")

# ----------------------------
# ROADS
# ----------------------------

print("\nDownloading roads...")

G = ox.graph_from_polygon(
    study_area,
    network_type="drive",
    simplify=True
)

edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
edges = edges[["highway", "length", "geometry"]]

save_layer(edges, "osm_roads.geojson")

# ----------------------------
# POIs (critical infrastructure)
# ----------------------------

print("\nDownloading POIs...")

pois = ox.features_from_polygon(
    study_area,
    tags={
        "amenity": ["hospital", "school", "clinic", "fire_station"]
    }
)

save_layer(pois, "osm_pois.geojson")

# ----------------------------
# SUMMARY
# ----------------------------

print("\nPIPELINE COMPLETE ✔")
print("Study buffer (km):", BUFFER_M / 1000)
print("Outputs saved to:")
print(" -", os.path.join(OUT_DIR, "osm_buildings.geojson"))
print(" -", os.path.join(OUT_DIR, "osm_roads.geojson"))
print(" -", os.path.join(OUT_DIR, "osm_pois.geojson"))