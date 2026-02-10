"""Media scanning and manifest creation."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .config import Config
from .utils import (
    ensure_directory,
    find_media_files,
    format_bytes,
    get_file_size,
)

logger = logging.getLogger(__name__)


class MediaScanner:
    """Scans source drives for media files and creates manifests."""

    def __init__(self, config: Config):
        self.config = config
        self.consolidation_root = Path(config.get_consolidation_root())
        self.manifests_dir = self.consolidation_root / "manifests"
        ensure_directory(self.manifests_dir)

        extensions = config.get_supported_extensions()
        self.all_extensions = extensions.get('photos', []) + extensions.get('videos', [])

    def scan_source_drives(
        self, progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """Scan all configured source drives and create per-drive scan manifests.

        Returns dict with scan results including file counts, sizes, manifest paths.
        """
        source_drives = self.config.get('infrastructure.storage.source_drives', [])
        if not source_drives:
            raise ValueError("No source drives configured")

        results: Dict[str, Any] = {
            'total_files': 0,
            'total_size': 0,
            'drives_scanned': 0,
            'manifests': {},
            'errors': [],
            'per_drive': [],
        }

        for drive_info in source_drives:
            drive_path = drive_info.get('path', '')
            drive_label = drive_info.get('label', Path(drive_path).name)

            logger.info(f"Scanning drive: {drive_label} ({drive_path})")

            drive_dir = Path(drive_path)
            if not drive_dir.exists() or not drive_dir.is_dir():
                msg = f"Source drive not accessible: {drive_path}"
                logger.warning(msg)
                results['errors'].append(msg)
                continue

            drive_files: List[Dict[str, Any]] = []
            drive_size = 0
            file_count = 0

            for file_path in find_media_files(drive_dir, self.all_extensions):
                size = get_file_size(file_path)
                try:
                    relative = str(file_path.relative_to(drive_dir))
                except ValueError:
                    relative = file_path.name

                drive_files.append({
                    'path': str(file_path),
                    'relative_path': relative,
                    'size': size,
                    'modified': file_path.stat().st_mtime,
                })
                drive_size += size
                file_count += 1

                if progress_callback and file_count % 100 == 0:
                    progress_callback(file_count, 0)

            # Write per-drive scan manifest
            manifest_data = {
                'files': drive_files,
                'metadata': {
                    'created': datetime.now().isoformat(),
                    'drive_label': drive_label,
                    'drive_path': drive_path,
                    'total_files': file_count,
                    'total_size': drive_size,
                },
            }

            manifest_path = self.manifests_dir / f"{drive_label}_source_manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(manifest_data, f, indent=2)

            logger.info(
                f"Drive {drive_label}: {file_count:,} files, "
                f"{format_bytes(drive_size)}, manifest: {manifest_path}"
            )

            results['total_files'] += file_count
            results['total_size'] += drive_size
            results['drives_scanned'] += 1
            results['manifests'][drive_label] = str(manifest_path)
            results['per_drive'].append({
                'label': drive_label,
                'path': drive_path,
                'files': file_count,
                'size': drive_size,
            })

        logger.info(
            f"Scan complete: {results['total_files']:,} files, "
            f"{format_bytes(results['total_size'])} across "
            f"{results['drives_scanned']} drives"
        )
        return results

    def create_combined_manifest(self) -> str:
        """Merge per-drive _copied_manifest.json files into copied_files_combined.json.

        Returns the path to the combined manifest file.
        """
        combined_files: List[Dict[str, Any]] = []
        total_size = 0

        manifest_files = list(self.manifests_dir.glob("*_copied_manifest.json"))
        if not manifest_files:
            raise FileNotFoundError(
                f"No per-drive copied manifests found in {self.manifests_dir}. "
                "Run the copy phase first."
            )

        for manifest_path in manifest_files:
            logger.info(f"Loading manifest: {manifest_path.name}")
            with open(manifest_path, 'r') as f:
                data = json.load(f)
            files = data.get('files', [])
            combined_files.extend(files)
            total_size += sum(f.get('size', 0) for f in files)

        combined = {
            'files': combined_files,
            'metadata': {
                'created': datetime.now().isoformat(),
                'total_files': len(combined_files),
                'total_size': total_size,
                'source_manifests': [p.name for p in manifest_files],
            },
        }

        output_path = self.manifests_dir / "copied_files_combined.json"
        with open(output_path, 'w') as f:
            json.dump(combined, f, indent=2)

        logger.info(
            f"Combined manifest created: {len(combined_files):,} files, "
            f"{format_bytes(total_size)} — {output_path}"
        )
        return str(output_path)
