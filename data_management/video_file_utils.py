import os
import csv
import datetime
import subprocess
from pathlib import Path

# --- Configuration ---
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.avi'}
PLACEHOLDER_ACTIVITY = "Unknown"
CAMERA_NAME = "GoPro01"  # Change as needed
MEDIA_ROOT = Path("/path/to/your/media")  # CHANGE THIS
LOG_CSV_PATH = Path("/path/to/your/media_log.csv")  # CHANGE THIS

# --- Helper Functions ---

def get_video_metadata(video_path):
    """Extract duration and creation date using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "format=duration:format_tags=creation_time",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output = result.stdout.strip().split("\n")
    
    duration = float(output[0]) if output else 0
    try:
        creation_date = datetime.datetime.fromisoformat(output[1].replace("Z", "")).date()
    except (IndexError, ValueError):
        creation_date = datetime.datetime.fromtimestamp(video_path.stat().st_mtime).date()
    
    return duration, creation_date

def generate_filename(date, location, activity, camera, clip_id, extension):
    return f"{date.strftime('%Y%m%d')}_{location}_{activity}_{camera}_{clip_id:03d}{extension}"

def build_log_entry(file_name, date, location, activity, camera, duration, notes="", tags=""):
    return {
        "file_name": file_name,
        "date": str(date),
        "location": location,
        "activity": activity,
        "camera": camera,
        "duration": f"{int(duration // 60):02}:{int(duration % 60):02}",
        "notes": notes,
        "tags": tags
    }

def scan_and_process_videos(directory, location="Unknown"):
    log_entries = []
    clip_counter = 1
    for file in sorted(Path(directory).rglob("*")):
        if file.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        duration, creation_date = get_video_metadata(file)
        new_filename = generate_filename(
            creation_date, location, PLACEHOLDER_ACTIVITY, CAMERA_NAME, clip_counter, file.suffix.lower()
        )
        new_path = file.parent / new_filename
        if not new_path.exists():
            os.rename(file, new_path)
        log_entries.append(build_log_entry(
            new_filename, creation_date, location, PLACEHOLDER_ACTIVITY, CAMERA_NAME, duration
        ))
        clip_counter += 1
    return log_entries

def write_log_csv(log_entries, csv_path):
    fieldnames = ["file_name", "date", "location", "activity", "camera", "duration", "notes", "tags"]
    write_header = not csv_path.exists()
    
    with open(csv_path, "a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(log_entries)

# --- Main Execution ---

if __name__ == "__main__":
    # CHANGE this to match your folder of raw videos
    target_directory = MEDIA_ROOT / "2025" / "2025-08-03_Catalina_Diving"
    location = "Catalina"  # You can update per batch

    log_entries = scan_and_process_videos(target_directory, location=location)
    write_log_csv(log_entries, LOG_CSV_PATH)

    print(f"Processed {len(log_entries)} video(s). Log updated at {LOG_CSV_PATH}.")
