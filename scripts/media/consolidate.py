#!/usr/bin/env python3
"""
Photo Consolidation CLI

A safe, intelligent photo consolidation system that uses a copy-first approach
to consolidate photos from multiple drives while preserving originals.
"""

import os
import sys
import logging
import click
from datetime import datetime
from pathlib import Path
from colorama import init, Fore, Style

# Add the photo_consolidator package to path
sys.path.insert(0, str(Path(__file__).parent))

from photo_consolidator import (
    Config,
    MediaScanner,
    FileCopier,
    DuplicateDetector,
    PhotoConsolidator,
    ConsolidationReporter,
)

# Initialize colorama for cross-platform colored output
init()

# Will be reconfigured after config is loaded
_file_handler = None


def setup_logging(level: str = 'INFO', log_dir: Path = None):
    """Set up logging configuration."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler — always flush for Ansible visibility
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(console_handler)

    # File handler if log_dir provided
    if log_dir:
        _setup_file_logging(log_dir, formatter, root_logger)

    # Reduce noise from libraries
    logging.getLogger('PIL').setLevel(logging.WARNING)


def _setup_file_logging(log_dir: Path, formatter: logging.Formatter, root_logger: logging.Logger,
                        log_name: str = 'photo_consolidation'):
    """Add file handler to root logger."""
    global _file_handler
    log_dir.mkdir(parents=True, exist_ok=True)

    # Remove previous file handler if any
    if _file_handler is not None:
        root_logger.removeHandler(_file_handler)

    _file_handler = logging.FileHandler(log_dir / f'{log_name}.log')
    _file_handler.setFormatter(formatter)
    root_logger.addHandler(_file_handler)


def print_header(title: str):
    """Print a formatted header."""
    click.echo(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    click.echo(f"{Fore.CYAN}{title.center(60)}{Style.RESET_ALL}")
    click.echo(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
    sys.stdout.flush()

def print_success(message: str):
    """Print success message."""
    click.echo(f"{Fore.GREEN}OK: {message}{Style.RESET_ALL}")
    sys.stdout.flush()

def print_warning(message: str):
    """Print warning message."""
    click.echo(f"{Fore.YELLOW}WARN: {message}{Style.RESET_ALL}")
    sys.stdout.flush()

def print_error(message: str):
    """Print error message."""
    click.echo(f"{Fore.RED}ERROR: {message}{Style.RESET_ALL}")
    sys.stdout.flush()

def print_info(message: str):
    """Print info message."""
    click.echo(f"{Fore.BLUE}INFO: {message}{Style.RESET_ALL}")
    sys.stdout.flush()


@click.group()
@click.option('--config', '-c', help='Path to configuration file')
@click.option('--log-level', '-l', default='INFO',
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              help='Logging level')
@click.pass_context
def cli(ctx, config, log_level):
    """Photo Consolidation Tool - Safe copy-first photo organization."""

    # Initial logging setup (console only)
    setup_logging(log_level)

    try:
        # Load configuration
        config_obj = Config(config)

        # Validate configuration
        errors = config_obj.validate_config()
        if errors:
            print_error("Configuration validation failed:")
            for error in errors:
                click.echo(f"  - {error}")
            sys.exit(1)

        # Now set up file logging with consolidation_root
        consolidation_root = Path(config_obj.get_consolidation_root())
        log_dir = consolidation_root / "logs"
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        log_name = ctx.invoked_subcommand or 'photo_consolidation'
        _setup_file_logging(log_dir, formatter, logging.getLogger(), log_name)

        # Store in context
        ctx.ensure_object(dict)
        ctx.obj['config'] = config_obj

    except Exception as e:
        print_error(f"Failed to load configuration: {e}")
        sys.exit(1)


@cli.command()
@click.option('--progress', is_flag=True, help='Show detailed progress information')
@click.pass_context
def scan(ctx, progress):
    """Scan source drives and create manifests."""

    print_header("PHOTO SCANNING PHASE")

    config = ctx.obj['config']
    scanner = MediaScanner(config)

    try:
        print_info("Starting scan of source drives...")

        def progress_callback(current, total):
            if progress:
                click.echo(f"\rScanned: {current:,} files...", nl=False)
                sys.stdout.flush()

        results = scanner.scan_source_drives(progress_callback if progress else None)

        if progress:
            click.echo()  # New line after progress

        if results['errors']:
            print_warning(f"Scan completed with {len(results['errors'])} errors:")
            for error in results['errors']:
                click.echo(f"  - {error}")

        print_success(f"Scan complete: {results['total_files']:,} files found")
        print_info(f"Total size: {results['total_size']:,} bytes")
        print_info(f"Drives scanned: {results['drives_scanned']}")

        # Show manifest locations
        click.echo("\nManifest files created:")
        for drive, manifest in results['manifests'].items():
            click.echo(f"  - {drive} -> {manifest}")
        sys.stdout.flush()

    except Exception as e:
        print_error(f"Scan failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--dry-run/--no-dry-run', default=None, help='Perform dry run (override config)')
@click.option('--progress', is_flag=True, help='Show detailed progress information')
@click.pass_context
def copy(ctx, dry_run, progress):
    """Copy media files from source drives to incoming directory."""

    print_header("PHOTO COPYING PHASE")

    config = ctx.obj['config']
    copier = FileCopier(config)
    scanner = MediaScanner(config)

    try:
        print_info("Starting copy operation...")

        def progress_callback(current, total):
            if progress:
                percentage = (current / total * 100) if total > 0 else 0
                click.echo(f"\rProgress: {current:,}/{total:,} ({percentage:.1f}%)", nl=False)
                sys.stdout.flush()

        results = copier.copy_all_drives(dry_run, progress_callback if progress else None)

        if progress:
            click.echo()  # New line after progress

        if results['dry_run']:
            print_info("DRY RUN completed - no files were actually copied")

        if results['errors']:
            print_warning(f"Copy completed with {len(results['errors'])} errors:")
            for error in results['errors'][:5]:  # Show first 5 errors
                click.echo(f"  - {error}")
            if len(results['errors']) > 5:
                click.echo(f"  - ... and {len(results['errors']) - 5} more errors")

        print_success(f"Copy complete: {results['copied_files']:,} files copied")
        print_info(f"Skipped (existing): {results['skipped_files']:,}")
        print_info(f"Size copied: {results['copied_size']:,} bytes")
        if results['failed_files'] > 0:
            print_warning(f"Failed files: {results['failed_files']:,}")

        # Create combined manifest from per-drive manifests
        if not results['dry_run']:
            print_info("Creating combined manifest of copied files...")
            manifest_file = scanner.create_combined_manifest()
            print_success(f"Combined manifest created: {manifest_file}")

        sys.stdout.flush()

    except Exception as e:
        print_error(f"Copy failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--manifest', '-m', help='Manifest file to analyze')
@click.pass_context
def analyze(ctx, manifest):
    """Analyze copied files for duplicates and rank by quality."""

    print_header("DUPLICATE ANALYSIS PHASE")

    config = ctx.obj['config']
    detector = DuplicateDetector(config)

    try:
        print_info("Starting duplicate analysis...")

        results = detector.analyze_duplicates(manifest)

        # Show warnings
        if results['warnings']:
            for warning in results['warnings']:
                print_warning(warning)

        print_success("Duplicate analysis complete!")
        print_info(f"Total files: {results['total_files']:,}")
        print_info(f"Unique files: {results['unique_files']:,}")
        print_info(f"Duplicate groups: {results['duplicate_groups']:,}")
        print_info(f"Space savings potential: {results['space_savings_human']}")
        print_info(f"Duplicate percentage: {results['duplicate_percentage']:.1f}%")

        click.echo(f"\nReports generated:")
        click.echo(f"  - Summary: {results['summary_report']}")
        click.echo(f"  - Group files: {len(results['group_files'])} files")

        if results['duplicate_groups'] > 0:
            print_info("Use Nextcloud interface to review duplicate groups before consolidation")
        else:
            print_info("No duplicates found - all files are unique")

        sys.stdout.flush()

    except Exception as e:
        print_error(f"Analysis failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--dry-run/--no-dry-run', default=None, help='Perform dry run (override config)')
@click.option('--report', '-r', help='Save report to specific file')
@click.pass_context
def consolidate(ctx, dry_run, report):
    """Consolidate files by removing duplicates and organizing."""

    print_header("CONSOLIDATION PHASE")

    config = ctx.obj['config']
    consolidator = PhotoConsolidator(config)
    reporter = ConsolidationReporter(config)

    try:
        print_info("Starting file consolidation...")

        results = consolidator.consolidate_files(dry_run)

        if results['dry_run']:
            print_info("DRY RUN completed - no files were actually modified")

        # Show errors
        if results['errors']:
            print_warning(f"Consolidation completed with {len(results['errors'])} errors:")
            for error in results['errors'][:5]:
                click.echo(f"  - {error}")
            if len(results['errors']) > 5:
                click.echo(f"  - ... and {len(results['errors']) - 5} more errors")

        stats = results['statistics']
        print_success("Consolidation complete!")
        print_info(f"Files kept: {stats['files_kept']:,}")
        print_info(f"Files removed: {stats['files_removed']:,}")
        print_info(f"Space saved: {stats['space_saved_human']}")
        print_info(f"Final collection: {stats['final_collection_files']:,} files")

        # Generate and save report
        print_info("Generating final report...")
        report_file = reporter.save_report(results, report)
        print_success(f"Report saved: {report_file}")

        # Print summary
        click.echo("\n" + reporter.generate_summary_report(results))
        sys.stdout.flush()

    except Exception as e:
        print_error(f"Consolidation failed: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def workflow(ctx):
    """Run complete workflow: scan -> copy -> analyze -> consolidate."""

    print_header("COMPLETE PHOTO CONSOLIDATION WORKFLOW")

    config = ctx.obj['config']

    if config.is_dry_run():
        print_info("Running in DRY RUN mode (set dry_run: false in config for live run)")

    try:
        # Phase 1: Scan
        print_info("Phase 1/4: Scanning source drives...")
        ctx.invoke(scan)

        # Phase 2: Copy
        print_info("\nPhase 2/4: Copying files...")
        ctx.invoke(copy, progress=True)

        # Phase 3: Analyze
        print_info("\nPhase 3/4: Analyzing duplicates...")
        ctx.invoke(analyze)

        # Phase 4: Consolidate
        print_info("\nPhase 4/4: Consolidating files...")
        ctx.invoke(consolidate)

        print_header("WORKFLOW COMPLETE!")

        if config.is_dry_run():
            print_warning("This was a DRY RUN - no files were actually modified")
            print_info("Set dry_run: false in config and re-run to perform actual consolidation")
        else:
            print_success("Photo consolidation completed successfully!")
            print_info("Your photos are now consolidated and organized")
            print_info("Original drives remain untouched and can be safely formatted")

        sys.stdout.flush()

    except Exception as e:
        print_error(f"Workflow failed: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show current consolidation status and statistics."""

    print_header("CONSOLIDATION STATUS")

    config = ctx.obj['config']
    consolidation_root = Path(config.get_consolidation_root())

    click.echo(f"Consolidation root: {consolidation_root}")
    click.echo(f"Configuration: {config.config_path}")
    click.echo(f"Dry run mode: {config.is_dry_run()}")
    click.echo()

    # Check phase completion status
    phases = [
        ("Manifests", consolidation_root / "manifests", "Source drive scanning"),
        ("Incoming", consolidation_root / "incoming", "File copying"),
        ("Duplicates", consolidation_root / "duplicates", "Duplicate analysis"),
        ("Final", consolidation_root / "final", "Consolidation")
    ]

    for phase_name, phase_dir, description in phases:
        if phase_dir.exists():
            if phase_name == "Manifests":
                count = len(list(phase_dir.glob("*_source_manifest.json")))
                copied_count = len(list(phase_dir.glob("*_copied_manifest.json")))
                print_success(f"{phase_name}: {count} scan manifests, {copied_count} copy manifests - {description}")
            elif phase_name == "Duplicates":
                groups_dir = phase_dir / "groups"
                count = len(list(groups_dir.glob("group_*.txt"))) if groups_dir.exists() else 0
                print_success(f"{phase_name}: {count:,} groups - {description}")
            else:
                from photo_consolidator.utils import find_media_files
                extensions = config.get_supported_extensions()
                all_extensions = extensions.get('photos', []) + extensions.get('videos', [])
                count = sum(1 for _ in find_media_files(phase_dir, all_extensions))
                print_success(f"{phase_name}: {count:,} files - {description}")
        else:
            click.echo(f"  [ ] {phase_name}: Not started - {description}")

    sys.stdout.flush()


if __name__ == '__main__':
    cli()
