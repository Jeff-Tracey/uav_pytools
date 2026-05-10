#!/usr/bin/env python3
"""
Video Frame Extractor

This script extracts frames from video files (MP4 and other formats) and saves them as JPEG images.
It supports two modes:
1. JSON configuration mode: Use a JSON file to specify output directory and specific frame numbers
2. Skip interval mode: Extract every Nth frame based on a skip interval

Usage:
    python video_frame_extractor.py <video_path> [--json <json_file>] [--skip <interval>]
    
Examples:
    # Extract specific frames using JSON config
    python video_frame_extractor.py video.mp4 --json config.json
    
    # Extract every 30th frame (skip 29 frames between extractions)
    python video_frame_extractor.py video.mp4 --skip 29
    
    # Extract every frame (no skipping)
    python video_frame_extractor.py video.mp4 --skip 0
"""

import cv2
import json
import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

def load_json_config(json_path: str) -> Dict[str, Any]:
    """
    Load configuration from JSON file.
    
    Expected JSON format:
    {
        "video_path": "/path/to/video.mp4",
        "output_directory": "/path/to/output/dir",
        "frame_numbers": [0, 30, 60, 90, 120]  // optional
    }
    
    Args:
        json_path (str): Path to the JSON configuration file
        
    Returns:
        Dict[str, Any]: Configuration dictionary
    """

    try:
        with open(json_path, 'r') as f:
            config = json.load(f)
        
        # Check required fields and types
        assert isinstance(config, dict), "JSON configuration must be a dictionary"
        assert 'video_path' in config, "JSON configuration must contain 'video_path' field"
        assert 'output_directory' in config, "JSON configuration must contain 'output_directory' field"
        assert 'frame_numbers' not in config or isinstance(config['frame_numbers'], list), "JSON configuration 'frame_numbers' must be a list or omitted"
        # Validate that video_path is a valid file
        if not os.path.isfile(config['video_path']):
            raise ValueError(f"Video file '{config['video_path']}' does not exist")
        # Note: output_directory will be created if it doesn't exist
        return config
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format in '{json_path}': {e}")
    except FileNotFoundError:
        raise ValueError(f"JSON configuration file not found: '{json_path}'")


