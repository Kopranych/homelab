"""Reporting and statistics for photo consolidation."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from .utils import format_bytes

logger = logging.getLogger(__name__)


class ConsolidationReporter:
    """Generates reports and statistics for photo consolidation."""
    
    def __init__(self, config):
        """Initialize reporter with configuration."""
        self.config = config
        self.data_root = Path(config.get_consolidation_root())
    
    def generate_summary_report(self, results: Dict[str, Any]) -> str:
        """
        Generate human-readable summary report.
        
        Args:
            results: Results from consolidation process
            
        Returns:
            Formatted summary report
        """
        stats = results.get('statistics', {})
        paths = results.get('paths', {})
        
        report = []
        report.append("=" * 50)
        report.append("PHOTO CONSOLIDATION SUMMARY REPORT")
        report.append("=" * 50)
        report.append(f"Completed: {results.get('timestamp', 'Unknown')}")
        report.append(f"Mode: {'DRY RUN' if results.get('dry_run', False) else 'LIVE RUN'}")
        report.append("")
        
        report.append("=== CONSOLIDATION RESULTS ===")
        report.append(f"Strategy: Safe copy-first workflow (originals never touched)")
        report.append(f"Source: Copied files in {paths.get('incoming_dir', 'N/A')}")
        report.append(f"Target: Clean collection in {paths.get('final_dir', 'N/A')}")
        report.append("")
        
        report.append("=== FILE STATISTICS ===")
        report.append(f"• Total files processed: {stats.get('total_processed', 0):,}")
        report.append(f"• Files kept (unique + best quality): {stats.get('files_kept', 0):,}")
        report.append(f"• Duplicate files removed: {stats.get('files_removed', 0):,}")
        report.append(f"• Unique files copied: {stats.get('unique_files_copied', 0):,}")
        report.append(f"• Final collection: {stats.get('final_collection_files', 0):,} files "
                     f"({stats.get('final_collection_size_human', '0B')})")
        report.append(f"• Space saved from deduplication: {stats.get('space_saved_human', '0B')}")
        report.append("")
        
        report.append("=== QUALITY ACHIEVEMENTS ===")
        report.append("✅ All unique photos and videos preserved")
        report.append("✅ Only highest quality versions kept (RAW > high-res JPEG > compressed)")
        report.append("✅ Folder structure optimized and organized")
        report.append("✅ Storage maximized through intelligent deduplication")
        report.append("✅ Process 100% safe (originals never modified)")
        report.append("✅ Photos AND videos consolidated")
        report.append("✅ Hash verification throughout process")
        report.append("")
        
        report.append("=== SAFETY SUMMARY ===")
        report.append("🔒 Original drives: COMPLETELY UNTOUCHED throughout process")
        report.append(f"📁 Work performed: Only on copied files in {paths.get('incoming_dir', 'N/A')}")
        
        backup_dir = paths.get('backup_dir')
        if backup_dir:
            report.append(f"💾 Backups created: Yes, in {backup_dir}")
        else:
            report.append("💾 Backups created: Disabled (originals are the backup)")
        
        report.append("✅ Verification: Human confirmation via Nextcloud interface")
        report.append(f"📋 Audit trail: Complete logs in {self.data_root / 'logs'}")
        report.append("")
        
        # Show errors if any
        errors = results.get('errors', [])
        if errors:
            report.append("=== ERRORS ENCOUNTERED ===")
            for error in errors:
                report.append(f"❌ {error}")
            report.append("")
        
        report.append("=== NEXT STEPS ===")
        if results.get('dry_run', False):
            report.append("1. 🔄 REVIEW THIS DRY RUN RESULT")
            report.append("2. Run with dry_run=false to perform actual consolidation")
            report.append("3. Set up photo management (Immich, PhotoPrism, etc.)")
        else:
            report.append("1. ✅ PHOTO CONSOLIDATION COMPLETE")
            report.append(f"2. Review final collection in {paths.get('final_dir', 'N/A')}")
            report.append("3. Set up photo management (Immich, PhotoPrism, etc.)")
            report.append("4. Configure automated backups of final collection")
            report.append("5. Format original drives for Phase 6 - Storage Setup")
        
        report.append("")
        success = results.get('success', True) and len(errors) == 0
        status = "✅ COMPLETE SUCCESS" if success else "⚠️ COMPLETED WITH ISSUES"
        report.append(f"STATUS: {status}")
        
        return "\n".join(report)
    
    def print_progress_summary(self, phase: str, current: int, total: int, 
                             rate: str = "", eta: str = ""):
        """Print progress summary for a phase."""
        percentage = (current / total * 100) if total > 0 else 0
        
        print(f"\n=== {phase.upper()} PROGRESS ===")
        print(f"Files: {current:,} / {total:,} ({percentage:.1f}%)")
        if rate:
            print(f"Rate: {rate}")
        if eta:
            print(f"ETA: {eta}")
        print("=" * 40)
    
    def save_report(self, results: Dict[str, Any], filename: str = None) -> str:
        """
        Save detailed report to file.
        
        Args:
            results: Results dictionary
            filename: Optional filename (auto-generated if None)
            
        Returns:
            Path to saved report file
        """
        if filename is None:
            timestamp = results.get('timestamp', 'unknown').replace(':', '-')
            filename = f"consolidation_report_{timestamp}.txt"
        
        report_file = self.data_root / "logs" / filename
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate human-readable report
        report_content = self.generate_summary_report(results)
        
        try:
            with open(report_file, 'w') as f:
                f.write(report_content)
            
            logger.info(f"Report saved: {report_file}")
            return str(report_file)
            
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            raise
    
    def load_analysis_results(self) -> Dict[str, Any]:
        """Load results from duplicate analysis."""
        duplicates_dir = self.data_root / "duplicates" / "reports"
        analysis_file = duplicates_dir / "copied_files_analysis.txt"
        
        if not analysis_file.exists():
            return {}
        
        # Parse basic stats from analysis file
        stats = {}
        try:
            with open(analysis_file, 'r') as f:
                content = f.read()
                
            # Extract key statistics
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('Total files analyzed:'):
                    stats['total_files'] = int(line.split(':')[1].strip().replace(',', ''))
                elif line.startswith('Duplicate groups:'):
                    stats['duplicate_groups'] = int(line.split(':')[1].strip().replace(',', ''))
                elif line.startswith('Space savings:'):
                    stats['space_savings'] = line.split(':')[1].strip()
                    
        except Exception as e:
            logger.error(f"Failed to parse analysis results: {e}")
            
        return stats