#!/usr/bin/env python3
"""
flag_suspect_images.py

Flag potentially problematic images in a DJI Mavic 3M mission folder by checking:

  1. Trajectory outliers — images whose MRK-derived position deviates significantly
     from the local flight path (catches bad GPS/IMU placement like the rotated image)

  2. Sharpness — images with low Laplacian variance (catches motion blur, focus issues)

  3. Completeness — images missing their companion band files (e.g., has _D.JPG but
     missing one or more MS bands)

Usage:
    python flag_suspect_images.py <image_folder> <mrk_file> [options]

    --sharpness-threshold FLOAT   Laplacian variance below this = blurry (default: 100)
    --trajectory-zscore FLOAT     Z-score above this = trajectory outlier (default: 3.0)
    --quarantine                  Move flagged images to <image_folder>/quarantine/
    --report PATH                 Save report to this path (default: print to stdout)

Requirements:
    pip install opencv-python numpy
    exiftool must be installed (brew install exiftool)
"""

import argparse
import csv
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path


# --- MRK parsing (shared logic with mrk_to_geodata.py) ---

MRK_LINE_PATTERN = re.compile(
    r'^\s*\d+\s+'
    r'[\d.]+\s+'
    r'\[\d+\]\s+'
    r'[+-]?\d+,N\s+'
    r'[+-]?\d+,E\s+'
    r'[+-]?\d+,V\s+'
    r'[\d.]+,Lat\s+'
    r'[+-]?[\d.]+,Lon\s+'
    r'[\d.]+,Ellh'
)


def validate_mrk(path: Path) -> bool:
    if path.suffix.upper() != '.MRK':
        return False
    try:
        with open(path) as f:
            lines = [l for l in f if l.strip()]
        return len(lines) >= 2 and all(MRK_LINE_PATTERN.match(l) for l in lines[:2])
    except Exception:
        return False


def parse_mrk(path: Path) -> list[dict]:
    points = []
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            parts = line.split()

            def get(label):
                for p in parts:
                    if p.endswith(',' + label):
                        return float(p.split(',')[0])
                return None

            acc_match = re.search(r'([\d.]+),\s*([\d.]+),\s*([\d.]+)\s+\d+,Q', line)
            quality_match = re.search(r'(\d+),Q', line)

            points.append({
                'index':    int(parts[0]),
                'gps_time': float(parts[1]),
                'lat':      get('Lat'),
                'lon':      get('Lon'),
                'ellh_m':   get('Ellh'),
                'std_n_m':  float(acc_match.group(1)) if acc_match else None,
                'std_e_m':  float(acc_match.group(2)) if acc_match else None,
                'std_v_m':  float(acc_match.group(3)) if acc_match else None,
                'quality':  int(quality_match.group(1)) if quality_match else None,
            })
    return points


# --- Trajectory outlier detection ---

