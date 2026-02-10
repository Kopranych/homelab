"""File copying with verification and progress reporting."""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .config import Config
from .utils import (
    calculate_sha256,
    ensure_directory,
    find_media_files,
    format_bytes,
    get_available_space,
    get_file_size,
    safe_copy_file,
)

logger = logging.getLogger(__name__)


class FileCopier:
    """Copies media files from source drives with verification."""

    def __init__(self, config: Config):
        self.config = config
        self.consolidation_root = Path(config.get_consolidation_root())
        self.incoming_dir = self.consolidation_root / "incoming"
        self.manifests_dir = self.consolidation_root / "manifests"
        self.min_free_space_bytes = config.get_min_free_space_gb() * 1024 * 1024 * 1024

        extensions = config.get_supported_extensions()
        self.all_extensions = extensions.get('photos', []) + extensions.get('videos', [])

        ensure_directory(self.incoming_dir)
        ensure_directory(self.manifests_dir)

    def copy_all_drives(
        self,
        dry_run: Optional[bool] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Dict[str, Any]:
        """Copy media files from all configured source drives.

        For each drive:
        1. Enumerate media files
        2. Check available space
        3. Copy preserving structure into incoming/{drive_label}/
        4. Skip files that already exist with same size
        5. Verify each copy with SHA256
        6. Write per-drive JSON manifest

        Returns dict with copy results.
        """
        if dry_run is None:
            dry_run = self.config.is_dry_run()

        source_drives = self.config.get('infrastructure.storage.source_drives', [])
        if not source_drives:
            raise ValueError("No source drives configured")

        results: Dict[str, Any] = {
            'dry_run': dry_run,
            'copied_files': 0,
            'skipped_files': 0,
            'failed_files': 0,
            'copied_size': 0,
            'total_files': 0,
            'drives_processed': 0,
            'errors': [],
            'per_drive': [],
        }

        for drive_info in source_drives:
            drive_path = drive_info.get('path', '')
            drive_label = drive_info.get('label', Path(drive_path).name)

            logger.info(f"{'DRY RUN: ' if dry_run else ''}Processing drive: {drive_label} ({drive_path})")

            drive_dir = Path(drive_path)
            if not drive_dir.exists() or not drive_dir.is_dir():
                msg = f"Source drive not accessible: {drive_path}"
                logger.warning(msg)
                results['errors'].append(msg)
                continue

            drive_result = self._copy_single_drive(
                drive_dir, drive_label, dry_run, progress_callback
            )

            results['copied_files'] += drive_result['copied']
            results['skipped_files'] += drive_result['skipped']
            results['failed_files'] += drive_result['failed']
            results['copied_size'] += drive_result['copied_size']
            results['total_files'] += drive_result['total']
            results['drives_processed'] += 1
            results['errors'].extend(drive_result['errors'])
            results['per_drive'].append({
                'label': drive_label,
                'path': drive_path,
                **drive_result,
            })

        logger.info(
            f"{'DRY RUN: ' if dry_run else ''}Copy complete: "
            f"{results['copied_files']:,} copied, "
            f"{results['skipped_files']:,} skipped, "
            f"{results['failed_files']:,} failed, "
            f"{format_bytes(results['copied_size'])}"
        )
        return results

    def _copy_single_drive(
        self,
        drive_dir: Path,
        drive_label: str,
        dry_run: bool,
        progress_callback: Optional[Callable[[int, int], None]],
    ) -> Dict[str, Any]:
        """Copy all media files from a single drive."""
        dest_dir = self.incoming_dir / drive_label
        ensure_directory(dest_dir)

        # Collect files first for count
        logger.info(f"Enumerating files on {drive_label}...")
        media_files = list(find_media_files(drive_dir, self.all_extensions))
        total = len(media_files)
        logger.info(f"Found {total:,} media files on {drive_label}")

        if total == 0:
            return {
                'total': 0, 'copied': 0, 'skipped': 0, 'failed': 0,
                'copied_size': 0, 'errors': [],
            }

        # Calculate source size and check space
        source_size = sum(get_file_size(f) for f in media_files)
        logger.info(f"Total source size for {drive_label}: {format_bytes(source_size)}")

        if not dry_run:
            available = get_available_space(self.incoming_dir)
            needed = source_size + self.min_free_space_bytes
            if needed > available:
                msg = (
                    f"Insufficient space for {drive_label}: "
                    f"need {format_bytes(needed)}, have {format_bytes(available)}"
                )
                logger.error(msg)
                return {
                    'total': total, 'copied': 0, 'skipped': 0, 'failed': 0,
                    'copied_size': 0, 'errors': [msg],
                }
            logger.info(
                f"Space check OK: need {format_bytes(needed)}, "
                f"have {format_bytes(available)}"
            )

        copied = 0
        skipped = 0
        failed = 0
        copied_size = 0
        errors: List[str] = []
        manifest_entries: List[Dict[str, Any]] = []

        start_time = time.time()
        last_summary_time = start_time

        for i, src_path in enumerate(media_files, 1):
            try:
                relative = src_path.relative_to(drive_dir)
            except ValueError:
                relative = Path(src_path.name)

            dst_path = dest_dir / relative
            file_size = get_file_size(src_path)

            # Skip if destination exists with same size
            if dst_path.exists() and dst_path.stat().st_size == file_size:
                logger.debug(f"Skip (exists): {relative}")
                skipped += 1
                # Still add to manifest with hash of existing file
                file_hash = calculate_sha256(dst_path)
                manifest_entries.append({
                    'path': str(dst_path),
                    'relative_path': str(relative),
                    'size': file_size,
                    'hash': file_hash,
                    'modified': src_path.stat().st_mtime,
                })
                if progress_callback and i % 50 == 0:
                    progress_callback(i, total)
                continue

            if dry_run:
                logger.debug(f"DRY RUN: would copy {relative} ({format_bytes(file_size)})")
                copied += 1
                copied_size += file_size
            else:
                ensure_directory(dst_path.parent)
                # Copy file, hash source, then verify destination matches
                # (avoids triple-hash from safe_copy_file(verify=True) + calculate_sha256)
                try:
                    import shutil
                    shutil.copy2(src_path, dst_path)
                    src_hash = calculate_sha256(src_path)
                    dst_hash = calculate_sha256(dst_path)
                    if src_hash and src_hash == dst_hash:
                        manifest_entries.append({
                            'path': str(dst_path),
                            'relative_path': str(relative),
                            'size': file_size,
                            'hash': dst_hash,
                            'modified': src_path.stat().st_mtime,
                        })
                        copied += 1
                        copied_size += file_size
                    else:
                        msg = f"Hash verification failed: {src_path}"
                        logger.warning(msg)
                        errors.append(msg)
                        failed += 1
                except Exception as e:
                    msg = f"Failed to copy: {src_path} ({e})"
                    logger.warning(msg)
                    errors.append(msg)
                    failed += 1

            # Progress logging every 50 files
            if i % 50 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                logger.info(
                    f"Progress: {i:,}/{total:,} ({i*100/total:.1f}%) — "
                    f"{format_bytes(copied_size)} copied, "
                    f"{rate:.0f} files/min"
                )
                if progress_callback:
                    progress_callback(i, total)

            # Periodic time/size summary every 5 minutes
            now = time.time()
            if now - last_summary_time >= 300:
                elapsed = now - start_time
                logger.info(
                    f"Summary after {elapsed/60:.1f}min: "
                    f"{copied:,} copied, {skipped:,} skipped, {failed:,} failed, "
                    f"{format_bytes(copied_size)}"
                )
                last_summary_time = now

        # Write per-drive copied manifest
        if not dry_run and manifest_entries:
            manifest_data = {
                'files': manifest_entries,
                'metadata': {
                    'created': datetime.now().isoformat(),
                    'drive_label': drive_label,
                    'drive_path': str(drive_dir),
                    'total_files': len(manifest_entries),
                    'total_size': sum(e['size'] for e in manifest_entries),
                    'copied': copied,
                    'skipped': skipped,
                    'failed': failed,
                },
            }
            manifest_path = self.manifests_dir / f"{drive_label}_copied_manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(manifest_data, f, indent=2)
            logger.info(f"Per-drive manifest written: {manifest_path}")

        elapsed = time.time() - start_time
        logger.info(
            f"Drive {drive_label} complete in {elapsed/60:.1f}min: "
            f"{copied:,} copied, {skipped:,} skipped, {failed:,} failed, "
            f"{format_bytes(copied_size)}"
        )

        return {
            'total': total,
            'copied': copied,
            'skipped': skipped,
            'failed': failed,
            'copied_size': copied_size,
            'errors': errors,
        }
