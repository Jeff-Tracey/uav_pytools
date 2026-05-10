"""
Test suite for the refactored DJI SRT parser.

This module contains unit tests for all components of the SRT parser,
demonstrating research software engineering best practices for testing.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
import pandas as pd


from import_dji_srt_file import (
    SRTConfig,
    SRTValidationError,
    SRTParsingError,
    find_srt_files,
    parse_srt_records_with_filename,
    process_directory_to_combined_dataframe,
    validate_srt_file,
    split_srt_content,
    clean_html_content,
    extract_parameters,
    parse_subtitle_block,
    create_dataframe,
    parse_srt_records
)


class TestSRTConfig:
    """Test the SRTConfig class."""
    
    def test_config_has_required_attributes(self):
        """Test that config has all required attributes."""
        config = SRTConfig()
        assert hasattr(config, 'PATTERNS')
        assert hasattr(config, 'OUTPUT_COLUMNS')
        assert hasattr(config, 'TYPE_CONVERTERS')
        
    def test_patterns_dict_structure(self):
        """Test that patterns dictionary has expected keys."""
        config = SRTConfig()
        expected_keys = {
            'frame_cnt', 'diff_time', 'timestamp', 'iso', 'shutter',
            'fnum', 'ev', 'color_md', 'focal_len', 'latitude',
            'longitude', 'altitude', 'ct'
        }
        assert set(config.PATTERNS.keys()) == expected_keys


class TestSRTValidation:
    """Test SRT file validation functions."""
    
    def test_validate_srt_file_with_valid_file(self):
        """Test validation with a valid SRT file."""
        with tempfile.NamedTemporaryFile(suffix='.srt', mode='w', delete=False) as f:
            f.write("Test content")
            temp_path = Path(f.name)
        
        try:
            result = validate_srt_file(temp_path)
            assert result == temp_path
        finally:
            temp_path.unlink()
    
    def test_validate_srt_file_wrong_extension(self):
        """Test validation fails with wrong file extension."""
        with tempfile.NamedTemporaryFile(suffix='.txt', mode='w', delete=False) as f:
            f.write("Test content")
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(SRTValidationError, match="File must have .srt extension"):
                validate_srt_file(temp_path)
        finally:
            temp_path.unlink()
    
    def test_validate_srt_file_nonexistent(self):
        """Test validation fails with non-existent file."""
        fake_path = Path("/nonexistent/file.srt")
        with pytest.raises(SRTValidationError, match="File does not exist"):
            validate_srt_file(fake_path)
    
    def test_validate_srt_file_empty(self):
        """Test validation fails with empty file."""
        with tempfile.NamedTemporaryFile(suffix='.srt', mode='w', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(SRTValidationError, match="File is empty"):
                validate_srt_file(temp_path)
        finally:
            temp_path.unlink()


class TestContentProcessing:
    """Test content processing functions."""
    
    def test_split_srt_content(self):
        """Test splitting SRT content into blocks."""
        content = """1
00:00:00,000 --> 00:00:00,033
First subtitle

2
00:00:00,033 --> 00:00:00,066
Second subtitle"""
        
        blocks = split_srt_content(content)
        assert len(blocks) == 2
        assert "First subtitle" in blocks[0]
        assert "Second subtitle" in blocks[1]
    
    def test_clean_html_content(self):
        """Test HTML tag removal."""
        content = '<font size="28">FrameCnt: 1, DiffTime: 33ms</font>'
        cleaned = clean_html_content(content)
        assert cleaned == 'FrameCnt: 1, DiffTime: 33ms'
    
    def test_extract_parameters_basic(self):
        """Test parameter extraction with basic values."""
        content = '[iso: 190] [shutter: 1/60.0] [fnum: 1.8] [ev: 0]'
        config = SRTConfig()
        
        params = extract_parameters(content, config)
        
        assert params['iso'] == 190
        assert params['shutter'] == '1/60.0'
        assert params['fnum'] == 1.8
        assert params['ev'] == 0.0
    
    def test_extract_parameters_altitude(self):
        """Test altitude parameter extraction."""
        content = '[rel_alt: 18.000 abs_alt: 115.999]'
        config = SRTConfig()
        
        params = extract_parameters(content, config)
        
        assert params['rel_alt'] == 18.0
        assert params['abs_alt'] == 115.999
    
    def test_extract_parameters_missing_values(self):
        """Test parameter extraction with missing values."""
        content = '[iso: 190]'  # Only one parameter
        config = SRTConfig()
        
        params = extract_parameters(content, config)
        
        assert params['iso'] == 190
        assert params['fnum'] is None
        assert params['rel_alt'] is None
        assert params['abs_alt'] is None


class TestSubtitleParsing:
    """Test subtitle block parsing."""
    
    def test_parse_subtitle_block_complete(self):
        """Test parsing a complete subtitle block."""
        block = """1
