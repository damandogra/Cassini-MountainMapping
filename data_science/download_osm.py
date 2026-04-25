"""
OSM Downloader — Issue #11 (ENHANCED VERSION)
Ounila Flood Decision System (Person B)

Upgrades:
- 25 km buffer (larger catchment influence zone)
- Buildings + roads + POIs + settlements
- Clean output structure
"""

import osmnx as ox
import geopandas as gpd
from shapely.geometry import Polygon
import os

# -------------------------------------------------------
# 0. PATH SETUP
# -------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
OUT_DIR = os.path.join(BASE_DIR, "data", "raw")
os.makedirs(OUT_DIR, exist_ok=True)

print("Output folder:", OUT_DIR)

# -------------------------------------------------------
# 1. CATCHMENT POLYGON (Ounila)
# -------------------------------------------------------
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

poly = Polygon(coords)

gdf = gpd.GeoDataFrame(index=[0], geometry=[poly], crs="EPSG:4326")

# -------------------------------------------------------
# 2. BUFFER (EXPANDED → 25 km)
# -------------------------------------------------------
gdf_utm = gdf.to_crs(epsg=32629)

buffer_geom = gdf_utm.geometry.buffer(25000).iloc[0]  # ⬅️ increased from 15km

study_area = gpd.GeoSeries([buffer_geom], crs=32629).to_crs(4326).iloc[0]

print("Study area created (25 km buffer)")

# -------------------------------------------------------
# 3. BUILDINGS
# -------------------------------------------------------
print("Downloading buildings...")

buildings = ox.features_from_polygon(
    study_area,
    tags={"building": True}
).reset_index()

buildings["building"] = buildings["building"].fillna("yes")

buildings.to_file(
    os.path.join(OUT_DIR, "osm_buildings.geojson"),
    driver="GeoJSON"
)

# -------------------------------------------------------
# 4. ROAD NETWORK
# -------------------------------------------------------
print("Downloading road network...")

G = ox.graph_from_polygon(
    study_area,
    network_type="drive",
    simplify=True
)

ox.save_graphml(G, os.path.join(OUT_DIR, "osm_roads.graphml"))

edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
edges = edges[["highway", "length", "geometry"]]

edges.to_file(
    os.path.join(OUT_DIR, "osm_roads.geojson"),
    driver="GeoJSON"
)

# -------------------------------------------------------
# 5. POIs (ENHANCED)
# -------------------------------------------------------
print("Downloading POIs...")

pois = ox.features_from_polygon(
    study_area,
    tags={
        "amenity": [
            "hospital", "school", "clinic",
            "fire_station", "police", "townhall", "doctors"
        ],
        "healthcare": True
    }
).reset_index()

pois.to_file(
    os.path.join(OUT_DIR, "osm_pois.geojson"),
    driver="GeoJSON"
)

# -------------------------------------------------------
# 6. SETTLEMENTS (CRITICAL ADDITION)
# -------------------------------------------------------
print("Downloading settlements...")

places = ox.features_from_polygon(
    study_area,
    tags={"place": ["village", "hamlet", "town"]}
).reset_index()

places.to_file(
    os.path.join(OUT_DIR, "osm_places.geojson"),
    driver="GeoJSON"
)

# -------------------------------------------------------
# 7. SUMMARY
# -------------------------------------------------------
print("\nDONE ✔")
print("Buildings:", len(buildings))
print("Road edges:", len(edges))
print("POIs:", len(pois))
print("Settlements:", len(places))