# Video Frame Extractor Usage

## Overview
The `video_frame_extractor.py` script extracts frames from video files (MP4 and other formats supported by OpenCV) and saves them as JPEG images.

## Installation
First, install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Mode 1: JSON Configuration (Extract Specific Frames)
Create a JSON configuration file specifying the output directory and frame numbers:

```json
{
    "video_path": "/path/to/video.mp4", 
    "output_directory": "./extracted_frames",
    "frame_numbers": [0, 30, 60, 90, 120, 150]
}
```

Then run:
```bash
python video_frame_extractor.py your_video.mp4 --json frame_extraction_config.json
```

### Mode 2: Skip Interval (Extract Every Nth Frame)
Extract every Nth frame by specifying how many frames to skip:

```bash
# Extract every 30th frame (skip 29 frames between extractions)
python video_frame_extractor.py your_video.mp4 --skip 29

# Extract every frame (no skipping)
python video_frame_extractor.py your_video.mp4 --skip 0

# Extract every 10th frame
python video_frame_extractor.py your_video.mp4 --skip 9
```

## Command Line Arguments

- `video_path` (required): Path to the input video file
- `--json`: Path to JSON configuration file (optional)
- `--skip`: Number of frames to skip between extractions (optional)

**Note**: You must provide either `--json` or `--skip`, but not both.

## Output
- Frames are saved as JPEG files with 95% quality
- Filenames follow the pattern: `frame_XXXXXX.jpg` (where XXXXXX is the zero-padded frame number)
- If using skip mode, output directory is automatically created as `{video_name}_frames`

## Examples

```bash
# Extract frames 0, 100, 200, 300, etc. using JSON config
python video_frame_extractor.py drone_flight.mp4 --json config.json

# Extract every 60th frame (good for 1-second intervals at 60fps)
python video_frame_extractor.py drone_flight.mp4 --skip 59

# Extract every frame (be careful with large videos!)
python video_frame_extractor.py short_clip.mp4 --skip 0
```
