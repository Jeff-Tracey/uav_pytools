"""
DJI SRT File Parser

A refactored module for parsing DJI SRT files into structured DataFrames.
Implements research software engineering best practices including modularity,
type hints, configuration management, and comprehensive error handling.
"""

import argparse
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Constants
DEFAULT_ENCODING = 'utf-8'
SRT_EXTENSIONS = ('.srt', '.SRT')
TIMESTAMP_PATTERN = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})'


@dataclass
class SRTConfig:
    """Configuration class for SRT parsing parameters."""
    
    # Regex patterns for extracting data from SRT content
    PATTERNS = {
        'frame_cnt': r'FrameCnt: (\d+)',
        'diff_time': r'DiffTime: (\d+)ms',
        'timestamp': TIMESTAMP_PATTERN,
        'iso': r'\[iso: (\d+)\]',
        'shutter': r'\[shutter: ([\d/.]+)\]',
        'fnum': r'\[fnum: ([\d.]+)\]',
        'ev': r'\[ev: ([-\d.]+)\]',
        'color_md': r'\[color_md: ([^\]]+)\]',
        'focal_len': r'\[focal_len: ([\d.]+)\]',
        'latitude': r'\[latitude: ([-\d.]+)\]',
        'longitude': r'\[longitude: ([-\d.]+)\]',
        'altitude': r'\[rel_alt: ([\d.]+) abs_alt: ([\d.]+)\]',
        'ct': r'\[ct: (\d+)\]'
    }
    
    # Output column names in order
    OUTPUT_COLUMNS = [
        'subtitle_num', 'start_time', 'end_time', 'frame_cnt',
        'diff_time_ms', 'timestamp', 'iso', 'shutter', 'fnum',
        'ev', 'color_mode', 'focal_length', 'latitude', 'longitude',
        'relative_altitude', 'absolute_altitude', 'ct'
    ]
    
    # Type converters for extracted values
    TYPE_CONVERTERS = {
        'frame_cnt': int,
        'diff_time': int,
        'iso': int,
        'fnum': float,
        'ev': float,
        'focal_len': float,
        'latitude': float,
        'longitude': float,
        'ct': int
    }


class SRTValidationError(Exception):
    """Custom exception for SRT file validation errors."""
    pass


class SRTParsingError(Exception):
    """Custom exception for SRT parsing errors."""
    pass


def validate_srt_file(srt_file: Union[str, Path]) -> Path:
    """
    Validate that the provided file is a valid, readable SRT file.
    
    Args:
        srt_file: Path to the SRT file to validate
        
    Returns:
        Path object of the validated file
        
    Raises:
        SRTValidationError: If file validation fails
    """
    file_path = Path(srt_file)
    
    # Check file extension
    if file_path.suffix.lower() not in [ext.lower() for ext in SRT_EXTENSIONS]:
        raise SRTValidationError(f"File must have .srt extension, got: {file_path.suffix}")
    
    # Check file exists
    if not file_path.exists():
        raise SRTValidationError(f"File does not exist: {file_path}")
    
    # Check it's a file (not directory)
    if not file_path.is_file():
        raise SRTValidationError(f"Path is not a file: {file_path}")
    
    # Check file is readable
    if not os.access(file_path, os.R_OK):
        raise SRTValidationError(f"File is not readable: {file_path}")
    
    # Check file is not empty
    if file_path.stat().st_size == 0:
        raise SRTValidationError(f"File is empty: {file_path}")
    
    logger.info(f"File validation successful: {file_path}")
    return file_path


def find_srt_files(directory: Path, recursive: bool = False) -> List[Path]:
    """
    Find all SRT files in a directory.
    
    Args:
        directory: Directory to search
        recursive: Whether to search subdirectories
        
    Returns:
        List of SRT file paths sorted alphabetically
    """
    srt_files = []
    
    # Find both .srt and .SRT files
    for ext in ['srt', 'SRT']:
        if recursive:
            srt_files.extend(directory.rglob(f"*.{ext}"))
        else:
            srt_files.extend(directory.glob(f"*.{ext}"))
    
    # Sort for consistent ordering
    srt_files.sort()
    
    logger.info(f"Found {len(srt_files)} SRT files in {directory}")
    return srt_files


