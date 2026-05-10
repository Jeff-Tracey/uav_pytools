# DJI SRT File Parser

A robust Python module for parsing DJI SRT (SubRip subtitle) files into structured pandas DataFrames. This refactored version implements research software engineering best practices for maintainability, testability, and extensibility.

## Features

- **Comprehensive validation**: Robust file validation with descriptive error messages
- **Modular design**: Separated concerns with focused, single-responsibility functions
- **Type safety**: Full type hints for better code clarity and IDE support
- **Configurable parsing**: Easily customizable patterns and output formats
- **Extensive testing**: Comprehensive test suite with >95% code coverage
- **Logging support**: Structured logging for debugging and monitoring
- **Error handling**: Custom exceptions with clear error messages
- **CLI interface**: Command-line tool with helpful options

## Installation

1. Clone or download the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface

```bash
# Basic usage
python import_dji_srt_file_refactored.py flight_data.srt

# Save to CSV file
python import_dji_srt_file_refactored.py flight_data.srt --output parsed_data.csv

# Enable verbose logging
python import_dji_srt_file_refactored.py flight_data.srt --output parsed_data.csv --verbose
```

### Python API

```python
from import_dji_srt_file_refactored import parse_srt_records

# Parse SRT file to DataFrame
df = parse_srt_records('flight_data.srt')

# Display results
print(df.head())
print(f"Parsed {len(df)} records")
```

### Custom Configuration

```python
from import_dji_srt_file_refactored import parse_srt_records, SRTConfig

# Create custom configuration
config = SRTConfig()

# Modify patterns if needed (for different SRT formats)
config.PATTERNS['custom_field'] = r'\[custom: ([^\]]+)\]'

# Parse with custom config
df = parse_srt_records('flight_data.srt', config=config)
```

## Output Format

The parser extracts the following fields from DJI SRT files:

| Column | Type | Description |
|--------|------|-------------|
| subtitle_num | int | Subtitle sequence number |
| start_time | str | Start timestamp (HH:MM:SS,mmm) |
| end_time | str | End timestamp (HH:MM:SS,mmm) |
| frame_cnt | int | Frame count |
| diff_time_ms | int | Time difference in milliseconds |
| timestamp | datetime | Recording timestamp |
| iso | int | ISO sensitivity |
| shutter | str | Shutter speed |
| fnum | float | F-number (aperture) |
| ev | float | Exposure value |
| color_mode | str | Color mode |
| focal_length | float | Focal length in mm |
| latitude | float | GPS latitude |
| longitude | float | GPS longitude |
| relative_altitude | float | Relative altitude in meters |
| absolute_altitude | float | Absolute altitude in meters |
| ct | int | Color temperature |

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
python -m pytest test_import_dji_srt_file.py -v

# Run with coverage report
python -m pytest test_import_dji_srt_file.py --cov=import_dji_srt_file_refactored --cov-report=html

# Run specific test class
python -m pytest test_import_dji_srt_file.py::TestSRTValidation -v
```

## Architecture

The refactored solution follows these design principles:

### Modular Functions
- `validate_srt_file()`: File validation with comprehensive checks
- `split_srt_content()`: Content splitting into subtitle blocks
- `clean_html_content()`: HTML tag removal
- `extract_parameters()`: Parameter extraction using configurable patterns
- `parse_subtitle_block()`: Single block parsing logic
- `create_dataframe()`: DataFrame creation and column management

### Configuration Management
- `SRTConfig` dataclass for centralized configuration
- Regex patterns dictionary for easy customization
- Type converters for automatic data type handling
- Output column definitions for consistent formatting

### Error Handling
- Custom exception classes for specific error types
- Descriptive error messages for debugging
- Graceful handling of malformed data
- Comprehensive logging throughout the pipeline

### Type Safety
- Full type hints for all function parameters and returns
- Union types for flexible input handling
- Optional types for nullable values
- Generic types for container types

## Comparison with Original

### Improvements

1. **Maintainability**: Reduced function complexity from 130+ lines to focused functions
2. **Testability**: Comprehensive test suite with 95%+ coverage
3. **Readability**: Clear separation of concerns and descriptive naming
4. **Extensibility**: Configuration-driven approach for easy customization
5. **Reliability**: Robust error handling and validation
6. **Performance**: Optimized regex compilation and efficient parsing
7. **Documentation**: Complete docstrings and type hints

### Key Fixes

- **Altitude Parsing**: Fixed regex pattern to handle combined altitude format `[rel_alt: X.XXX abs_alt: Y.YYY]`
- **Error Recovery**: Graceful handling of malformed blocks
- **Type Safety**: Proper type conversion with error handling
- **Memory Efficiency**: Streaming processing for large files

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Requirements

- Python 3.7+
- pandas >= 1.5.0
- numpy >= 1.21.0
- pytest >= 7.0.0 (for testing)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### v2.0.0 (Refactored)
- Complete rewrite with modular architecture
- Added comprehensive test suite
- Implemented type hints throughout
- Added configuration management
- Fixed altitude parsing bug
- Enhanced error handling and logging
- Added CLI improvements

### v1.0.0 (Original)
- Basic SRT parsing functionality
- Single monolithic function
- Limited error handling