def create_output_directory(output_dir: str) -> None:
    """
    Create the output directory for extracted JPEG images if it doesn't exist.
    
    Args:
        output_dir (str): Directory path to create
        
    Raises:
        OSError: If directory creation fails due to permissions or other issues
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"Output directory ready: {output_dir}")
    except OSError as e:
        raise OSError(f"Failed to create output directory '{output_dir}': {e}")


def extract_video_frames(video_path: str, output_dir: str, frame_numbers: Optional[List[int]] = None, skip_interval: Optional[int] = None) -> None:
    """
    Extract frames from a video file and save them as JPEG images.
    
    Args:
        video_path (str): Path to the input video file
        output_dir (str): Directory to save the extracted JPEG images
        frame_numbers (List[int], optional): Specific frame numbers to extract
        skip_interval (int, optional): Number of frames to skip between extractions (minus 1)
    """
    # Open the video file
    vid = cv2.VideoCapture(video_path)
    
    if not vid.isOpened():
        raise ValueError(f"Error: Could not open video file '{video_path}'")
    
    # Create output directory if it doesn't exist
    create_output_directory(output_dir)
    
    # Get video properties
    total_frames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = vid.get(cv2.CAP_PROP_FPS)
    
    print(f"Video: {video_path}")
    print(f"Total frames: {total_frames}")
    print(f"FPS: {fps}")
    print(f"Output directory: {output_dir}")
    
    frame_count = 0
    extracted_count = 0
    
    try:
        if frame_numbers is not None:
            # Extract specific frame numbers
            print(f"Extracting {len(frame_numbers)} specific frames...")
            
            # Sort frame numbers to process them in order
            sorted_frames = sorted(frame_numbers)
            
            for target_frame in sorted_frames:
                if target_frame >= total_frames:
                    print(f"Warning: Frame {target_frame} exceeds total frames ({total_frames}), skipping...")
                    continue
                
                # Set the frame position
                vid.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                ret, frame = vid.read()
                
                if ret:
                    # Create filename with zero-padded frame number
                    # TODO:: Use frame_count + 1
                    # TODO: Use basename_frame_000000.jpg (or basename/frame_000000.jpg) of image file
                    filename = f"frame_{target_frame:06d}.jpg"
                    output_path = os.path.join(output_dir, filename)
                    
                    # Save frame as JPEG
                    cv2.imwrite(output_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                    extracted_count += 1
                    print(f"Extracted frame {target_frame} -> {filename}")
                else:
                    print(f"Warning: Could not read frame {target_frame}")
        
        else:
            # Extract frames with skip interval
            skip_interval = skip_interval if skip_interval is not None else 0
            print(f"Extracting every {skip_interval + 1} frame(s)...")
            
            while True:
                ret, frame = vid.read()
                
                if not ret:
                    break
                
                # Check if we should extract this frame
                if frame_count % (skip_interval + 1) == 0:
                    # Create filename with zero-padded frame number
                    # TODO: Next two lines are repeated above (use DRY)
                    # TODO:: Use frame_count + 1
                    # TODO: Use basename_frame_000000.jpg (or basename/frame_000000.jpg) of image file
                    filename = f"frame_{frame_count:06d}.jpg"
                    output_path = os.path.join(output_dir, filename)
                    
                    # Save frame as JPEG
                    cv2.imwrite(output_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                    extracted_count += 1
                    
                    if extracted_count % 10 == 0:  # Progress update every 10 frames
                        print(f"Extracted {extracted_count} frames...")
                
                frame_count += 1
    
    finally:
        vid.release()
    
    print(f"Extraction complete! Extracted {extracted_count} frames from {total_frames} total frames.")




def main(args):
    """Main function to handle command line arguments and execute frame extraction."""

    try:
        if args.json_file:
            # JSON configuration mode
            config = load_json_config(args.json_file)
            video_path = config.get('video_path')
            output_dir = config['output_directory']
            frame_numbers = config.get('frame_numbers')
            
            if not isinstance(video_path, str) or not video_path:
                print("Error: 'video_path' must be a non-empty string in the JSON configuration", file=sys.stderr)
                sys.exit(1)
            if not isinstance(output_dir, str) or not output_dir:
                print("Error: 'output_directory' must be a non-empty string in the JSON configuration", file=sys.stderr)
                sys.exit(1)
            if frame_numbers is not None and not isinstance(frame_numbers, list):
                print("Error: 'frame_numbers' must be a list in the JSON configuration", file=sys.stderr)
                sys.exit(1)
            extract_video_frames(
                video_path=video_path,
                output_dir=output_dir,
                frame_numbers=frame_numbers
            )
        
        elif args.skip_interval is not None and args.video_path is not None:
            # Skip interval mode
            # Validate video file exists
            if not os.path.isfile(args.video_path):
                print(f"Error: Video file '{args.video_path}' not found", file=sys.stderr)
                sys.exit(1)
            
            # Use current directory + video filename as default output directory
            video_name = Path(args.video_path).stem
            output_dir = f"{video_name}_frames"
            
            extract_video_frames(
                video_path=args.video_path,
                output_dir=output_dir,
                skip_interval=args.skip_interval
            )
        
        else:
            print("Error: Must provide either --json or both video_path and --skip arguments", file=sys.stderr)
            parser.print_help()
            sys.exit(1)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract frames from video files and save as JPEG images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
        %(prog)s video.mp4 --json config.json
        %(prog)s video.mp4 --skip 29
        %(prog)s video.mp4 --skip 0
        """
    )

    parser.add_argument('video_path', nargs='?', help='Path to the input video file (required when using --skip mode)')  
    parser.add_argument('--json', dest='json_file', help='Path to JSON configuration file (optional)')
    parser.add_argument('--skip', type=int, dest='skip_interval', help='Number of frames to skip between extractions (optional, default: 0)')
    args = parser.parse_args()
    
    main(args)