def haversine_m(lat1, lon1, lat2, lon2) -> float:
    """Distance in metres between two lat/lon points."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def trajectory_residuals(points: list[dict]) -> list[float]:
    """
    For each point, compute its perpendicular distance from the line connecting
    its two neighbours. End points use a window of 3 neighbours to avoid
    flagging normal acceleration/deceleration at flight start and end.
    Returns a list of residuals (metres) in index order.
    """
    n = len(points)
    residuals = []
    for i, p in enumerate(points):
        if i == 0:
            # Use points 1 and 2 as the reference line
            prev, nxt = points[1], points[2]
        elif i == n - 1:
            # Use points n-3 and n-2 as the reference line
            prev, nxt = points[n-3], points[n-2]
        else:
            prev, nxt = points[i-1], points[i+1]

        scale = 111320.0
        cos_lat = math.cos(math.radians(p['lat']))

        ax = (prev['lon'] - p['lon']) * scale * cos_lat
        ay = (prev['lat'] - p['lat']) * scale
        bx = (nxt['lon']  - p['lon']) * scale * cos_lat
        by = (nxt['lat']  - p['lat']) * scale

        cross = abs(ax * by - ay * bx)
        base  = math.hypot(bx - ax, by - ay)
        residuals.append(cross / base if base > 0 else 0.0)
    return residuals


def zscore(values: list[float]) -> list[float]:
    mean = sum(values) / len(values)
    std  = math.sqrt(sum((v - mean)**2 for v in values) / len(values))
    if std == 0:
        return [0.0] * len(values)
    return [(v - mean) / std for v in values]


def flag_trajectory_outliers(points: list[dict], z_threshold: float) -> dict[int, float]:
    """Return {image_index: z_score} for trajectory outliers."""
    residuals = trajectory_residuals(points)
    zscores   = zscore(residuals)
    return {
        points[i]['index']: round(zscores[i], 2)
        for i in range(len(points))
        if abs(zscores[i]) > z_threshold
    }


# --- Sharpness check ---

def laplacian_variance(image_path: Path) -> float | None:
    """Return Laplacian variance of a greyscale image. None if unreadable."""
    try:
        import cv2
        import numpy as np
        img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return None
        return float(cv2.Laplacian(img, cv2.CV_64F).var())
    except ImportError:
        return None


def flag_blurry_images(image_paths: list[Path], threshold: float) -> dict[str, float]:
    """Return {filename: score} for images below the sharpness threshold."""
    flagged = {}
    for p in image_paths:
        score = laplacian_variance(p)
        if score is not None and score < threshold:
            flagged[p.name] = round(score, 1)
    return flagged


# --- Completeness check ---

BAND_SUFFIXES = ['_D.JPG', '_MS_G.TIF', '_MS_R.TIF', '_MS_RE.TIF', '_MS_NIR.TIF']


def flag_incomplete_sets(image_folder: Path) -> dict[int, list[str]]:
    """
    Return {image_index: [missing_band_suffixes]} for incomplete capture sets.
    """
    # Group files by image index (the 4-digit number before the band suffix)
    index_map: dict[int, set[str]] = {}
    pattern = re.compile(r'_(\d{4})_(D\.JPG|MS_G\.TIF|MS_R\.TIF|MS_RE\.TIF|MS_NIR\.TIF)$',
                         re.IGNORECASE)
    for f in image_folder.iterdir():
        m = pattern.search(f.name)
        if m:
            idx = int(m.group(1))
            band = '_' + m.group(2).upper()
            index_map.setdefault(idx, set()).add(band)

    expected = {s.upper().lstrip('_D') for s in
                ['_D.JPG', '_MS_G.TIF', '_MS_R.TIF', '_MS_RE.TIF', '_MS_NIR.TIF']}

    incomplete = {}
    for idx, found in index_map.items():
        found_norm = {s.lstrip('_') for s in found}
        missing = [s for s in BAND_SUFFIXES if s.lstrip('_').upper() not in
                   {x.upper() for x in found_norm}]
        if missing:
            incomplete[idx] = missing
    return incomplete


# --- Quarantine ---

def quarantine_images(image_folder: Path, filenames: list[str]) -> None:
    q = image_folder / 'quarantine'
    q.mkdir(exist_ok=True)
    for name in filenames:
        src = image_folder / name
        if src.exists():
            shutil.move(str(src), str(q / name))
            print(f'  Moved {name} → quarantine/')


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description='Flag suspect images in a Mavic 3M mission folder.'
    )
    parser.add_argument('image_folder', type=Path, help='Mission image folder')
    parser.add_argument('mrk_file',     type=Path, help='Timestamp.MRK file')
    parser.add_argument('--sharpness-threshold', type=float, default=100.0,
                        help='Laplacian variance below this = blurry (default: 100)')
    parser.add_argument('--trajectory-zscore', type=float, default=3.0,
                        help='Z-score above this = trajectory outlier (default: 3.0)')
    parser.add_argument('--quarantine', action='store_true',
                        help='Move flagged RGB images to <image_folder>/quarantine/')
    parser.add_argument('--report', type=Path, default=None,
                        help='Save CSV report to this path')
    args = parser.parse_args()

    if not args.image_folder.exists():
        sys.exit(f'Error: image folder not found: {args.image_folder}')
    if not args.mrk_file.exists():
        sys.exit(f'Error: MRK file not found: {args.mrk_file}')
    if not validate_mrk(args.mrk_file):
        sys.exit(f'Error: {args.mrk_file} does not appear to be a valid Mavic 3M MRK file.')

    # --- Parse MRK ---
    points = parse_mrk(args.mrk_file)
    print(f'Parsed {len(points)} positions from {args.mrk_file.name}')

    # --- Trajectory outliers ---
    print(f'\nChecking trajectory (z-score threshold: {args.trajectory_zscore})...')
    traj_flags = flag_trajectory_outliers(points, args.trajectory_zscore)
    if traj_flags:
        for idx, z in sorted(traj_flags.items()):
            print(f'  Image {idx:04d}: trajectory z-score = {z}  *** FLAGGED')
    else:
        print('  No trajectory outliers found.')

    # --- Sharpness ---
    rgb_images = sorted(args.image_folder.glob('*_D.JPG'))
    print(f'\nChecking sharpness on {len(rgb_images)} RGB images '
          f'(threshold: {args.sharpness_threshold})...')
    blur_flags = flag_blurry_images(rgb_images, args.sharpness_threshold)
    if blur_flags:
        for name, score in sorted(blur_flags.items()):
            print(f'  {name}: sharpness = {score}  *** FLAGGED')
    else:
        print('  No blurry images found.')
        if not rgb_images:
            print('  (No RGB images found — is opencv-python installed?)')

    # --- Completeness ---
    print(f'\nChecking band completeness...')
    incomplete = flag_incomplete_sets(args.image_folder)
    if incomplete:
        for idx, missing in sorted(incomplete.items()):
            print(f'  Image {idx:04d}: missing {missing}  *** FLAGGED')
    else:
        print('  All capture sets complete.')

    # --- Summary ---
    all_flagged_indices = set(traj_flags.keys()) | {
        int(re.search(r'_(\d{4})_D', n).group(1))
        for n in blur_flags if re.search(r'_(\d{4})_D', n)
    } | set(incomplete.keys())

    print(f'\n--- Summary ---')
    print(f'  Trajectory outliers:  {len(traj_flags)}')
    print(f'  Blurry images:        {len(blur_flags)}')
    print(f'  Incomplete sets:      {len(incomplete)}')
    print(f'  Total unique flagged: {len(all_flagged_indices)}')

    # --- CSV report ---
    if args.report:
        rows = []
        for p in points:
            idx = p['index']
            rows.append({
                'index':          idx,
                'trajectory_flag': idx in traj_flags,
                'trajectory_zscore': traj_flags.get(idx, ''),
                'sharpness_flag': any(
                    re.search(rf'_{idx:04d}_D', n) for n in blur_flags
                ),
                'sharpness_score': next(
                    (v for n, v in blur_flags.items()
                     if re.search(rf'_{idx:04d}_D', n)), ''
                ),
                'incomplete_set': idx in incomplete,
                'missing_bands':  ';'.join(incomplete.get(idx, [])),
            })
        with open(args.report, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f'\nReport saved to {args.report}')

    # --- Quarantine ---
    if args.quarantine and all_flagged_indices:
        print(f'\nMoving flagged images to quarantine/...')
        to_move = []
        for idx in all_flagged_indices:
            # Move all band files for flagged indices
            for f in args.image_folder.glob(f'*_{idx:04d}_*.TIF'):
                to_move.append(f.name)
            for f in args.image_folder.glob(f'*_{idx:04d}_D.JPG'):
                to_move.append(f.name)
        quarantine_images(args.image_folder, to_move)


if __name__ == '__main__':
    main()
