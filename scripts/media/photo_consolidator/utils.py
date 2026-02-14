"""Utility functions for photo consolidation."""

import os
import hashlib
import json
import shutil
import subprocess
import psutil
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional, Tuple, List
import logging

try:
    import exifread
except ImportError:
    exifread = None

logger = logging.getLogger(__name__)


def calculate_sha256(file_path: Path, chunk_size: int = 8192) -> str:
    """
    Calculate SHA256 hash of a file.
    
    Args:
        file_path: Path to file
        chunk_size: Size of chunks to read at a time
        
    Returns:
        SHA256 hash as hexadecimal string
    """
    hasher = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Failed to calculate hash for {file_path}: {e}")
        return ""


def get_file_size(file_path: Path) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes, 0 if error
    """
    try:
        return file_path.stat().st_size
    except Exception as e:
        logger.error(f"Failed to get size for {file_path}: {e}")
        return 0


def format_bytes(bytes_value: int) -> str:
    """
    Format bytes as human-readable string.
    
    Args:
        bytes_value: Size in bytes
        
    Returns:
        Formatted string like "1.2GB"
    """
    if bytes_value == 0:
        return "0B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(bytes_value)
    
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    return f"{size:.1f}{units[unit_index]}"


def get_available_space(path: Path) -> int:
    """
    Get available disk space for a path in bytes.
    
    Args:
        path: Path to check
        
    Returns:
        Available space in bytes
    """
    try:
        usage = psutil.disk_usage(str(path))
        return usage.free
    except Exception as e:
        logger.error(f"Failed to get disk space for {path}: {e}")
        return 0


def ensure_directory(path: Path) -> bool:
    """
    Ensure directory exists, creating it if necessary.
    
    Args:
        path: Directory path to ensure
        
    Returns:
        True if directory exists or was created successfully
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return False


def safe_copy_file(source: Path, destination: Path, verify: bool = True) -> bool:
    """
    Safely copy a file with optional verification.
    
    Args:
        source: Source file path
        destination: Destination file path  
        verify: Whether to verify copy with hash comparison
        
    Returns:
        True if copy was successful
    """
    try:
        # Ensure destination directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        shutil.copy2(source, destination)
        
        # Verify copy if requested
        if verify:
            source_hash = calculate_sha256(source)
            dest_hash = calculate_sha256(destination)
            if source_hash != dest_hash:
                logger.error(f"Hash verification failed for {source} -> {destination}")
                return False
        
        logger.debug(f"Successfully copied {source} -> {destination}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to copy {source} -> {destination}: {e}")
        return False


def is_media_file(file_path: Path, supported_extensions: List[str]) -> bool:
    """
    Check if file is a supported media file.
    
    Args:
        file_path: Path to file
        supported_extensions: List of supported extensions (without dots)
        
    Returns:
        True if file is supported media type
    """
    if not file_path.is_file():
        return False
    
    extension = file_path.suffix.lower().lstrip('.')
    return extension in [ext.lower() for ext in supported_extensions]


def find_media_files(directory: Path, supported_extensions: List[str]) -> Generator[Path, None, None]:
    """
    Recursively find all media files in a directory.
    
    Args:
        directory: Directory to search
        supported_extensions: List of supported file extensions
        
    Yields:
        Path objects for media files found
    """
    if not directory.exists() or not directory.is_dir():
        logger.warning(f"Directory does not exist or is not a directory: {directory}")
        return
    
    try:
        for file_path in directory.rglob('*'):
            if is_media_file(file_path, supported_extensions):
                yield file_path
    except Exception as e:
        logger.error(f"Error scanning directory {directory}: {e}")


def get_relative_path(file_path: Path, base_path: Path) -> Path:
    """
    Get relative path from base path.
    
    Args:
        file_path: Full file path
        base_path: Base path to make relative to
        
    Returns:
        Relative path
    """
    try:
        return file_path.relative_to(base_path)
    except ValueError:
        # If paths don't have common base, return the file name
        return Path(file_path.name)


def create_manifest_entry(file_path: Path, base_path: Optional[Path] = None) -> dict:
    """
    Create manifest entry for a file.
    
    Args:
        file_path: Path to file
        base_path: Base path for relative path calculation
        
    Returns:
        Dictionary with file information
    """
    try:
        stat = file_path.stat()
        
        entry = {
            'path': str(file_path),
            'relative_path': str(get_relative_path(file_path, base_path) if base_path else file_path),
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'hash': calculate_sha256(file_path)
        }
        
        return entry
        
    except Exception as e:
        logger.error(f"Failed to create manifest entry for {file_path}: {e}")
        return {
            'path': str(file_path),
            'error': str(e)
        }