def parse_srt_records_with_filename(srt_file: Union[str, Path], config: Optional[SRTConfig] = None) -> pd.DataFrame:
    """
    Parse an SRT file and add filename column to the DataFrame.
    
    Args:
        srt_file: Path to the SRT file
        config: Configuration object (uses default if None)
        
    Returns:
        DataFrame with parsed records including 'source_file' column
    """
    if config is None:
        config = SRTConfig()
    
    # Parse the SRT file normally
    df = parse_srt_records(srt_file, config)
    
    # Add source filename column
    file_path = Path(srt_file)
    df['source_file'] = file_path.name
    
    # Reorder columns to put source_file at the beginning
    cols = ['source_file'] + [col for col in df.columns if col != 'source_file']
    df = df[cols]
    
    return df if isinstance(df, pd.DataFrame) else df.to_frame().T


def process_directory_to_combined_dataframe(
    directory: Union[str, Path], 
    recursive: bool = False,
    config: Optional[SRTConfig] = None,
    output_file: Optional[Union[str, Path]] = None
) -> pd.DataFrame:
    """
    Process all SRT files in a directory and combine into a single DataFrame.
    
    Args:
        directory: Path to directory containing SRT files
        recursive: Whether to search subdirectories recursively
        config: Configuration object (uses default if None)
        output_file: Optional path to save combined CSV file
        
    Returns:
        Combined DataFrame with all records from all SRT files
        
    Raises:
        SRTValidationError: If directory doesn't exist or contains no SRT files
    """
    directory_path = Path(directory)
    
    # Validate directory
    if not directory_path.exists():
        raise SRTValidationError(f"Directory does not exist: {directory_path}")
    if not directory_path.is_dir():
        raise SRTValidationError(f"Path is not a directory: {directory_path}")
    
    # Find all SRT files
    srt_files = find_srt_files(directory_path, recursive)
    
    if not srt_files:
        raise SRTValidationError(f"No SRT files found in {directory_path}")
    
    logger.info(f"Processing {len(srt_files)} SRT files from {directory_path}")
    
    # Process each file and collect DataFrames
    dataframes = []
    processing_stats = {
        "successful": 0, 
        "failed": 0, 
        "total_records": 0,
        "failed_files": []
    }
    
    for srt_file in srt_files:
        try:
            logger.info(f"Processing: {srt_file}")
            
            # Parse the file with filename included
            df = parse_srt_records_with_filename(srt_file, config)
            
            if not df.empty:
                dataframes.append(df)
                processing_stats["successful"] += 1
                processing_stats["total_records"] += len(df)
                logger.info(f"Successfully processed {srt_file.name}: {len(df)} records")
            else:
                logger.warning(f"No records found in {srt_file.name}")
                
        except Exception as e:
            logger.error(f"Failed to process {srt_file}: {e}")
            processing_stats["failed"] += 1
            processing_stats["failed_files"].append(srt_file.name)
    
    # Combine all DataFrames
    if dataframes:
        combined_df = pd.concat(dataframes, ignore_index=True)
        logger.info(f"Combined {len(dataframes)} DataFrames into single DataFrame with {len(combined_df)} records")
    else:
        # Create empty DataFrame with expected columns
        if config is None:
            config = SRTConfig()
        combined_df = pd.DataFrame(columns=['source_file'] + config.OUTPUT_COLUMNS)
        logger.warning("No valid DataFrames to combine")
    
    # Save to file if specified
    if output_file:
        output_path = Path(output_file)
        combined_df.to_csv(output_path, index=False)
        logger.info(f"Saved combined DataFrame to {output_path}")
    
    # Log summary
    logger.info(f"Processing complete: {processing_stats['successful']} successful, "
                f"{processing_stats['failed']} failed, "
                f"{processing_stats['total_records']} total records")
    
    if processing_stats["failed_files"]:
        logger.warning(f"Failed files: {', '.join(processing_stats['failed_files'])}")
    
    return combined_df


