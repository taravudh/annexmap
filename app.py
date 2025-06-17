from flask import Flask, render_template, jsonify, request, send_file
import geopandas as gpd
import os
from shapely.geometry import shape, box
import qrcode
from io import BytesIO

app = Flask(__name__)
DATA_DIR = 'data'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data/<layer_name>')
def serve_geojson(layer_name):
    layer_map = {
        'grid4k': 'grid4k_4326_merge.gpkg',
        'grid50k': 'grid50k_4326.gpkg',
        'nrf': 'nrf_singlepart.gpkg'
    }
    filename = layer_map.get(layer_name)
    if not filename:
        return jsonify({"error": "Invalid layer name"}), 404

    filepath = os.path.join(DATA_DIR, filename)
    gdf = gpd.read_file(filepath).to_crs(epsg=4326)
    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notnull()]

    if layer_name in ['grid4k', 'nrf']:
        try:
            minx = float(request.args.get('minx'))
            miny = float(request.args.get('miny'))
            maxx = float(request.args.get('maxx'))
            maxy = float(request.args.get('maxy'))
            bounds_geom = box(minx, miny, maxx, maxy)
            gdf = gdf[gdf.intersects(bounds_geom)]
        except:
            pass

    return jsonify(gdf.__geo_interface__)

@app.route('/intersect_nrf', methods=['POST'])
def intersect_nrf():
    data = request.get_json()
    if not data or 'geometry' not in data:
        return jsonify({"error": "No geometry provided"}), 400

    geom = shape(data['geometry'])

    grid4k = gpd.read_file(os.path.join(DATA_DIR, 'grid4k_4326_merge.gpkg')).to_crs(epsg=4326)
    grid4k = grid4k[grid4k.geometry.intersects(geom)]

    result = []
    for _, row in grid4k.iterrows():
        ms = row.get("MAPSHEET", "N/A")
        ms50k = row.get("MAPSHEET50K", "N/A")
        result.append(f"MAPSHEET: {ms} / MAPSHEET50K: {ms50k}")

    return jsonify(result)

@app.route('/qr_code', methods=['POST'])
def qr_code():
    data = request.get_json()
    mapsheet_text = "\n".join(data.get("mapsheets", [])) or "No mapsheets"
    img = qrcode.make(mapsheet_text)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")
if __name__ == '__main__':
    app.run(debug=True)
