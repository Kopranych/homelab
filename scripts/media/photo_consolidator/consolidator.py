"""Photo consolidation and final processing."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from tqdm import tqdm

from .config import Config
from .duplicates import DuplicateGroup, FileInfo
from .utils import (
    ensure_directory, 
    safe_copy_file, 
    format_bytes, 
    cleanup_empty_directories,
    get_current_timestamp
)

logger = logging.getLogger(__name__)


@dataclass
class ConsolidationStats:
    """Statistics for consolidation process."""
    total_processed: int = 0
    files_kept: int = 0
    files_removed: int = 0
    space_saved: int = 0
    unique_files_copied: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class PhotoConsolidator:
    """Consolidates photos by removing duplicates and organizing files."""
    
    def __init__(self, config: Config):
        """
        Initialize consolidator with configuration.
        
        Args:
            config: Configuration instance
        """
        self.config = config
        self.data_root = Path(config.get_data_root())
        self.incoming_dir = self.data_root / "incoming"
        self.duplicates_dir = self.data_root / "duplicates"
        self.final_dir = self.data_root / "final"
        self.backup_dir = self.data_root / "backup" / "consolidation"
        self.manifests_dir = self.data_root / "manifests"
        
        # Ensure directories exist
        ensure_directory(self.final_dir)
        if self.config.should_backup_before_removal():
            ensure_directory(self.backup_dir)
    
    def consolidate_files(self, dry_run: Optional[bool] = None) -> Dict[str, Any]:
        """
        Consolidate files by removing duplicates and organizing.
        
        Args:
            dry_run: Whether to perform dry run (defaults to config setting)
            
        Returns:
            Dictionary with consolidation results
        """
        if dry_run is None:
            dry_run = self.config.is_dry_run()
        
        logger.info(f"{'DRY RUN: ' if dry_run else ''}Starting file consolidation")
        
        stats = ConsolidationStats()
        
        # Check prerequisites
        if not self.incoming_dir.exists():
            raise ValueError(f"Incoming directory not found: {self.incoming_dir}")
        
        # Process duplicate groups if analysis was done
        if self.duplicates_dir.exists() and (self.duplicates_dir / "groups").exists():
            logger.info("Processing duplicate groups")
            self._process_duplicate_groups(stats, dry_run)
        else:
            logger.warning("No duplicate analysis found, processing all files as unique")
        
        # Process unique files
        logger.info("Processing unique files")
        self._process_unique_files(stats, dry_run)
        
        # Generate final report
        report_data = self._generate_final_report(stats, dry_run)
        
        logger.info(f"{'DRY RUN: ' if dry_run else ''}Consolidation complete: "
                   f"{stats.files_kept} kept, {stats.files_removed} removed, "
                   f"{format_bytes(stats.space_saved)} saved")
        
        return report_data
    
    def _process_duplicate_groups(self, stats: ConsolidationStats, dry_run: bool):
        """Process duplicate groups according to quality rankings."""
        
        groups_dir = self.duplicates_dir / "groups"
        group_files = list(groups_dir.glob("group_*.txt"))
        
        if not group_files:
            logger.warning("No duplicate group files found")
            return
        
        logger.info(f"Processing {len(group_files)} duplicate groups")
        
        with tqdm(group_files, desc="Processing groups", unit="groups") as pbar:
            for group_file in pbar:
                try:
                    self._process_single_group(group_file, stats, dry_run)
                except Exception as e:
                    error_msg = f"Failed to process group {group_file}: {e}"
                    logger.error(error_msg)
                    stats.errors.append(error_msg)
                pbar.update()
    
    def _process_single_group(self, group_file: Path, stats: ConsolidationStats, dry_run: bool):
        """Process a single duplicate group."""
        
        # Parse group file to extract file paths and rankings
        files_to_remove = []
        best_file = None
        
        with open(group_file, 'r') as f:
            content = f.read()
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                
                # Find KEEP file (best quality)
                if 'KEEP' in line and 'Full:' in line:
                    path_start = line.find('Full: ') + 6
                    best_file = line[path_start:].strip()
                
                # Find REMOVE files
                elif 'REMOVE' in line and 'Full:' in line:
                    path_start = line.find('Full: ') + 6
                    remove_file = line[path_start:].strip()
                    files_to_remove.append(remove_file)
        
        if not best_file:
            logger.warning(f"No best file found in group {group_file}")
            return
        
        best_path = Path(best_file)
        if not best_path.exists():
            logger.error(f"Best file not found: {best_path}")
            return
        
        # Safety check - ensure file is in incoming directory
        if not str(best_path).startswith(str(self.incoming_dir)):
            logger.error(f"Safety violation: Best file not in incoming directory: {best_path}")
            return
        
        # Determine final destination path
        rel_path = best_path.relative_to(self.incoming_dir)
        # Remove source drive prefix (e.g., sdb1/, sdc1/)
        path_parts = rel_path.parts
        if len(path_parts) > 1:
            rel_path = Path(*path_parts[1:])  # Skip first part (drive name)
        
        dest_path = self.final_dir / rel_path
        
        # Copy best file to final location
        if dry_run:
            logger.debug(f"DRY RUN: Would copy {best_path} -> {dest_path}")
        else:
            if ensure_directory(dest_path.parent):
                if safe_copy_file(best_path, dest_path, verify=True):
                    logger.debug(f"Kept: {rel_path} (quality winner)")
                    stats.files_kept += 1
                else:
                    error_msg = f"Failed to copy best file: {best_path}"
                    logger.error(error_msg)
                    stats.errors.append(error_msg)
                    return
            else:
                error_msg = f"Failed to create directory for {dest_path}"
                logger.error(error_msg) 
                stats.errors.append(error_msg)
                return
        
        # Process files to remove
        if files_to_remove:
            self._handle_duplicate_removal(files_to_remove, group_file.stem, stats, dry_run)
        
        stats.total_processed += len(files_to_remove) + 1
    
    def _handle_duplicate_removal(self, files_to_remove: List[str], group_name: str,
                                 stats: ConsolidationStats, dry_run: bool):
        """Handle removal of duplicate files with optional backup."""
        
        # Backup files if configured
        if self.config.should_backup_before_removal() and not dry_run:
            group_backup_dir = self.backup_dir / group_name
            ensure_directory(group_backup_dir)
            
            logger.debug(f"Creating backup for group {group_name}")
            for file_path_str in files_to_remove:
                file_path = Path(file_path_str)
                if file_path.exists():
                    backup_path = group_backup_dir / file_path.name
                    if not safe_copy_file(file_path, backup_path):
                        logger.warning(f"Failed to backup: {file_path}")
        
        # Remove duplicate files
        space_saved_group = 0
        for file_path_str in files_to_remove:
            file_path = Path(file_path_str)
            
            # Safety check
            if not str(file_path).startswith(str(self.incoming_dir)):
                logger.warning(f"Safety violation: Remove file not in incoming: {file_path}")
                continue
            
            if file_path.exists():
                file_size = file_path.stat().st_size
                
                if dry_run:
                    logger.debug(f"DRY RUN: Would remove {file_path} ({format_bytes(file_size)})")
                    space_saved_group += file_size
                    stats.files_removed += 1
                else:
                    try:
                        file_path.unlink()
                        logger.debug(f"Removed: {file_path.relative_to(self.incoming_dir)} (duplicate)")
                        space_saved_group += file_size
                        stats.files_removed += 1
                    except Exception as e:
                        error_msg = f"Failed to remove {file_path}: {e}"
                        logger.error(error_msg)
                        stats.errors.append(error_msg)
        
        stats.space_saved += space_saved_group
    
    def _process_unique_files(self, stats: ConsolidationStats, dry_run: bool):
        """Process files that have no duplicates."""
        
        # Load combined manifest to find unique files
        manifest_file = self.manifests_dir / "copied_files_combined.json"
        if not manifest_file.exists():
            logger.warning(f"Combined manifest not found: {manifest_file}")
            return
        
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
        
        files = manifest.get('files', [])
        if not files:
            logger.warning("No files found in combined manifest")
            return
        
        # Create hash -> files mapping
        hash_to_files = {}
        for file_data in files:
            file_hash = file_data.get('hash', '')
            if file_hash:
                if file_hash not in hash_to_files:
                    hash_to_files[file_hash] = []
                hash_to_files[file_hash].append(file_data)
        
        # Find unique files (hashes with only one file)
        unique_files = []
        for file_hash, files_with_hash in hash_to_files.items():
            if len(files_with_hash) == 1:
                unique_files.append(files_with_hash[0])
        
        if not unique_files:
            logger.info("No unique files to process")
            return
        
        logger.info(f"Processing {len(unique_files)} unique files")
        
        with tqdm(unique_files, desc="Processing unique files", unit="files") as pbar:
            for file_data in pbar:
                try:
                    source_path = Path(file_data['path'])
                    
                    # Safety check
                    if not str(source_path).startswith(str(self.incoming_dir)):
                        logger.warning(f"Safety violation: Unique file not in incoming: {source_path}")
                        continue
                    
                    if not source_path.exists():
                        logger.warning(f"Unique file not found: {source_path}")
                        continue
                    
                    # Determine destination path
                    rel_path = source_path.relative_to(self.incoming_dir)
                    # Remove source drive prefix
                    path_parts = rel_path.parts
                    if len(path_parts) > 1:
                        rel_path = Path(*path_parts[1:])
                    
                    dest_path = self.final_dir / rel_path
                    
                    # Copy unique file
                    if dry_run:
                        logger.debug(f"DRY RUN: Would copy unique file {source_path} -> {dest_path}")
                    else:
                        if ensure_directory(dest_path.parent):
                            if safe_copy_file(source_path, dest_path, verify=True):
                                logger.debug(f"Unique: {rel_path}")
                                stats.unique_files_copied += 1
                            else:
                                error_msg = f"Failed to copy unique file: {source_path}"
                                logger.error(error_msg)
                                stats.errors.append(error_msg)
                    
                except Exception as e:
                    error_msg = f"Error processing unique file {file_data.get('path', 'unknown')}: {e}"
                    logger.error(error_msg)
                    stats.errors.append(error_msg)
        
        stats.files_kept += len(unique_files) if dry_run else stats.unique_files_copied
    
    def _generate_final_report(self, stats: ConsolidationStats, dry_run: bool) -> Dict[str, Any]:
        """Generate final consolidation report."""
        
        # Count final collection
        final_count = 0
        final_size = 0
        
        if not dry_run and self.final_dir.exists():
            from .utils import find_media_files
            extensions = self.config.get_supported_extensions()
            all_extensions = extensions.get('photos', []) + extensions.get('videos', [])
            
            for file_path in find_media_files(self.final_dir, all_extensions):
                final_count += 1
                final_size += file_path.stat().st_size
        
        # Create report data
        report_data = {
            'dry_run': dry_run,
            'timestamp': get_current_timestamp(),
            'statistics': {
                'total_processed': stats.total_processed,
                'files_kept': stats.files_kept,
                'files_removed': stats.files_removed,
                'unique_files_copied': stats.unique_files_copied,
                'space_saved_bytes': stats.space_saved,
                'space_saved_human': format_bytes(stats.space_saved),
                'final_collection_files': final_count,
                'final_collection_size_bytes': final_size,
                'final_collection_size_human': format_bytes(final_size)
            },
            'paths': {
                'incoming_dir': str(self.incoming_dir),
                'final_dir': str(self.final_dir),
                'backup_dir': str(self.backup_dir) if self.config.should_backup_before_removal() else None
            },
            'configuration': {
                'preserve_structure': self.config.should_preserve_structure(),
                'backup_before_removal': self.config.should_backup_before_removal(),
                'parallel_jobs': self.config.get_parallel_jobs()
            },
            'errors': stats.errors,
            'success': len(stats.errors) == 0
        }
        
        # Write detailed report file
        report_file = self.data_root / "logs" / f"final_consolidation_{get_current_timestamp().replace(':', '-')}.json"
        ensure_directory(report_file.parent)
        
        try:
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            logger.info(f"Final report saved: {report_file}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
        
        # Clean up empty directories in incoming
        if not dry_run:
            removed_dirs = cleanup_empty_directories(self.incoming_dir)
            if removed_dirs > 0:
                logger.info(f"Cleaned up {removed_dirs} empty directories")
        
        return report_data