def process_srt_batch_individual(
    directory: Union[str, Path],
    output_directory: Union[str, Path],
    recursive: bool = False,
    config: Optional[SRTConfig] = None
) -> Dict[str, pd.DataFrame]:
    """
    Process all SRT files in a directory and save individual CSV files.
    
    Args:
        directory: Path to directory containing SRT files
        output_directory: Directory to save individual CSV files
        recursive: Whether to search subdirectories recursively
        config: Configuration object (uses default if None)
        
    Returns:
        Dictionary mapping filename to DataFrame
    """
    directory_path = Path(directory)
    output_dir = Path(output_directory)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find SRT files
    srt_files = find_srt_files(directory_path, recursive)
    
    if not srt_files:
        raise SRTValidationError(f"No SRT files found in {directory_path}")
    
    results = {}
    
    for srt_file in srt_files:
        try:
            # Parse with filename included
            df = parse_srt_records_with_filename(srt_file, config)
            results[srt_file.name] = df
            
            # Save individual CSV
            csv_filename = srt_file.stem + '.csv'
            csv_path = output_dir / csv_filename
            df.to_csv(csv_path, index=False)
            
            logger.info(f"Processed {srt_file.name} → {csv_path} ({len(df)} records)")
            
        except Exception as e:
            logger.error(f"Failed to process {srt_file}: {e}")
    
    return results

def split_srt_content(content: str) -> List[str]:
    """
    Split SRT content into individual subtitle blocks.
    
    Args:
        content: Raw SRT file content
        
    Returns:
        List of subtitle blocks as strings
    """
    blocks = re.split(r'\n\s*\n', content.strip())
    logger.debug(f"Split content into {len(blocks)} blocks")
    return [block for block in blocks if block.strip()]


def clean_html_content(content: str) -> str:
    """
    Remove HTML tags from SRT content.
    
    Args:
        content: Raw content with HTML tags
        
    Returns:
        Cleaned content without HTML tags
    """
    # Remove font tags
    content = re.sub(r'<font[^>]*>', '', content)
    content = re.sub(r'</font>', '', content)
    return content


def extract_parameters(content: str, config: SRTConfig) -> Dict[str, Optional[Union[str, float, int]]]:
    """
    Extract all parameters from SRT content using configured patterns.
    
    Args:
        content: Cleaned SRT content
        config: Configuration object with patterns and converters
        
    Returns:
        Dictionary of extracted parameters
    """
    results = {}
    
    for key, pattern in config.PATTERNS.items():
        match = re.search(pattern, content)
        
        if match:
            if key == 'altitude':
                # Special handling for altitude (two values in one match)
                results['rel_alt'] = float(match.group(1))
                results['abs_alt'] = float(match.group(2))
            else:
                value = match.group(1)
                # Apply type conversion if configured
                if key in config.TYPE_CONVERTERS:
                    try:
                        value = config.TYPE_CONVERTERS[key](value)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to convert {key}='{value}': {e}")
                        value = None
                results[key] = value
        else:
            if key == 'altitude':
                results['rel_alt'] = None
                results['abs_alt'] = None
            else:
                results[key] = None
    
    return results


def parse_subtitle_block(block: str, config: SRTConfig) -> Optional[Dict[str, Union[str, int, float, None]]]:
    """
    Parse a single SRT subtitle block into a structured record.
    
    Args:
        block: Individual subtitle block as string
        config: Configuration object
        
    Returns:
        Dictionary containing parsed record or None if parsing fails
    """
    try:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            logger.warning(f"Skipping block with insufficient lines: {len(lines)}")
            return None
        
        # Parse subtitle number
        subtitle_num = int(lines[0])
        
        # Parse timestamps
        timestamp_line = lines[1]
        start_time, end_time = timestamp_line.split(' --> ')
        
        # Parse content (remove HTML tags)
        content_lines = lines[2:]
        content = ' '.join(content_lines)
        content = clean_html_content(content)
        
        # Extract all parameters
        params = extract_parameters(content, config)
        
        # Create record with consistent field names
        record = {
            'subtitle_num': subtitle_num,
            'start_time': start_time,
            'end_time': end_time,
            'frame_cnt': params.get('frame_cnt'),
            'diff_time_ms': params.get('diff_time'),
            'timestamp': params.get('timestamp'),
            'iso': params.get('iso'),
            'shutter': params.get('shutter'),
            'fnum': params.get('fnum'),
            'ev': params.get('ev'),
            'color_mode': params.get('color_md'),
            'focal_length': params.get('focal_len'),
            'latitude': params.get('latitude'),
            'longitude': params.get('longitude'),
            'relative_altitude': params.get('rel_alt'),
            'absolute_altitude': params.get('abs_alt'),
            'ct': params.get('ct')
        }
        
        return record
        
    except Exception as e:
        logger.error(f"Failed to parse subtitle block: {e}")
        logger.debug(f"Problematic block: {block[:100]}...")
        return None


