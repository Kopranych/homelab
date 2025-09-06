"""
Photo Consolidation Tool

A safe, intelligent photo consolidation system that uses a copy-first approach
to consolidate photos from multiple drives while preserving originals.
"""

__version__ = "1.0.0"
__author__ = "Homelab Team"

from .config import Config
from .scanner import PhotoScanner
from .duplicates import DuplicateDetector
from .consolidator import PhotoConsolidator
from .reporter import ConsolidationReporter

__all__ = [
    'Config',
    'PhotoScanner', 
    'DuplicateDetector',
    'PhotoConsolidator',
    'ConsolidationReporter'
]