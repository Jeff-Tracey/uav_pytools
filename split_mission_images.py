#!/usr/bin/env python3
"""
split_mission_images.py

Split a DJI Mavic 3M raw mission folder into separate RGB and multispectral
working copies, with all metadata files copied to both. The original mission
folder is left untouched as an archive.

Output directories are created as siblings of the input folder:
    <mission_folder>_RGB/   — RGB JPG images + metadata
    <mission_folder>_MS/    — Multispectral GeoTIFF images + metadata

Usage:
    python split_mission_images.py <mission_folder>
    python split_mission_images.py <mission_folder> --dry-run
"""

import argparse
import shutil
import sys
from pathlib import Path


# --- File classification ---

# RGB: DJI wide-angle camera JPEGs (_W.JPG)
RGB_SUFFIXES = {'.jpg', '.jpeg'}
RGB_PATTERNS = ['_W']  # filename must end with one of these before the extension

# Multispectral: GeoTIFF band files (_G, _R, _RE, _NIR)
MS_SUFFIXES = {'.tif', '.tiff'}

def classify_file(path: Path) -> str:
    """
    Return 'rgb', 'ms', 'metadata', or 'unknown' for a given file.
    """
    suffix = path.suffix.lower()
    stem = path.stem.upper()

    if suffix in RGB_SUFFIXES:
        if any(stem.endswith(p) for p in RGB_PATTERNS):
            return 'rgb'
        # JPEGs that don't match _W pattern — treat as metadata (e.g. thumbnails)
        return 'metadata'

    if suffix in MS_SUFFIXES:
        return 'ms'

    # Everything else: metadata
    return 'metadata'


# --- Core logic ---

def split_mission(mission_dir: Path, dry_run: bool = False) -> None:
    if not mission_dir.exists():
        print(f"ERROR: Mission folder not found: {mission_dir}", file=sys.stderr)
        sys.exit(1)

    if not mission_dir.is_dir():
        print(f"ERROR: Path is not a directory: {mission_dir}", file=sys.stderr)
        sys.exit(1)

    parent = mission_dir.parent
    rgb_dir = parent / f"{mission_dir.name}_RGB"
    ms_dir  = parent / f"{mission_dir.name}_MS"

    # Guard against overwriting existing working copies
    for d in (rgb_dir, ms_dir):
        if d.exists():
            print(
                f"ERROR: Output directory already exists: {d}\n"
                f"       Remove or rename it before running this script.",
                file=sys.stderr
            )
            sys.exit(1)

    # Classify all files in the mission folder (non-recursive)
    files = sorted(f for f in mission_dir.iterdir() if f.is_file())

    rgb_files      = [f for f in files if classify_file(f) == 'rgb']
    ms_files       = [f for f in files if classify_file(f) == 'ms']
    metadata_files = [f for f in files if classify_file(f) == 'metadata']
    unknown_files  = [f for f in files if classify_file(f) == 'unknown']

    # Summary
    print(f"Mission folder : {mission_dir}")
    print(f"RGB images     : {len(rgb_files)}")
    print(f"MS images      : {len(ms_files)} (across all bands)")
    print(f"Metadata files : {len(metadata_files)}")
    if unknown_files:
        print(f"Unknown files  : {len(unknown_files)} (will be ignored)")
        for f in unknown_files:
            print(f"    {f.name}")
    print()
    print(f"Output RGB     : {rgb_dir}")
    print(f"Output MS      : {ms_dir}")

    if dry_run:
        print("\n[DRY RUN — no files will be copied]")
        print("\nRGB directory would contain:")
        for f in sorted(rgb_files + metadata_files):
            print(f"    {f.name}")
        print("\nMS directory would contain:")
        for f in sorted(ms_files + metadata_files):
            print(f"    {f.name}")
        return

    # Create output directories
    rgb_dir.mkdir()
    ms_dir.mkdir()

    # Copy files
    def copy_files(file_list: list, dest: Path, label: str) -> None:
        print(f"\nCopying {label} to {dest.name}/")
        for f in sorted(file_list):
            dest_path = dest / f.name
            shutil.copy2(f, dest_path)
            print(f"    {f.name}")

    copy_files(rgb_files,      rgb_dir, "RGB images")
    copy_files(metadata_files, rgb_dir, "metadata")
    copy_files(ms_files,       ms_dir,  "MS images")
    copy_files(metadata_files, ms_dir,  "metadata")

    print(f"\nDone.")
    print(f"  RGB working copy : {rgb_dir}")
    print(f"  MS working copy  : {ms_dir}")
    print(f"  Archive (untouched): {mission_dir}")


# --- CLI ---

def main():
    parser = argparse.ArgumentParser(
        description="Split a Mavic 3M mission folder into RGB and multispectral working copies."
    )
    parser.add_argument(
        "mission_folder",
        type=Path,
        help="Path to the raw mission folder to split"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be copied without copying anything"
    )
    args = parser.parse_args()

    split_mission(args.mission_folder.resolve(), dry_run=args.dry_run)


if __name__ == "__main__":
    main()
