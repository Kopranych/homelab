"""Duplicate detection and quality ranking."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass
from tqdm import tqdm

from .config import Config
from .utils import format_bytes, ensure_directory, get_current_timestamp

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """Information about a media file."""
    path: str
    relative_path: str
    size: int
    hash: str
    extension: str
    quality_score: float = 0.0
    
    @property
    def name(self) -> str:
        """Get filename without path."""
        return Path(self.path).name
    
    @property
    def parent_dir(self) -> str:
        """Get parent directory name."""
        return Path(self.path).parent.name


@dataclass 
class DuplicateGroup:
    """Group of duplicate files."""
    hash: str
    files: List[FileInfo]
    best_file: Optional[FileInfo] = None
    total_size: int = 0
    space_savings: int = 0
    
    def __post_init__(self):
        """Calculate derived properties after initialization."""
        self.total_size = sum(f.size for f in self.files)
        if self.best_file:
            self.space_savings = self.total_size - self.best_file.size


class DuplicateDetector:
    """Detects and ranks duplicate files by quality."""
    
    def __init__(self, config: Config):
        """
        Initialize duplicate detector with configuration.
        
        Args:
            config: Configuration instance
        """
        self.config = config
        self.data_root = Path(config.get_data_root())
        self.duplicates_dir = self.data_root / "duplicates" 
        self.manifests_dir = self.data_root / "manifests"
        
        # Get quality configuration
        self.quality_config = config.get_quality_config()
        self.format_scores = self.quality_config.get('format_scores', {})
        self.folder_bonuses = self.quality_config.get('folder_bonuses', {})
        self.size_thresholds = self.quality_config.get('size_thresholds', {})
        
        # Ensure directories exist
        ensure_directory(self.duplicates_dir)
        ensure_directory(self.duplicates_dir / "reports")
        ensure_directory(self.duplicates_dir / "groups")
    
    def analyze_duplicates(self, manifest_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze copied files for duplicates and rank by quality.
        
        Args:
            manifest_file: Path to manifest file (defaults to copied_files_combined.json)
            
        Returns:
            Dictionary with analysis results
        """
        if manifest_file is None:
            manifest_file = str(self.manifests_dir / "copied_files_combined.json")
        
        manifest_path = Path(manifest_file)
        if not manifest_path.exists():
            raise ValueError(f"Manifest file not found: {manifest_file}")
        
        logger.info(f"Starting duplicate analysis from {manifest_file}")
        
        # Load manifest
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        files = manifest.get('files', [])
        total_files = len(files)
        
        if total_files == 0:
            logger.warning("No files found in manifest")
            return self._empty_results()
        
        logger.info(f"Analyzing {total_files} files for duplicates")
        
        # Convert to FileInfo objects and calculate quality scores
        file_infos = []
        for file_data in tqdm(files, desc="Processing files", unit="files"):
            file_info = self._create_file_info(file_data)
            file_info.quality_score = self._calculate_quality_score(file_info)
            file_infos.append(file_info)
        
        # Group by hash to find duplicates
        hash_groups = defaultdict(list)
        for file_info in file_infos:
            if file_info.hash:  # Skip files without valid hash
                hash_groups[file_info.hash].append(file_info)
        
        # Find duplicate groups (more than one file with same hash)
        duplicate_groups = []
        unique_files = []
        
        for file_hash, files_with_hash in hash_groups.items():
            if len(files_with_hash) > 1:
                # Sort by quality score (highest first)
                files_with_hash.sort(key=lambda f: f.quality_score, reverse=True)
                
                group = DuplicateGroup(
                    hash=file_hash,
                    files=files_with_hash,
                    best_file=files_with_hash[0]
                )
                duplicate_groups.append(group)
            else:
                unique_files.extend(files_with_hash)
        
        logger.info(f"Found {len(duplicate_groups)} duplicate groups, "
                   f"{len(unique_files)} unique files")
        
        # Generate reports
        results = self._generate_reports(duplicate_groups, unique_files, total_files)
        
        # Check for warnings
        duplicate_percentage = (len(duplicate_groups) * 100) / total_files if total_files > 0 else 0
        max_percentage = self.config.get_safety_config().get('max_duplicate_percentage', 80)
        
        if duplicate_percentage > max_percentage:
            warning = f"High duplicate percentage: {duplicate_percentage:.1f}% (threshold: {max_percentage}%)"
            logger.warning(warning)
            results['warnings'].append(warning)
        
        logger.info("Duplicate analysis complete")
        return results
    
    def _create_file_info(self, file_data: Dict[str, Any]) -> FileInfo:
        """Create FileInfo object from manifest data."""
        path = file_data.get('path', '')
        extension = Path(path).suffix.lower().lstrip('.')
        
        return FileInfo(
            path=path,
            relative_path=file_data.get('relative_path', ''),
            size=file_data.get('size', 0),
            hash=file_data.get('hash', ''),
            extension=extension
        )
    
    def _calculate_quality_score(self, file_info: FileInfo) -> float:
        """
        Calculate quality score for a file.
        
        Args:
            file_info: File information
            
        Returns:
            Quality score (0-100)
        """
        score = 0.0
        
        # Base score by file format
        extension = file_info.extension.lower()
        
        # RAW file formats get highest priority
        raw_extensions = ['cr2', 'nef', 'arw', 'dng', 'raf', 'orf', 'rw2', 'pef', 'srw', 'x3f']
        if extension in raw_extensions:
            score += self.format_scores.get('raw_files', 90)
        elif extension in ['jpg', 'jpeg']:
            # Score JPEG based on file size (higher = better quality)
            large_threshold = self.size_thresholds.get('photo_large_mb', 5) * 1024 * 1024
            if file_info.size > large_threshold:
                score += self.format_scores.get('high_res_jpg', 75)
            else:
                score += self.format_scores.get('standard_jpg', 60)
        elif extension == 'png':
            score += self.format_scores.get('png', 65)
        elif extension in ['heic', 'heif']:
            score += self.format_scores.get('heic', 70)
        elif extension in ['mp4', 'mov', 'avi', 'mkv']:
            # Video files - score by size
            large_threshold = self.size_thresholds.get('video_large_mb', 100) * 1024 * 1024
            if file_info.size > large_threshold:
                score += self.format_scores.get('videos_hd', 70)
            else:
                score += self.format_scores.get('videos_sd', 50)
        else:
            # Default score for other formats
            score += 50
        
        # Folder context bonus/penalty
        folder_path = Path(file_info.path).parent
        folder_name = folder_path.name.lower()
        parent_folder = folder_path.parent.name.lower()
        
        # Check for organized folders
        organized_keywords = ['photos', 'pictures', 'vacation', 'wedding', 'family', 'events']
        meaningful_keywords = ['2020', '2021', '2022', '2023', '2024', 'holiday', 'trip']
        backup_keywords = ['backup', 'old', 'copy', 'duplicate', 'archive']
        junk_keywords = ['downloads', 'temp', 'tmp', 'cache', 'recycle']
        
        # Year patterns (organized)
        if any(year in folder_name for year in ['2020', '2021', '2022', '2023', '2024']):
            score += self.folder_bonuses.get('organized', 10)
        elif any(keyword in folder_name for keyword in organized_keywords):
            score += self.folder_bonuses.get('organized', 10)
        elif any(keyword in folder_name for keyword in meaningful_keywords):
            score += self.folder_bonuses.get('meaningful', 5)
        elif any(keyword in folder_name for keyword in backup_keywords):
            score += self.folder_bonuses.get('backup', -10)
        elif any(keyword in folder_name for keyword in junk_keywords):
            score += self.folder_bonuses.get('junk', -15)
        
        # Check parent folder too
        if any(keyword in parent_folder for keyword in backup_keywords):
            score += self.folder_bonuses.get('backup', -5)
        
        # Size bonus (larger files are generally better quality)
        if file_info.size > 10 * 1024 * 1024:  # > 10MB
            score += 5
        elif file_info.size > 50 * 1024 * 1024:  # > 50MB  
            score += 10
        
        # Ensure score is within bounds
        return max(0, min(100, score))
    
    def _generate_reports(self, duplicate_groups: List[DuplicateGroup], 
                         unique_files: List[FileInfo], total_files: int) -> Dict[str, Any]:
        """Generate comprehensive duplicate analysis reports."""
        
        # Calculate statistics
        total_duplicates = sum(len(group.files) for group in duplicate_groups)
        total_space_savings = sum(group.space_savings for group in duplicate_groups)
        
        # Generate main summary report
        summary_report = self.duplicates_dir / "reports" / "copied_files_analysis.txt"
        self._write_summary_report(summary_report, duplicate_groups, unique_files, 
                                 total_files, total_space_savings)
        
        # Generate individual group reports
        group_files = []
        for i, group in enumerate(duplicate_groups):
            group_file = self.duplicates_dir / "groups" / f"group_{i+1:05d}.txt"
            self._write_group_report(group_file, group, i+1)
            group_files.append(str(group_file))
        
        results = {
            'total_files': total_files,
            'unique_files': len(unique_files),
            'duplicate_groups': len(duplicate_groups),
            'total_duplicates': total_duplicates,
            'space_savings_bytes': total_space_savings,
            'space_savings_human': format_bytes(total_space_savings),
            'duplicate_percentage': (total_duplicates * 100) / total_files if total_files > 0 else 0,
            'summary_report': str(summary_report),
            'group_files': group_files,
            'warnings': [],
            'analysis_timestamp': get_current_timestamp()
        }
        
        logger.info(f"Generated reports: {len(group_files)} groups, "
                   f"savings: {format_bytes(total_space_savings)}")
        
        return results
    
    def _write_summary_report(self, report_file: Path, duplicate_groups: List[DuplicateGroup],
                            unique_files: List[FileInfo], total_files: int, 
                            total_space_savings: int):
        """Write summary analysis report."""
        
        with open(report_file, 'w') as f:
            f.write("=== PHOTO CONSOLIDATION DUPLICATE ANALYSIS ===\n")
            f.write(f"Generated: {get_current_timestamp()}\n")
            f.write(f"Configuration: {self.config.config_path}\n\n")
            
            f.write("=== SUMMARY STATISTICS ===\n")
            f.write(f"Total files analyzed: {total_files:,}\n")
            f.write(f"Unique files: {len(unique_files):,}\n")
            f.write(f"Duplicate groups: {len(duplicate_groups):,}\n")
            f.write(f"Total duplicates: {sum(len(g.files) for g in duplicate_groups):,}\n")
            f.write(f"Space savings: {format_bytes(total_space_savings)}\n")
            
            if total_files > 0:
                duplicate_percentage = (len(duplicate_groups) * 100) / total_files
                f.write(f"Duplicate percentage: {duplicate_percentage:.1f}%\n")
            
            f.write("\n=== DUPLICATE GROUPS SUMMARY ===\n")
            for i, group in enumerate(duplicate_groups[:10]):  # Show first 10 groups
                f.write(f"\nGroup {i+1:05d} ({group.hash[:8]}):\n")
                f.write(f"  Files: {len(group.files)}\n")
                f.write(f"  Best: {group.best_file.name} (score: {group.best_file.quality_score:.1f})\n")
                f.write(f"  Savings: {format_bytes(group.space_savings)}\n")
            
            if len(duplicate_groups) > 10:
                f.write(f"\n... and {len(duplicate_groups) - 10} more groups\n")
            
            f.write("\n=== QUALITY SCORING BREAKDOWN ===\n")
            
            # Show extension distribution
            ext_counter = Counter(f.extension for group in duplicate_groups for f in group.files)
            f.write("File extensions in duplicates:\n")
            for ext, count in ext_counter.most_common():
                f.write(f"  .{ext}: {count:,} files\n")
            
            # Show folder patterns
            folder_counter = Counter(Path(f.path).parent.name for group in duplicate_groups for f in group.files)
            f.write("\nTop folders with duplicates:\n")
            for folder, count in folder_counter.most_common(10):
                f.write(f"  {folder}: {count:,} files\n")
            
            f.write("\n=== NEXT STEPS ===\n")
            f.write("1. Review duplicate groups in the groups/ directory\n")
            f.write("2. Verify quality rankings look correct\n")
            f.write("3. Use Nextcloud interface for visual verification\n")
            f.write("4. Run consolidation to remove lower quality duplicates\n")
            f.write("\n=== CONFIGURATION USED ===\n")
            f.write(f"Format scores: {self.format_scores}\n")
            f.write(f"Folder bonuses: {self.folder_bonuses}\n")
            f.write(f"Size thresholds: {self.size_thresholds}\n")
    
    def _write_group_report(self, group_file: Path, group: DuplicateGroup, group_number: int):
        """Write individual duplicate group report."""
        
        with open(group_file, 'w') as f:
            f.write(f"=== Duplicate Group {group_number:05d} ===\n")
            f.write(f"Hash: {group.hash}\n")
            f.write(f"Files: {len(group.files)}\n")
            f.write(f"Total size: {format_bytes(group.total_size)}\n") 
            f.write(f"Space savings: {format_bytes(group.space_savings)}\n\n")
            
            f.write("Files ranked by quality (KEEP first, REMOVE others):\n\n")
            
            for i, file_info in enumerate(group.files):
                action = "KEEP" if i == 0 else "REMOVE"
                quality_indicator = "🎯 BEST QUALITY" if i == 0 else ""
                
                f.write(f"[{i+1}] {action} - Score: {file_info.quality_score:.0f}/100 {quality_indicator}\n")
                f.write(f"    Full: {file_info.path}\n")
                f.write(f"    Size: {format_bytes(file_info.size)}\n")
                f.write(f"    Format: {file_info.extension.upper()}\n")
                f.write(f"    Folder: {Path(file_info.path).parent.name}\n")
                f.write("\n")
            
            f.write(f"Recommendation: Keep file [1], remove files [2-{len(group.files)}]\n")
            f.write(f"Space saved by removing duplicates: {format_bytes(group.space_savings)}\n")
    
    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results structure."""
        return {
            'total_files': 0,
            'unique_files': 0,
            'duplicate_groups': 0,
            'total_duplicates': 0,
            'space_savings_bytes': 0,
            'space_savings_human': '0B',
            'duplicate_percentage': 0,
            'summary_report': '',
            'group_files': [],
            'warnings': [],
            'analysis_timestamp': get_current_timestamp()
        }


def get_current_timestamp():
    """Get current timestamp as ISO string."""
    from datetime import datetime
    return datetime.now().isoformat()