00:00:00,000 --> 00:00:00,033
<font size="28">FrameCnt: 1, DiffTime: 33ms
2025-07-12 23:08:26.224
[iso: 190] [shutter: 1/60.0] [fnum: 1.8] [ev: 0] [color_md: dlog_m] [focal_len: 24.00] [latitude: 32.847151] [longitude: -117.016501] [rel_alt: 18.000 abs_alt: 115.999] [ct: 5378] </font>"""
        
        config = SRTConfig()
        record = parse_subtitle_block(block, config)
        
        assert record is not None
        assert record['subtitle_num'] == 1
        assert record['start_time'] == '00:00:00,000'
        assert record['end_time'] == '00:00:00,033'
        assert record['frame_cnt'] == 1
        assert record['diff_time_ms'] == 33
        assert record['iso'] == 190
        assert record['relative_altitude'] == 18.0
        assert record['absolute_altitude'] == 115.999
    
    def test_parse_subtitle_block_incomplete(self):
        """Test parsing an incomplete subtitle block."""
        block = """1
00:00:00,000 --> 00:00:00,033"""  # Missing content
        
        config = SRTConfig()
        record = parse_subtitle_block(block, config)
        
        assert record is None
    
    def test_parse_subtitle_block_malformed(self):
        """Test parsing a malformed subtitle block."""
        block = """not_a_number
00:00:00,000 --> 00:00:00,033
Some content"""
        
        config = SRTConfig()
        record = parse_subtitle_block(block, config)
        
        assert record is None


class TestDataFrameCreation:
    """Test DataFrame creation and processing."""
    
    def test_create_dataframe_with_records(self):
        """Test DataFrame creation with valid records."""
        # Generate test data dynamically
        import random
        
        test_subtitle_num = random.randint(1, 1000)
        test_altitude = round(random.uniform(0, 500), 3)
        
        test_records = [
            {
                'subtitle_num': test_subtitle_num,
                'start_time': '00:01:23,456',
                'end_time': '00:01:23,789',
                'frame_cnt': random.randint(1, 10000),
                'relative_altitude': test_altitude,
                'absolute_altitude': test_altitude + random.uniform(50, 200)
            }
        ]
        
        config = SRTConfig()
        df = create_dataframe(test_records, config)
        
        # Test that the function preserves input data
        for i, record in enumerate(test_records):
            for key, expected_value in record.items():
                actual_value = df.iloc[i][key]
                assert actual_value == expected_value, f"Value for {key} should be preserved"
        
        # Test structural properties
        assert len(df) == len(test_records)
        assert set(df.columns) == set(config.OUTPUT_COLUMNS)
    
    def test_create_dataframe_empty_records(self):
        """Test DataFrame creation with empty records."""
        config = SRTConfig()
        df = create_dataframe([], config)
        
        assert len(df) == 0
        assert list(df.columns) == config.OUTPUT_COLUMNS
    
    def test_create_dataframe_missing_columns(self):
        """Test DataFrame creation ensures all columns are present."""
        records = [{'subtitle_num': 1}]  # Only one column
        
        config = SRTConfig()
        df = create_dataframe(records, config)
        
        assert len(df.columns) == len(config.OUTPUT_COLUMNS)
        assert all(col in df.columns for col in config.OUTPUT_COLUMNS)


class TestIntegration:
    """Integration tests for the complete parsing process."""
    
    def test_parse_srt_records_integration(self):
        """Test the complete parsing workflow with property-based assertions."""
        srt_content = """1
00:00:00,000 --> 00:00:00,033
<font size="28">FrameCnt: 1, DiffTime: 33ms
2025-07-12 23:08:26.224
[iso: 190] [shutter: 1/60.0] [fnum: 1.8] [ev: 0] [color_md: dlog_m] [focal_len: 24.00] [latitude: 32.847151] [longitude: -117.016501] [rel_alt: 18.000 abs_alt: 115.999] [ct: 5378] </font>

