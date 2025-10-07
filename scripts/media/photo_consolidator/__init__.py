"""
Photo Consolidation Tool

A safe, intelligent photo consolidation system that uses a copy-first approach
to consolidate photos from multiple drives while preserving originals.
"""

__version__ = "1.0.0"
__author__ = "Homelab Team"

from .config import Config
from .media_scanner import MediaScanner
from .file_copier import FileCopier
from .duplicates import DuplicateDetector
from .consolidator import PhotoConsolidator
from .reporter import ConsolidationReporter

# For backward compatibility, keep PhotoScanner as alias to MediaScanner
PhotoScanner = MediaScanner

__all__ = [
    'Config',
    'MediaScanner',
    'FileCopier',
    'PhotoScanner',  # Backward compatibility
    'DuplicateDetector',
    'PhotoConsolidator',
    'ConsolidationReporter'
]