def validate_file_integrity(file_path: Path, expected_hash: str) -> bool:
    """
    Validate file integrity against expected hash.
    
    Args:
        file_path: Path to file
        expected_hash: Expected SHA256 hash
        
    Returns:
        True if hash matches
    """
    if not file_path.exists():
        logger.error(f"File does not exist for validation: {file_path}")
        return False
    
    actual_hash = calculate_sha256(file_path)
    if actual_hash != expected_hash:
        logger.error(f"Hash mismatch for {file_path}: expected {expected_hash}, got {actual_hash}")
        return False
    
    return True


def cleanup_empty_directories(directory: Path) -> int:
    """
    Remove empty directories recursively.
    
    Args:
        directory: Root directory to clean up
        
    Returns:
        Number of directories removed
    """
    removed_count = 0
    
    try:
        # Walk bottom-up to remove empty directories
        for dirpath, dirnames, filenames in os.walk(str(directory), topdown=False):
            dir_path = Path(dirpath)
            
            # Skip if directory has files
            if filenames:
                continue
                
            # Skip if directory has subdirectories (that weren't empty)
            if any(Path(dir_path / dirname).exists() for dirname in dirnames):
                continue
            
            # Remove empty directory
            try:
                dir_path.rmdir()
                logger.debug(f"Removed empty directory: {dir_path}")
                removed_count += 1
            except OSError as e:
                logger.debug(f"Could not remove directory {dir_path}: {e}")
    
    except Exception as e:
        logger.error(f"Error cleaning up directories in {directory}: {e}")
    
    return removed_count


def extract_photo_date(file_path: Path) -> Optional[Tuple[int, int]]:
    """
    Extract photo/video date from EXIF metadata.

    Args:
        file_path: Path to media file

    Returns:
        Tuple of (year, month) or None if no date found
    """
    ext = file_path.suffix.lower().lstrip('.')

    # Try EXIF for image files
    if ext in ('jpg', 'jpeg', 'tiff', 'tif', 'cr2', 'nef', 'arw', 'dng',
               'raf', 'orf', 'rw2', 'pef', 'srw', 'x3f', 'heic', 'heif', 'png'):
        result = _extract_exif_date(file_path)
        if result:
            return result

    # Try ffprobe for video files
    if ext in ('mp4', 'mov', 'avi', 'mkv', 'mts', '3gp'):
        result = _extract_video_date(file_path)
        if result:
            return result

    return None


def _extract_exif_date(file_path: Path) -> Optional[Tuple[int, int]]:
    """Extract date from EXIF tags using exifread."""
    if exifread is None:
        return None
    try:
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f, stop_tag='DateTimeDigitized', details=False)

        for tag_name in ('EXIF DateTimeOriginal', 'EXIF DateTimeDigitized', 'Image DateTime'):
            tag = tags.get(tag_name)
            if tag:
                # Format: "2020:07:28 11:49:03"
                date_str = str(tag).strip()
                if len(date_str) >= 7 and date_str[4] == ':':
                    year = int(date_str[:4])
                    month = int(date_str[5:7])
                    if 1900 <= year <= 2100 and 1 <= month <= 12:
                        return (year, month)
    except Exception as e:
        logger.debug(f"Could not read EXIF from {file_path}: {e}")
    return None


def _extract_video_date(file_path: Path) -> Optional[Tuple[int, int]]:
    """Extract creation date from video using ffprobe."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json',
             '-show_entries', 'format_tags=creation_time', str(file_path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            creation_time = data.get('format', {}).get('tags', {}).get('creation_time', '')
            if creation_time and len(creation_time) >= 7:
                # Format: "2020-07-28T11:49:03.000000Z"
                year = int(creation_time[:4])
                month = int(creation_time[5:7])
                if 1900 <= year <= 2100 and 1 <= month <= 12:
                    return (year, month)
    except Exception as e:
        logger.debug(f"Could not read video date from {file_path}: {e}")
    return None


def get_current_timestamp():
    """Get current timestamp as ISO string."""
    return datetime.now().isoformat()