def create_dataframe_old(records: List[Dict], config: SRTConfig) -> pd.DataFrame:
    """
    Create a pandas DataFrame from parsed records.
    
    Args:
        records: List of parsed record dictionaries
        config: Configuration object
        
    Returns:
        Pandas DataFrame with processed data
    """
    if not records:
        logger.warning("No records to create DataFrame from")
        return pd.DataFrame(columns=config.OUTPUT_COLUMNS)
    
    df = pd.DataFrame(records)
    
    # Convert timestamp to datetime if available
    if 'timestamp' in df.columns and not df['timestamp'].isna().all():
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            logger.info("Successfully converted timestamps to datetime")
        except Exception as e:
            logger.warning(f"Failed to convert timestamps to datetime: {e}")
    
    # Ensure all expected columns are present
    for col in config.OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = None
    
    # Reorder columns to match expected output
    df = df[config.OUTPUT_COLUMNS]
    
    logger.info(f"Created DataFrame with {len(df)} records and {len(df.columns)} columns")
    if isinstance(df, pd.Series):
        df = df.to_frame().T
    return df if isinstance(df, pd.DataFrame) else pd.DataFrame([df])


def create_dataframe(records: List[Dict], config: SRTConfig) -> pd.DataFrame:
    """
    Create a pandas DataFrame from parsed records.
    
    Args:
        records: List of parsed record dictionaries
        config: Configuration object
        
    Returns:
        Pandas DataFrame with processed data
    """
    if not records:
        logger.warning("No records to create DataFrame from")
        return pd.DataFrame(columns=config.OUTPUT_COLUMNS)
    
    df = pd.DataFrame(records)
    
    # Convert timestamp to datetime if available
    if 'timestamp' in df.columns and df['timestamp'].notna().any():
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            logger.info("Successfully converted timestamps to datetime")
        except Exception as e:
            logger.warning(f"Failed to convert timestamps to datetime: {e}")
    
    # Ensure all expected columns are present
    for col in config.OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = None
    
    # Reorder columns to match expected output
    df = df[config.OUTPUT_COLUMNS]
    
    logger.info(f"Created DataFrame with {len(df)} records and {len(df.columns)} columns")
    if isinstance(df, pd.Series):
        df = df.to_frame().T
    return df

def parse_srt_records(srt_file: Union[str, Path], config: Optional[SRTConfig] = None) -> pd.DataFrame:
    """
    Parse an SRT file and return a DataFrame with the records.
    
    Args:
        srt_file: Path to the SRT file to parse
        config: Optional configuration object. If None, uses default config.
        
    Returns:
        DataFrame containing the parsed records
        
    Raises:
        SRTValidationError: If file validation fails
        SRTParsingError: If parsing fails
    """
    if config is None:
        config = SRTConfig()
    
    # Validate input file
    file_path = validate_srt_file(srt_file)
    
    try:
        # Read file content
        with open(file_path, 'r', encoding=DEFAULT_ENCODING) as file:
            content = file.read()
        
        logger.info(f"Successfully read file: {file_path}")
        
        # Split content into blocks
        blocks = split_srt_content(content)
        
        # Parse each block
        records = []
        for i, block in enumerate(blocks):
            record = parse_subtitle_block(block, config)
            if record is not None:
                records.append(record)
            else:
                logger.warning(f"Failed to parse block {i+1}")
        
        # Create DataFrame
        df = create_dataframe(records, config)
        
        logger.info(f"Successfully parsed {len(records)} records from {len(blocks)} blocks")
        return df
        
    except Exception as e:
        raise SRTParsingError(f"Failed to parse SRT file {file_path}: {e}") from e