2
00:00:00,033 --> 00:00:00,066
<font size="28">FrameCnt: 2, DiffTime: 33ms
2025-07-12 23:08:26.258
[iso: 190] [shutter: 1/60.0] [fnum: 1.8] [ev: 0] [color_md: dlog_m] [focal_len: 24.00] [latitude: 32.847151] [longitude: -117.016501] [rel_alt: 18.000 abs_alt: 115.999] [ct: 5379] </font>"""
        
        with tempfile.NamedTemporaryFile(suffix='.srt', mode='w', delete=False) as f:
            f.write(srt_content)
            temp_path = Path(f.name)
        
        try:
            df = parse_srt_records(temp_path)
            
            # Test structural properties instead of exact values
            assert len(df) == 2, "Should parse exactly 2 records"
            assert not df.empty, "DataFrame should not be empty"
            
            # Test that all expected columns are present
            config = SRTConfig()
            assert list(df.columns) == config.OUTPUT_COLUMNS, "All expected columns should be present"
            
            # Test data type consistency
            assert df['subtitle_num'].dtype in ['int64', 'Int64'], "subtitle_num should be integer"
            assert df['frame_cnt'].dtype in ['int64', 'Int64'], "frame_cnt should be integer"
            assert df['relative_altitude'].dtype in ['float64', 'Float64'], "altitude should be float"
            
            # Test logical relationships
            assert df['subtitle_num'].is_monotonic_increasing, "Subtitle numbers should increase"
            assert (df['frame_cnt'] > 0).all(), "Frame count should be positive"
            assert df['relative_altitude'].notna().all(), "Altitude should not be null"
            assert df['absolute_altitude'].notna().all(), "Absolute altitude should not be null"
            
            # Test that timestamps are parseable
            assert df['start_time'].str.match(r'\d{2}:\d{2}:\d{2},\d{3}').all(), "Start time format should be valid"
            assert df['end_time'].str.match(r'\d{2}:\d{2}:\d{2},\d{3}').all(), "End time format should be valid"
            
            # Test that camera parameters are reasonable ranges
            if df['iso'].notna().any():
                assert (df['iso'] >= 50).all() and (df['iso'] <= 6400).all(), "ISO should be in reasonable range"
            
            if df['relative_altitude'].notna().any():
                assert (df['relative_altitude'] >= 0).all(), "Relative altitude should be non-negative"
                
        finally:
            temp_path.unlink()


class TestBatchProcessing:
    """Test batch processing functionality."""
    
    def test_find_srt_files(self):
        """Test finding SRT files in directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test SRT files
            (temp_path / "flight1.srt").write_text(SAMPLE_SRT_BLOCK)
            (temp_path / "flight2.SRT").write_text(SAMPLE_SRT_BLOCK)
            (temp_path / "other.txt").write_text("not an srt file")
            
            # Create subdirectory with SRT file
            sub_dir = temp_path / "subdir"
            sub_dir.mkdir()
            (sub_dir / "flight3.srt").write_text(SAMPLE_SRT_BLOCK)
            
            # Test non-recursive
            files = find_srt_files(temp_path, recursive=False)
            assert len(files) == 2
            assert all(f.suffix.lower() == '.srt' for f in files)
            
            # Test recursive
            files = find_srt_files(temp_path, recursive=True)
            assert len(files) == 3
    
    def test_parse_srt_records_with_filename(self):
        """Test parsing SRT with filename column added."""
        with tempfile.NamedTemporaryFile(suffix='.srt', mode='w', delete=False) as f:
            f.write(SAMPLE_SRT_BLOCK)
            temp_path = Path(f.name)
        
        try:
            df = parse_srt_records_with_filename(temp_path)
            
            # Check that source_file column exists and is correct
            assert 'source_file' in df.columns
            assert df['source_file'].iloc[0] == temp_path.name
            assert df.columns[0] == 'source_file'  # Should be first column
            
        finally:
            temp_path.unlink()
    
    def test_process_directory_to_combined_dataframe(self):
        """Test processing directory and combining DataFrames."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create multiple SRT files
            for i in range(3):
                srt_content = SAMPLE_SRT_BLOCK.replace("FrameCnt: 1", f"FrameCnt: {i+1}")
                (temp_path / f"flight{i+1}.srt").write_text(srt_content)
            
            # Process directory
            combined_df = process_directory_to_combined_dataframe(temp_path)
            
            # Should have 3 records (one from each file)
            assert len(combined_df) == 3
            assert 'source_file' in combined_df.columns
            assert combined_df['source_file'].nunique() == 3  # 3 different files
            
            # Check that frame counts are different (1, 2, 3)
            assert set(combined_df['frame_cnt'].unique()) == {1, 2, 3}
    
    def test_process_directory_empty(self):
        """Test processing empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            with pytest.raises(SRTValidationError, match="No SRT files found"):
                process_directory_to_combined_dataframe(temp_path)

# Sample data for testing
SAMPLE_SRT_BLOCK = """1
00:00:00,000 --> 00:00:00,033
<font size="28">FrameCnt: 1, DiffTime: 33ms
2025-07-12 23:08:26.224
[iso: 190] [shutter: 1/60.0] [fnum: 1.8] [ev: 0] [color_md: dlog_m] [focal_len: 24.00] [latitude: 32.847151] [longitude: -117.016501] [rel_alt: 18.000 abs_alt: 115.999] [ct: 5378] </font>"""


if __name__ == "__main__":
    # Run tests when script is executed directly
    pytest.main([__file__, "-v"])
