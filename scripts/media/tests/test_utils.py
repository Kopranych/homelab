#!/usr/bin/env python3
"""Tests for photo consolidation utilities using should/when pattern."""

import sys
import tempfile
from pathlib import Path
from photo_consolidator.utils import calculate_sha256, format_bytes, is_media_file, ensure_directory, create_manifest_entry, get_relative_path


def test_should_calculate_sha256_hash_when_file_provided():
    """Should calculate correct SHA256 hash when valid file is provided."""

    # When calculating hash of a file with known content
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        test_content = "Hello, World!"
        f.write(test_content)
        temp_file = Path(f.name)
    
    try:
        # Should calculate hash
        file_hash = calculate_sha256(temp_file)
        
        # Should return valid hash string
        assert isinstance(file_hash, str), "Hash should be a string"
        assert len(file_hash) == 64, "SHA256 hash should be 64 characters"
        assert file_hash.isalnum(), "Hash should contain only alphanumeric characters"
        
        # Should be consistent
        second_hash = calculate_sha256(temp_file)
        assert file_hash == second_hash, "Hash should be consistent"
        
        print(f"✅ SHA256 hash calculated: {file_hash[:16]}...")
        
    finally:
        temp_file.unlink()

def test_should_format_bytes_as_human_readable_when_size_provided():
    """Should format bytes as human-readable string when size is provided."""

    # When formatting different byte sizes
    test_cases = [
        (0, "0B"),
        (500, "500.0B"),
        (1024, "1.0KB"),
        (1024 * 1024, "1.0MB"),
        (1024 * 1024 * 1024, "1.0GB"),
        (1536, "1.5KB"),  # 1.5 * 1024
        (2048 * 1024 * 1024, "2.0GB")  # 2GB
    ]
    
    for byte_value, expected_format in test_cases:
        # Should format correctly
        result = format_bytes(byte_value)
        assert isinstance(result, str), f"Result should be string for {byte_value}"
        assert result == expected_format, f"Expected {expected_format}, got {result} for {byte_value}"
    
    print("✅ Byte formatting works correctly for all test cases")

def test_should_detect_media_files_when_supported_extensions_provided():
    """Should detect media files when supported extensions are provided."""

    # When checking different file types
    extensions = ['jpg', 'png', 'mp4', 'mov']
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files
        media_files = [
            temp_path / "photo.jpg",
            temp_path / "image.PNG",  # Test case insensitivity
            temp_path / "video.mp4",
            temp_path / "movie.MOV"   # Test case insensitivity
        ]
        
        non_media_files = [
            temp_path / "document.txt",
            temp_path / "archive.zip",
            temp_path / "script.py"
        ]
        
        # Create the files
        for file_path in media_files + non_media_files:
            file_path.touch()
        
        # Should detect media files
        for media_file in media_files:
            assert is_media_file(media_file, extensions), f"{media_file.name} should be detected as media"
        
        # Should not detect non-media files
        for non_media_file in non_media_files:
            assert not is_media_file(non_media_file, extensions), f"{non_media_file.name} should not be detected as media"
    
    print("✅ Media file detection works correctly")

def test_should_ensure_directory_exists_when_path_provided():
    """Should ensure directory exists when path is provided."""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # When ensuring a new directory
        new_dir = temp_path / "new" / "nested" / "directory"
        assert not new_dir.exists(), "Directory should not exist initially"
        
        # Should create directory
        result = ensure_directory(new_dir)
        assert result is True, "Function should return True on success"
        assert new_dir.exists(), "Directory should exist after creation"
        assert new_dir.is_dir(), "Path should be a directory"
        
        # When ensuring existing directory
        result2 = ensure_directory(new_dir)
        assert result2 is True, "Function should return True for existing directory"
    
    print("✅ Directory creation works correctly")

def test_should_get_relative_path_when_base_path_provided():
    """Should get relative path when base path is provided."""

    # When getting relative paths
    base_path = Path("/data/incoming")
    
    test_cases = [
        (Path("/data/incoming/sdb1/photos/image.jpg"), Path("sdb1/photos/image.jpg")),
        (Path("/data/incoming/photo.jpg"), Path("photo.jpg")),
        (Path("/data/incoming/folder/subfolder/video.mp4"), Path("folder/subfolder/video.mp4"))
    ]
    
    for full_path, expected_relative in test_cases:
        # Should calculate correct relative path
        relative_path = get_relative_path(full_path, base_path)
        assert relative_path == expected_relative, f"Expected {expected_relative}, got {relative_path}"
    
    print("✅ Relative path calculation works correctly")

def test_should_create_manifest_entry_when_file_provided():
    """Should create manifest entry when file is provided."""

    # When creating manifest entry for a file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        test_content = "Test file content"
        f.write(test_content)
        temp_file = Path(f.name)
    
    try:
        # Should create manifest entry
        entry = create_manifest_entry(temp_file)
        
        # Should contain required fields
        assert isinstance(entry, dict), "Entry should be a dictionary"
        assert 'path' in entry, "Entry should contain path"
        assert 'size' in entry, "Entry should contain size"
        assert 'hash' in entry, "Entry should contain hash"
        assert 'modified' in entry, "Entry should contain modified time"
        
        # Should have correct values
        assert entry['path'] == str(temp_file), "Path should match file path"
        assert entry['size'] > 0, "Size should be greater than 0"
        assert len(entry['hash']) == 64, "Hash should be SHA256 (64 chars)"
        assert isinstance(entry['modified'], float), "Modified time should be float"
        
        print(f"✅ Manifest entry created with hash {entry['hash'][:16]}...")
        
    finally:
        temp_file.unlink()