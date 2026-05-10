# uav_pytools

Python utilities for DJI UAV mission planning, data management, and project setup. Developed for ecological field work with the DJI Mavic 3M (multispectral) and DJI Air 3S.

```
mission_planning/    — pre-flight calculations
data_management/     — post-flight data processing and format conversion
project_management/  — project directory setup
tests/               — test suite
```

---

## Requirements

```bash
pip install -r requirements.txt
```

Core dependencies: `pandas`, `numpy`, `opencv-python`, `geopandas`, `geojson`,
`shapely`. `ffprobe` (part of ffmpeg) required for `video_file_utils.py`.

Python 3.8+

---

## Mission Planning

### `mission_planning/calc_drone_gsd.py`
Calculate ground sample distance (GSD) from flight altitude (AGL), or the
altitude needed to achieve a target GSD. Supports Mavic 3M RGB and Multispectral
cameras, and DJI Air 2S. Camera specs are hardcoded from DJI documentation.

```bash
# GSD at 60m AGL for Mavic 3M multispectral
python calc_drone_gsd.py --drone DJI_Mavic_3M --image_type Multispectral --agl 60

# Altitude needed for 3cm/px GSD (RGB)
python calc_drone_gsd.py --drone DJI_Mavic_3M --image_type RGB --gsd 3.0

# Show all outputs
python calc_drone_gsd.py --drone DJI_Mavic_3M --image_type Multispectral --agl 60 --gsd 3.0 --debug
```

Options: `--drone` (DJI_Mavic_3M, DJI_Air_2S), `--image_type` (RGB, Multispectral,
Wide, Tele), `--agl` (meters), `--gsd` (cm/px), `--debug`

---

### `mission_planning/perceived_altitude.py`
Calculate perceived (density) altitude from true altitude, barometric pressure,
and temperature. Useful for understanding drone performance at elevation or in
non-standard atmospheric conditions. Currently a module (functions only, no CLI).

```python
from perceived_altitude import alt_perceived
density_alt = alt_perceived(altitude=500, pressure=980, temperature=25)
```

---

## Data Management

### `data_management/mrk_to_geodata.py`
Convert a DJI Mavic 3M `Timestamp.MRK` file to KML, GeoJSON, or Shapefile.
The MRK file contains PPK timestamp and position data for each image capture.
Output includes camera location points and a flight path line.

```bash
# Default output: KML
python mrk_to_geodata.py mission/DJI_Timestamp.MRK output/flight_path.kml

# GeoJSON
python mrk_to_geodata.py mission/DJI_Timestamp.MRK output/flight_path.geojson --format geojson

# Shapefile
python mrk_to_geodata.py mission/DJI_Timestamp.MRK output/flight_path --format shapefile
```

---

### `data_management/flag_suspect_images.py`
Flag potentially problematic images in a Mavic 3M mission folder before
photogrammetry processing. Three independent checks:

1. **Trajectory outliers** — perpendicular deviation from local flight path
   (MRK-based); z-score threshold
2. **Sharpness** — Laplacian variance on RGB images; flags motion blur or
   focus issues
3. **Band completeness** — confirms all four multispectral bands (G, R, RE, NIR)
   are present for each image index

```bash
# Report only
python flag_suspect_images.py mission/ --report

# Quarantine flagged images (moves to mission/quarantine/)
python flag_suspect_images.py mission/ --quarantine

# Adjust thresholds
python flag_suspect_images.py mission/ --trajectory-zscore 2.5 --sharpness-threshold 50
```

Options: `--sharpness-threshold` (default 100), `--trajectory-zscore` (default 3.0),
`--quarantine`, `--report`

---

### `data_management/split_mission_images.py`
Split a raw Mavic 3M mission folder into separate RGB and multispectral working
copies for independent WebODM processing. All metadata files are copied to both.
The original folder is left untouched as an archive.

Output directories are created as siblings of the input folder:
- `<mission>_RGB/` — `_W.JPG` files + all metadata
- `<mission>_MS/` — `.TIF` band files + all metadata

```bash
# Preview without copying
python split_mission_images.py /path/to/mission --dry-run

# Run
python split_mission_images.py /path/to/mission
```

Errors if output directories already exist — protects against overwriting a
working copy already in use.

---

### `data_management/geojson_to_shapefile.py`
Convert a GeoJSON file of camera locations (from DJI flight logs or MRK export)
to ESRI Shapefiles — a camera location point shapefile and a flight path line
shapefile. Reprojects to a specified EPSG coordinate system.

Currently a module with a hardcoded `__main__` block. Edit the paths and EPSG
at the bottom of the file before running.

```bash
python geojson_to_shapefile.py
```

---

### `data_management/import_dji_srt_file.py`
Parse DJI SRT (SubRip subtitle) files into structured pandas DataFrames. DJI
video files embed flight telemetry — GPS position, altitude, ISO, shutter speed,
focal length, and more — as SRT subtitle tracks. This script extracts that
telemetry into a clean tabular format.

Supports single file, directory (combined output), or directory batch
(individual CSV per file) modes.

```bash
# Single file → CSV
python import_dji_srt_file.py flight.srt --output flight.csv

# All SRT files in directory → combined CSV
python import_dji_srt_file.py /path/to/srt/files --output combined.csv

# All SRT files → one CSV per file
python import_dji_srt_file.py /path/to/srt/files --batch --output-dir /path/to/csvs

# Recursive directory search
python import_dji_srt_file.py /path/to/srt/files --recursive --output all.csv

# Verbose logging
python import_dji_srt_file.py flight.srt --log-level INFO
```

