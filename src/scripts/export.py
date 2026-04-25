import rasterio
from rasterio.transform import from_bounds
import numpy as np

def exportar_geotiff(matrix, filename, bbox_coords, crs="EPSG:4326"):
    """
    Exporta una matriz NumPy a un archivo GeoTIFF con georreferenciación.
    bbox_coords debe ser [min_lon, min_lat, max_lon, max_lat]
    """
    # Evitamos NaNs (los convertimos a 0 para que los programas GIS no den error)
    matrix_safe = np.nan_to_num(matrix)
    
    height, width = matrix_safe.shape
    
    # Creamos el 'Transform' (El mapa que le dice al archivo cuánto mide cada píxel)
    min_lon, min_lat, max_lon, max_lat = bbox_coords
    transform = from_bounds(min_lon, min_lat, max_lon, max_lat, width, height)
    
    # Escribimos el archivo
    with rasterio.open(
        filename,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,                  # 1 banda (escala de grises/valores)
        dtype=matrix_safe.dtype,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(matrix_safe, 1)
        
    print(f"💾 GeoTIFF guardado con éxito: {filename}")