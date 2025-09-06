"""Photo scanning and manifest generation."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Generator, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from .config import Config
from .utils import (
    find_media_files, 
    create_manifest_entry, 
    ensure_directory, 
    format_bytes,
    get_available_space,
    safe_copy_file
)

logger = logging.getLogger(__name__)


class PhotoScanner:
    """Scans directories for photos and creates manifests."""
    
    def __init__(self, config: Config):
        """
        Initialize scanner with configuration.
        
        Args:
            config: Configuration instance
        """
        self.config = config
        self.data_root = Path(config.get_data_root())
        self.manifests_dir = self.data_root / "manifests"
        self.supported_extensions = self._get_all_supported_extensions()
        
        # Ensure directories exist
        ensure_directory(self.manifests_dir)
    
    def _get_all_supported_extensions(self) -> List[str]:
        """Get all supported file extensions."""
        extensions = self.config.get_supported_extensions()
        all_extensions = []
        all_extensions.extend(extensions.get('photos', []))
        all_extensions.extend(extensions.get('videos', []))
        return [ext.lower() for ext in all_extensions]
    
    def scan_source_drives(self, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Scan all configured source drives and create manifests.
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with scan results and statistics
        """
        source_drives = self.config.get_source_drives()
        if not source_drives:
            raise ValueError("No source drives configured")
        
        logger.info(f"Starting scan of {len(source_drives)} source drives")
        
        results = {
            'drives_scanned': 0,
            'total_files': 0,
            'total_size': 0,
            'manifests': {},
            'errors': []
        }
        
        for drive_path in source_drives:
            drive = Path(drive_path)
            if not drive.exists():
                error_msg = f"Source drive not found: {drive_path}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
                continue
            
            logger.info(f"Scanning drive: {drive_path}")
            
            try:
                drive_result = self._scan_drive(drive, progress_callback)
                results['drives_scanned'] += 1
                results['total_files'] += drive_result['file_count']
                results['total_size'] += drive_result['total_size']
                results['manifests'][drive_path] = drive_result['manifest_file']
                
                logger.info(f"Completed scanning {drive_path}: "
                          f"{drive_result['file_count']} files, "
                          f"{format_bytes(drive_result['total_size'])}")
                
            except Exception as e:
                error_msg = f"Failed to scan drive {drive_path}: {e}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
        
        logger.info(f"Scan complete: {results['total_files']} files, "
                   f"{format_bytes(results['total_size'])}")
        
        return results
    
    def _scan_drive(self, drive_path: Path, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Scan a single drive for media files.
        
        Args:
            drive_path: Path to drive to scan
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with scan results
        """
        drive_name = drive_path.name
        manifest_file = self.manifests_dir / f"{drive_name}_original_manifest.json"
        
        logger.info(f"Scanning drive {drive_path} -> {manifest_file}")
        
        # Find all media files
        media_files = list(find_media_files(drive_path, self.supported_extensions))
        total_files = len(media_files)
        
        if total_files == 0:
            logger.warning(f"No media files found in {drive_path}")
            return {
                'file_count': 0,
                'total_size': 0,
                'manifest_file': str(manifest_file)
            }
        
        logger.info(f"Found {total_files} media files in {drive_path}")
        
        # Create manifest entries with progress bar
        manifest_entries = []
        total_size = 0
        
        with tqdm(total=total_files, desc=f"Processing {drive_name}", unit="files") as pbar:
            # Use parallel processing for better performance
            parallel_jobs = min(self.config.get_parallel_jobs(), total_files)
            
            with ThreadPoolExecutor(max_workers=parallel_jobs) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(create_manifest_entry, file_path, drive_path): file_path 
                    for file_path in media_files
                }
                
                # Process completed tasks
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        entry = future.result()
                        if 'error' not in entry:
                            manifest_entries.append(entry)
                            total_size += entry['size']
                        else:
                            logger.error(f"Failed to process {file_path}: {entry['error']}")
                    except Exception as e:
                        logger.error(f"Exception processing {file_path}: {e}")
                    
                    pbar.update(1)
                    if progress_callback:
                        progress_callback(len(manifest_entries), total_files)
        
        # Create manifest
        manifest = {
            'drive_path': str(drive_path),
            'drive_name': drive_name,
            'scan_timestamp': get_current_timestamp(),
            'total_files': len(manifest_entries),
            'total_size': total_size,
            'files': manifest_entries
        }
        
        # Save manifest
        try:
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2, default=str)
            logger.info(f"Saved manifest: {manifest_file}")
        except Exception as e:
            logger.error(f"Failed to save manifest {manifest_file}: {e}")
            raise
        
        return {
            'file_count': len(manifest_entries),
            'total_size': total_size,
            'manifest_file': str(manifest_file)
        }
    
    def copy_media_files(self, target_dir: Optional[str] = None, 
                        dry_run: Optional[bool] = None,
                        progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Copy media files from source drives to target directory.
        
        Args:
            target_dir: Target directory (defaults to /data/incoming)
            dry_run: Whether to perform dry run (defaults to config setting)  
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with copy results and statistics
        """
        if target_dir is None:
            target_dir = str(self.data_root / "incoming")
        
        if dry_run is None:
            dry_run = self.config.is_dry_run()
        
        target_path = Path(target_dir)
        
        # Check available space
        min_space_gb = self.config.get_min_free_space_gb()
        available_space = get_available_space(target_path.parent)
        min_space_bytes = min_space_gb * 1024 * 1024 * 1024
        
        if available_space < min_space_bytes:
            raise ValueError(f"Insufficient space: {format_bytes(available_space)} available, "
                           f"need at least {format_bytes(min_space_bytes)}")
        
        logger.info(f"{'DRY RUN: ' if dry_run else ''}Starting copy operation to {target_path}")
        
        # Load manifests
        manifests = self._load_manifests()
        if not manifests:
            raise ValueError("No manifests found. Run scan first.")
        
        results = {
            'copied_files': 0,
            'copied_size': 0,
            'failed_files': 0,
            'errors': [],
            'dry_run': dry_run
        }
        
        # Calculate totals for progress bar
        total_files = sum(len(manifest['files']) for manifest in manifests.values())
        total_size = sum(manifest['total_size'] for manifest in manifests.values())
        
        logger.info(f"{'DRY RUN: ' if dry_run else ''}Copying {total_files} files "
                   f"({format_bytes(total_size)})")
        
        with tqdm(total=total_files, desc="Copying files", unit="files") as pbar:
            for drive_path, manifest in manifests.items():
                drive_name = Path(drive_path).name
                drive_target_dir = target_path / drive_name
                
                if not dry_run:
                    ensure_directory(drive_target_dir)
                
                for file_entry in manifest['files']:
                    source_file = Path(file_entry['path'])
                    relative_path = Path(file_entry['relative_path'])
                    target_file = drive_target_dir / relative_path
                    
                    try:
                        if dry_run:
                            logger.debug(f"DRY RUN: Would copy {source_file} -> {target_file}")
                        else:
                            # Ensure target directory exists
                            ensure_directory(target_file.parent)
                            
                            # Copy file with verification
                            success = safe_copy_file(source_file, target_file, verify=True)
                            if not success:
                                results['failed_files'] += 1
                                continue
                        
                        results['copied_files'] += 1
                        results['copied_size'] += file_entry['size']
                        
                    except Exception as e:
                        error_msg = f"Failed to copy {source_file}: {e}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                        results['failed_files'] += 1
                    
                    pbar.update(1)
                    if progress_callback:
                        progress_callback(results['copied_files'], total_files)
        
        logger.info(f"{'DRY RUN: ' if dry_run else ''}Copy complete: "
                   f"{results['copied_files']} files copied, "
                   f"{results['failed_files']} failed")
        
        return results
    
    def _load_manifests(self) -> Dict[str, Dict[str, Any]]:
        """Load all available manifests."""
        manifests = {}
        
        for manifest_file in self.manifests_dir.glob("*_original_manifest.json"):
            try:
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
                    drive_path = manifest['drive_path']
                    manifests[drive_path] = manifest
                    logger.debug(f"Loaded manifest: {manifest_file}")
            except Exception as e:
                logger.error(f"Failed to load manifest {manifest_file}: {e}")
        
        return manifests
    
    def create_copied_manifest(self, source_dir: Optional[str] = None) -> str:
        """
        Create manifest of copied files.
        
        Args:
            source_dir: Directory to scan (defaults to /data/incoming)
            
        Returns:
            Path to created manifest file
        """
        if source_dir is None:
            source_dir = str(self.data_root / "incoming")
        
        source_path = Path(source_dir)
        if not source_path.exists():
            raise ValueError(f"Source directory does not exist: {source_path}")
        
        manifest_file = self.manifests_dir / "copied_files_combined.json"
        
        logger.info(f"Creating manifest of copied files: {manifest_file}")
        
        # Find all media files in the copied directory
        media_files = list(find_media_files(source_path, self.supported_extensions))
        total_files = len(media_files)
        
        if total_files == 0:
            logger.warning(f"No media files found in {source_path}")
            return str(manifest_file)
        
        logger.info(f"Found {total_files} copied files")
        
        # Create manifest entries
        manifest_entries = []
        total_size = 0
        
        with tqdm(total=total_files, desc="Analyzing copied files", unit="files") as pbar:
            parallel_jobs = min(self.config.get_parallel_jobs(), total_files)
            
            with ThreadPoolExecutor(max_workers=parallel_jobs) as executor:
                future_to_file = {
                    executor.submit(create_manifest_entry, file_path, source_path): file_path
                    for file_path in media_files
                }
                
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        entry = future.result()
                        if 'error' not in entry:
                            manifest_entries.append(entry)
                            total_size += entry['size']
                    except Exception as e:
                        logger.error(f"Exception processing {file_path}: {e}")
                    
                    pbar.update(1)
        
        # Create manifest
        manifest = {
            'source_directory': str(source_path),
            'scan_timestamp': get_current_timestamp(),
            'total_files': len(manifest_entries),
            'total_size': total_size,
            'files': manifest_entries
        }
        
        # Save manifest
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2, default=str)
        
        logger.info(f"Created copied files manifest: {total_files} files, "
                   f"{format_bytes(total_size)}")
        
        return str(manifest_file)


# Simple timestamp function without pandas dependency
from datetime import datetime

def get_current_timestamp():
    """Get current timestamp as ISO string."""
    return datetime.now().isoformat()