import os
import requests
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from shapely.geometry import Polygon

# --- CONFIG ---
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

# Morocco 2020 UN-adjusted population count (100m resolution)
WORLDPOP_URL = "https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/MAR/mar_ppp_2020.tif"
RAW_FILE = os.path.join(RAW_DIR, "worldpop_morocco_raw.tif")
CLIPPED_FILE = os.path.join(RAW_DIR, "worldpop_ounila.tif")

# --- 1. DOWNLOAD ---
def download_worldpop():
    if os.path.exists(RAW_FILE):
        print("Raw WorldPop file already exists. Skipping download.")
        return
    
    print(f"Downloading WorldPop data (this may take a minute)...")
    response = requests.get(WORLDPOP_URL, stream=True)
    if response.status_code == 200:
        with open(RAW_FILE, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download complete.")
    else:
        print(f"Failed to download. Status code: {response.status_code}")

# --- 2. CLIP ---
def clip_population():
    # Define same study area as OSM script
    coords = [
        [-7.152786, 31.281004], [-7.173386, 31.285698], [-7.185402, 31.28159], 
        [-7.188835, 31.293033], [-7.171326, 31.29626], [-7.181625, 31.307407], 
        [-7.172356, 31.31386], [-7.179909, 31.337616], [-7.175789, 31.351397], 
        [-7.179222, 31.361658], [-7.165833, 31.368694], [-7.159996, 31.366935], 
        [-7.14592, 31.370746], [-7.135277, 31.367228], [-7.118111, 31.37397], 
        [-7.102661, 31.378074], [-7.061119, 31.370453], [-7.053223, 31.361951], 
        [-7.039146, 31.363417], [-7.025414, 31.338202], [-7.002754, 31.336736], 
        [-6.969452, 31.340255], [-6.971855, 31.328232], [-6.979065, 31.325006], 
        [-6.990395, 31.313274], [-7.023354, 31.279537], [-7.03743, 31.278656], 
        [-7.049446, 31.284525], [-7.059746, 31.277483], [-7.074509, 31.280417], 
        [-7.082062, 31.268093], [-7.106094, 31.274842], [-7.108841, 31.28071], 
        [-7.124977, 31.283644], [-7.14077, 31.280417], [-7.152786, 31.281004]
    ]
    poly = Polygon(coords)
    gdf = gpd.GeoDataFrame(index=[0], geometry=[poly], crs="EPSG:4326")
    
    # 25km buffer logic (match Issue 11)
    gdf_utm = gdf.to_crs(epsg=32629)
    buffer_geom = gdf_utm.geometry.buffer(25000).to_crs(4326).iloc[0]

    print("Clipping population raster...")
    with rasterio.open(RAW_FILE) as src:
        out_image, out_transform = mask(src, [buffer_geom], crop=True)
        out_meta = src.meta.copy()

    out_meta.update({
        "driver": "GTiff",
        "height": out_image.shape[1],
        "width": out_image.shape[2],
        "transform": out_transform,
        "nodata": 0
    })

    with rasterio.open(CLIPPED_FILE, "w", **out_meta) as dest:
        dest.write(out_image)
    print(f"Success! Clipped raster saved to {CLIPPED_FILE}")

if __name__ == "__main__":
    download_worldpop()
    clip_population()