def main_old():
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(
        description="Parse DJI SRT files into structured CSV format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
            %(prog)s flight_data.srt
            %(prog)s flight_data.srt --output parsed_data.csv
            %(prog)s flight_data.srt --output parsed_data.csv --verbose
        """
    )
    
    parser.add_argument('srt_file', type=str, help='Path to the SRT file to parse')
    parser.add_argument('--output', '-o', type=str, default=None, help='Path to save the DataFrame as a CSV file (optional)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--log-level', type=str, default='WARNING',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='Set the logging level (default: WARNING)')
    parser.add_argument('--config', '-c', type=str, default=None, help='Path to custom configuration file (optional)')
    args = parser.parse_args()
    
    # Set logging level
    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')
    logging.getLogger().setLevel(numeric_level)
    
    try:
        # Parse the SRT file
        df = parse_srt_records(args.srt_file)
        
        # Display summary information
        print(f"\n{'='*50}")
        print("SRT PARSING SUMMARY")
        print(f"{'='*50}")
        print(f"File: {args.srt_file}")
        print(f"Records parsed: {len(df)}")
        print(f"Columns: {len(df.columns)}")
        
        print(f"\n{'='*50}")
        print("FIRST 5 RECORDS")
        print(f"{'='*50}")
        print(df.head())
        
        print(f"\n{'='*50}")
        print("DATAFRAME INFO")
        print(f"{'='*50}")
        df.info()
        
        # Save to CSV if requested
        if args.output:
            output_path = Path(args.output)
            df.to_csv(output_path, index=False)
            print(f"\n{'='*50}")
            print(f"DataFrame saved to: {output_path}")
            print(f"{'='*50}")
        
        logger.info("SRT file parsing completed successfully")
        
    except (SRTValidationError, SRTParsingError) as e:
        logger.error(f"Parsing failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    
    return 0


def main():
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(
        description="Parse DJI SRT files into structured CSV format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
            %(prog)s flight_data.srt                                    # Single file
            %(prog)s /path/to/srt/directory                             # All SRT files → combined CSV
            %(prog)s /path/to/srt/directory --recursive                 # Include subdirectories
            %(prog)s /path/to/srt/directory --output combined.csv       # Specify output file
            %(prog)s /path/to/srt/directory --batch --output-dir /out   # Individual CSV files
        """
    )
    
    parser.add_argument('path', type=str, help='Path to SRT file or directory containing SRT files')
    parser.add_argument('--output', '-o', type=str, default=None, 
                       help='Output CSV file path (for single file or combined output)')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='Output directory for individual CSV files (use with --batch)')
    parser.add_argument('--batch', action='store_true',
                       help='Process directory files individually (requires --output-dir)')
    parser.add_argument('--recursive', '-r', action='store_true',
                       help='Recursively search subdirectories for SRT files')
    parser.add_argument('--log-level', type=str, default='WARNING',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='Set the logging level (default: WARNING)')
    parser.add_argument('--config', '-c', type=str, default=None, 
                       help='Path to custom configuration file (optional)')
    
    args = parser.parse_args()
    
    # Set logging level
    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')
    logging.getLogger().setLevel(numeric_level)
    
    try:
        input_path = Path(args.path)
        
        if input_path.is_file():
            # Single file processing
            df = parse_srt_records_with_filename(input_path)
            print(f"Processed {input_path.name}: {len(df)} records")
            
            if args.output:
                df.to_csv(args.output, index=False)
                print(f"Saved to: {args.output}")
            else:
                print("DataFrame preview:")
                print(df.head())
                
        elif input_path.is_dir():
            if args.batch:
                # Individual file processing
                if not args.output_dir:
                    raise ValueError("--output-dir is required when using --batch")
                
                results = process_srt_batch_individual(
                    input_path, args.output_dir, args.recursive
                )
                print(f"Processed {len(results)} files individually")
                
            else:
                # Combined processing (default for directories)
                output_file = args.output or f"combined_srt_data.csv"
                
                combined_df = process_directory_to_combined_dataframe(
                    input_path, args.recursive, output_file=output_file
                )
                
                print(f"Combined {len(combined_df)} records from {input_path}")
                print(f"Files processed: {combined_df['source_file'].nunique()}")
                print(f"Saved to: {output_file}")
                
        else:
            raise SRTValidationError(f"Path does not exist: {input_path}")
            
    except (SRTValidationError, SRTParsingError) as e:
        logger.error(f"SRT processing error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    
    return 0

"""
# Process single file (includes filename column)
python import_dji_srt_file.py flight.srt --output flight_with_filename.csv

# Process directory and combine all files
python import_dji_srt_file.py /path/to/srt/files --output combined_flights.csv

# Process directory recursively and combine
python import_dji_srt_file.py /path/to/srt/files --recursive --output all_flights.csv

# Process directory and save individual CSV files
python import_dji_srt_file.py /path/to/srt/files --batch --output-dir /path/to/csvs

# Process with verbose logging
python import_dji_srt_file.py /path/to/srt/files --log-level INFO
"""

if __name__ == "__main__":
    exit(main())
