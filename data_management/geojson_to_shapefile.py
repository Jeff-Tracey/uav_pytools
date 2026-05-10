# Take a GeoJSON file for camera locations and save as point and line shapefiles

import os
import geojson
import geopandas as gpd
from shapely.geometry import Point, LineString
import re

# -----------------------------------------------------------------------------
# functions
# -----------------------------------------------------------------------------

def extract_sequential_integer(filename):
    match = re.search(r'_(\d{4})_D\.JPG$', filename)
    if match:
        return int(match.group(1))
    return None

def geojson_to_shapefile(geojson_file, output_dir, epsg_id, debug=False):
    # Load GeoJSON file using geojson package
    with open(geojson_file, 'r') as f:
        data = geojson.load(f)
    
    if debug:
        print(data)
    
    # Convert GeoJSON data to GeoDataFrame
    gdf = gpd.GeoDataFrame.from_features(data['features'])
    
    # Set the initial CRS to WGS84 (EPSG:4326)
    gdf.set_crs(epsg=4326, inplace=True)
    
    # Rename columns to fit within the 10 character limit of Shapefiles
    gdf = gdf.rename(columns={
        'capture_time': 'capt_time',
        'rotation': 'rot'
    })
    
    # Extract sequential integer from filename and add as a new field
    gdf['seq_int'] = gdf['filename'].apply(extract_sequential_integer)
    
    # Sort GeoDataFrame by the new field
    gdf = gdf.sort_values(by='seq_int')
    
    # Project the GeoDataFrame to the specified EPSG ID
    gdf = gdf.to_crs(epsg=epsg_id)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract points from GeoDataFrame
    points_gdf = gdf[gdf.geometry.type == 'Point']
    
    # Write points to point shapefile
    points_shapefile_path = os.path.join(output_dir, 'camera_pts.shp')
    points_gdf.to_file(points_shapefile_path, driver='ESRI Shapefile')
    
    # Create a line using the points as vertices
    points = [point for point in points_gdf.geometry]
    if not points:
        print("No points found in the GeoDataFrame.")
        return
    
    line = LineString(points)
    
    # Create a GeoDataFrame for the line
    line_gdf = gpd.GeoDataFrame({'id': [0]}, geometry=[line], crs=gdf.crs)
    
    # Write the line to line shapefile
    line_shapefile_path = os.path.join(output_dir, 'camera_path.shp')
    line_gdf.to_file(line_shapefile_path, driver='ESRI Shapefile')

# -----------------------------------------------------------------------------
# main
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    geojson_file = '/Users/jeff/Projects/Drones/Data/mavic3m1-area_test-21mar2025/assets/Princess-View-Place-3-21-2025-shots.geojson'
    output_dir = '/Users/jeff/Projects/Drones/Data/mavic3m1-area_test-21mar2025/processing/shapefiles'
    epsg_id = 32611  # Example EPSG ID for WGS 84 / UTM zone 11N
    geojson_to_shapefile(geojson_file, output_dir, epsg_id, debug=True)