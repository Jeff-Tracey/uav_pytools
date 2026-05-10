#!/usr/bin/env python3
"""
mrk_to_geodata.py

Convert a DJI Mavic 3M Timestamp.MRK file to KML, GeoJSON, or Shapefile.

Usage:
    python mrk_to_geodata.py <input.MRK> <output_path> [--format kml|geojson|shapefile]

Default output format: KML
"""

import argparse
import json
import re
import sys
from pathlib import Path


# --- Validation ---

MRK_LINE_PATTERN = re.compile(
    r'^\s*\d+\s+'           # line index
    r'[\d.]+\s+'            # GPS time (seconds of week)
    r'\[\d+\]\s+'           # GPS week [NNNN]
    r'[+-]?\d+,N\s+'        # N velocity
    r'[+-]?\d+,E\s+'        # E velocity
    r'[+-]?\d+,V\s+'        # V velocity
    r'[\d.]+,Lat\s+'        # latitude
    r'[+-]?[\d.]+,Lon\s+'   # longitude
    r'[\d.]+,Ellh'          # ellipsoidal height
)


def validate_mrk(path: Path) -> bool:
    """Return True if file looks like a Mavic 3M .MRK file."""
    if path.suffix.upper() != '.MRK':
        return False
    try:
        with open(path) as f:
            lines = [l for l in f if l.strip()]
        if len(lines) < 2:
            return False
        # Check first two data lines match expected format
        return all(MRK_LINE_PATTERN.match(l) for l in lines[:2])
    except Exception:
        return False


# --- Parsing ---

def parse_mrk(path: Path) -> list[dict]:
    """Parse MRK file, return list of image point dicts."""
    points = []
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            parts = line.split()
            # Extract fields by label suffix
            def get(label):
                for p in parts:
                    if p.endswith(',' + label):
                        return float(p.split(',')[0])
                return None

            image_index = int(parts[0])
            gps_time = float(parts[1])
            gps_week = int(parts[2].strip('[]'))
            lat = get('Lat')
            lon = get('Lon')
            ellh = get('Ellh')

            # Accuracy: three floats before the quality flag
            # Format: "stdN, stdE, stdV"  then "Q,Q"
            acc_match = re.search(r'([\d.]+),\s*([\d.]+),\s*([\d.]+)\s+\d+,Q', line)
            std_n = std_e = std_v = None
            if acc_match:
                std_n, std_e, std_v = (float(x) for x in acc_match.groups())

            quality_match = re.search(r'(\d+),Q', line)
            quality = int(quality_match.group(1)) if quality_match else None

            points.append({
                'index': image_index,
                'gps_time': gps_time,
                'gps_week': gps_week,
                'lat': lat,
                'lon': lon,
                'ellh_m': ellh,
                'std_n_m': std_n,
                'std_e_m': std_e,
                'std_v_m': std_v,
                'quality': quality,
            })
    return points


# --- Writers ---

def write_kml(points: list[dict], output: Path, name: str) -> None:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        f'  <Document><name>{name}</name>',
    ]
    for p in points:
        desc = (
            f"GPS Week: {p['gps_week']} | Time: {p['gps_time']:.3f}s | "
            f"Ellh: {p['ellh_m']}m | Quality: {p['quality']}"
        )
        lines += [
            '  <Placemark>',
            f"    <name>Image {p['index']:03d}</name>",
            f'    <description>{desc}</description>',
            '    <Point>',
            f"      <coordinates>{p['lon']},{p['lat']},{p['ellh_m']}</coordinates>",
            '    </Point>',
            '  </Placemark>',
        ]
    lines += ['  </Document>', '</kml>']
    output.write_text('\n'.join(lines), encoding='utf-8')


def write_geojson(points: list[dict], output: Path) -> None:
    features = []
    for p in points:
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [p['lon'], p['lat'], p['ellh_m']],
            },
            'properties': {k: v for k, v in p.items() if k not in ('lat', 'lon', 'ellh_m')},
        })
    fc = {'type': 'FeatureCollection', 'features': features}
    output.write_text(json.dumps(fc, indent=2), encoding='utf-8')


def write_shapefile(points: list[dict], output: Path) -> None:
    try:
        import shapefile
    except ImportError:
        sys.exit('pyshp is required for shapefile output: pip install pyshp')

    with shapefile.Writer(str(output), shapeType=shapefile.POINTZ) as w:
        w.field('index',   'N', 4)
        w.field('gps_time','F', 14, 6)
        w.field('gps_week','N', 6)
        w.field('ellh_m',  'F', 10, 3)
        w.field('std_n_m', 'F', 8, 4)
        w.field('std_e_m', 'F', 8, 4)
        w.field('std_v_m', 'F', 8, 4)
        w.field('quality', 'N', 4)
        for p in points:
            w.pointz(p['lon'], p['lat'], p['ellh_m'])
            w.record(
                p['index'], p['gps_time'], p['gps_week'], p['ellh_m'],
                p['std_n_m'], p['std_e_m'], p['std_v_m'], p['quality'],
            )

    # Write .prj (WGS84)
    prj = output.with_suffix('.prj')
    prj.write_text(
        'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",'
        'SPHEROID["WGS_1984",6378137.0,298.257223563]],'
        'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
    )


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description='Convert Mavic 3M .MRK to geodata.')
    parser.add_argument('input',  type=Path, help='Path to Timestamp.MRK file')
    parser.add_argument('output', type=Path, help='Output file path (without extension for shapefile)')
    parser.add_argument('--format', choices=['kml', 'geojson', 'shapefile'],
                        default='kml', help='Output format (default: kml)')
    args = parser.parse_args()

    if not args.input.exists():
        sys.exit(f'Error: input file not found: {args.input}')

    if not validate_mrk(args.input):
        sys.exit(
            f'Error: {args.input} does not appear to be a valid Mavic 3M Timestamp.MRK file.\n'
            'Expected .MRK extension and DJI PPK timestamp format.'
        )

    points = parse_mrk(args.input)
    print(f'Parsed {len(points)} image positions from {args.input.name}')

    fmt = args.format
    output = args.output

    if fmt == 'kml':
        if output.suffix.lower() != '.kml':
            output = output.with_suffix('.kml')
        write_kml(points, output, args.input.stem)
    elif fmt == 'geojson':
        if output.suffix.lower() != '.geojson':
            output = output.with_suffix('.geojson')
        write_geojson(points, output)
    elif fmt == 'shapefile':
        output = output.with_suffix('')  # shapefile writer adds .shp etc.
        write_shapefile(points, output)

    print(f'Wrote {fmt} to {output}')


if __name__ == '__main__':
    main()