**Output columns:** `subtitle_num`, `start_time`, `end_time`, `frame_cnt`,
`diff_time_ms`, `timestamp`, `iso`, `shutter`, `fnum`, `ev`, `color_mode`,
`focal_length`, `latitude`, `longitude`, `relative_altitude`, `absolute_altitude`, `ct`

Python API:
```python
from import_dji_srt_file import parse_srt_records
df = parse_srt_records('flight.srt')
```

Tests: `python -m pytest tests/test_import_dji_srt_file.py -v`

---

### `data_management/video_frame_extractor.py`
Extract frames from DJI video files (MP4 and other formats) and save as JPEG
images. Two modes:

1. **JSON config mode** — specify exact frame numbers and output directory via
   a JSON config file (see `frame_extraction_config.json` for format)
2. **Skip interval mode** — extract every Nth frame

```bash
# Extract specific frames using JSON config
python video_frame_extractor.py video.mp4 --json frame_extraction_config.json

# Extract every 30th frame
python video_frame_extractor.py video.mp4 --skip 29

# Extract every frame
python video_frame_extractor.py video.mp4 --skip 0
```

See `VIDEO_FRAME_EXTRACTOR_README.md` for full documentation.

---

### `data_management/video_file_utils.py`
Utility module for scanning, renaming, and logging video files from a media
directory. Uses `ffprobe` to extract duration and creation date metadata.
Generates standardized filenames (`YYYYMMDD_location_activity_camera_NNN.ext`)
and builds a CSV log of all video files.

Currently a module (no CLI). Edit configuration constants at the top of the
file (`MEDIA_ROOT`, `LOG_CSV_PATH`, `CAMERA_NAME`) before importing or running.

---

## Project Management

### `project_management/create_drone_project.py`
Create directory structures for drone photogrammetry projects. Three modes:

**One-off mission** (default) — self-contained dated project:
```
YYYYMMDD_site-name_mission-type/
├── planning/  (checklists/, airspace/, flight_path/)
├── field_notes/
├── raw_data/
├── working_data/         ← split_mission_images.py writes here
├── webodm_output/        (orthophoto/, dsm/, dtm/, pointcloud/, model3d/)
├── gis/
├── deliverables/
└── processing_notes.md
```

**Repeat monitoring site** (`--new-site`) — site-level structure with dated visits:
```
site-name_mission-type/
├── planning/  (checklists/, airspace/, flight_path/)
└── visits/
    └── YYYYMMDD/   ← same subdirs as one-off, minus planning/
```

**Add visit** (`--add-visit`) — adds a new dated visit to an existing site.

```bash
# One-off mission (today's date)
python create_drone_project.py rancho-mission-canyon ms-mapping

# One-off mission (specific date)
python create_drone_project.py rancho-mission-canyon ms-mapping --date 20260506

# New repeat monitoring site
python create_drone_project.py rancho-mission-canyon ms-mapping --new-site

# Add a visit to an existing site
python create_drone_project.py rancho-mission-canyon ms-mapping --add-visit

# Any mode with a checklist file copied into planning/checklists/
python create_drone_project.py rancho-mission-canyon ms-mapping --checklist ~/checklists/mavic3m.pdf

# Specify output location
python create_drone_project.py rancho-mission-canyon ms-mapping --project-path /path/to/projects
```

Mission types: `ms-mapping`, `rgb-mapping`, `ms-rgb-mapping`, `3d-model`, `survey`

### `create_drone_project-backup.py`
Sets up a standard directory structure for a new drone project, including
subdirectories for raw footage, editing assets, SfM outputs, documentation,
and deliverables. Creates a project proposal template in Markdown.

Supports project types: Default, Vegetation Imagery, Drone Mapping, Drone
Videography, Drone Photography.

*Note: This is a backup/development copy. Work in progress — additional project
types and dated directory naming (`YYYYMMDD_site-name_mission-type/`) to be added.*

---

## Typical Workflow

```
Pre-mission
  └── mission_planning/calc_drone_gsd.py          # determine AGL for target GSD

Post-mission (raw data in hand)
  └── data_management/flag_suspect_images.py      # check for bad images before processing
  └── data_management/mrk_to_geodata.py           # export flight path for QGIS / documentation
  └── data_management/split_mission_images.py     # create RGB and MS working copies for WebODM

Video data
  └── data_management/import_dji_srt_file.py      # extract telemetry from video SRT files
  └── data_management/video_frame_extractor.py    # pull frames for annotation or review
```

---

## Notes

- Scripts target DJI Mavic 3M file naming conventions (`_W.JPG`, `_G.TIF`,
  `_R.TIF`, `_RE.TIF`, `_NIR.TIF`, `Timestamp.MRK`). Adaptations may be needed
  for other DJI platforms.
- `geojson_to_shapefile.py` and `video_file_utils.py` have hardcoded paths in
  their `__main__` blocks — edit before running.
- `perceived_altitude.py` is a utility module; no CLI yet.

---

---

## License

RAIL Non-Commercial License — free for academic research, conservation science,
ecological monitoring, wildlife management, environmental education, and use by
non-profit organizations and government agencies. Commercial use requires a
separate license. See [LICENSE.md](LICENSE.md) for full terms.
