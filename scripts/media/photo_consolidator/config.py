"""Configuration management for photo consolidation."""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """Manages configuration for photo consolidation from YAML files."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to config file. If None, searches for config files.
        """
        self.config_path = config_path or self._find_config_file()
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _find_config_file(self) -> str:
        """Find configuration file in standard locations."""
        # Look for config files in order of preference
        possible_paths = [
            "config.local.yml",
            "config.yml", 
            "../../../config.local.yml",
            "../../../config.yml",
        ]
        
        for path in possible_paths:
            config_file = Path(__file__).parent / path
            if config_file.exists():
                logger.info(f"Found config file: {config_file}")
                return str(config_file.resolve())
        
        raise FileNotFoundError("No configuration file found. Expected config.yml or config.local.yml")
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
            logger.info(f"Loaded configuration from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            raise
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path like 'photo_consolidation.quality.raw_files'
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_photo_config(self) -> Dict[str, Any]:
        """Get photo consolidation specific configuration."""
        return self.get('photo_consolidation', {})
    
    def get_source_drives(self) -> List[str]:
        """Get list of source drive paths."""
        drives = self.get('infrastructure.storage.source_drives', [])
        return [drive.get('path', '') for drive in drives if drive.get('path')]
    
    def get_data_root(self) -> str:
        """Get data root directory."""
        return self.get('infrastructure.storage.data_root', '/data')

    def get_consolidation_root(self) -> str:
        """Get photo consolidation working directory."""
        root = self.get('infrastructure.storage.consolidation_root')
        if root:
            return root
        return self.get_data_root() + '/photo-consolidation'

    def get_supported_extensions(self) -> Dict[str, List[str]]:
        """Get supported file extensions for photos and videos."""
        extensions = self.get('photo_consolidation.extensions', {})
        return {
            'photos': extensions.get('photos', []),
            'videos': extensions.get('videos', [])
        }
    
    def get_quality_config(self) -> Dict[str, Any]:
        """Get quality scoring configuration."""
        return self.get('photo_consolidation.quality', {})
    
    def get_safety_config(self) -> Dict[str, Any]:
        """Get safety configuration."""
        return self.get('photo_consolidation.safety', {})
    
    def get_process_config(self) -> Dict[str, Any]:
        """Get process configuration."""
        return self.get('photo_consolidation.process', {})
    
    def get_parallel_jobs(self) -> int:
        """Get number of parallel jobs to run."""
        return self.get('photo_consolidation.process.parallel_jobs', 4)
    
    def get_min_free_space_gb(self) -> int:
        """Get minimum free space requirement in GB."""
        return self.get('photo_consolidation.safety.min_free_space_gb', 100)
    
    def should_backup_before_removal(self) -> bool:
        """Check if backup should be created before file removal."""
        return self.get('photo_consolidation.safety.backup_before_removal', False)
    
    def should_preserve_structure(self) -> bool:
        """Check if original folder structure should be preserved."""
        return self.get('photo_consolidation.process.preserve_structure', True)
    
    def is_dry_run(self) -> bool:
        """Check if this is a dry run."""
        return self.get('photo_consolidation.process.dry_run', True)
    
    def get_log_level(self) -> str:
        """Get logging level."""
        return self.get('logging.components.photo_consolidation', 'INFO')
    
    def validate_config(self) -> List[str]:
        """
        Validate configuration and return list of errors.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check required paths
        data_root = self.get_data_root()
        if not data_root:
            errors.append("Data root directory not configured")
        elif not Path(data_root).exists():
            errors.append(f"Data root directory does not exist: {data_root}")

        consolidation_root = self.get_consolidation_root()
        if not consolidation_root:
            errors.append("Consolidation root directory not configured")
        elif not Path(consolidation_root).parent.exists():
            errors.append(f"Parent of consolidation root does not exist: {consolidation_root}")

        # Check source drives
        source_drives = self.get_source_drives()
        if not source_drives:
            errors.append("No source drives configured")
        else:
            for drive in source_drives:
                if not Path(drive).exists():
                    errors.append(f"Source drive does not exist: {drive}")
        
        # Check extensions
        extensions = self.get_supported_extensions()
        if not extensions.get('photos') and not extensions.get('videos'):
            errors.append("No supported file extensions configured")
        
        # Check parallel jobs
        parallel_jobs = self.get_parallel_jobs()
        if parallel_jobs < 1 or parallel_jobs > 32:
            errors.append(f"Invalid parallel_jobs value: {parallel_jobs} (must be 1-32)")
        
        return errors
    
    def __str__(self) -> str:
        """String representation of configuration."""
        return f"Config(path={self.config_path}, drives={len(self.get_source_drives())})"