"""Tests for media scanning and manifest creation."""

import json
from pathlib import Path

import pytest
import yaml

from photo_consolidator.config import Config
from photo_consolidator.media_scanner import MediaScanner


class TestScanSourceDrives:
    """Test source drive scanning."""

    def test_per_drive_manifest_created(self, sample_config, tmp_consolidation_root, tmp_path):
        """Scanning a drive creates a per-drive scan manifest."""
        drive_dir = tmp_path / 'drive_a'
        drive_dir.mkdir()
        (drive_dir / 'photo1.jpg').write_bytes(b'jpg1')
        (drive_dir / 'subdir').mkdir()
        (drive_dir / 'subdir' / 'photo2.png').write_bytes(b'png-data')

        config_data = yaml.safe_load(open(sample_config.config_path))
        config_data['infrastructure']['storage']['source_drives'] = [
            {'path': str(drive_dir), 'label': 'drive_a'}
        ]

        config_path = tmp_path / 'config_scan.yml'
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        config = Config(str(config_path))
        scanner = MediaScanner(config)
        results = scanner.scan_source_drives()

        assert results['total_files'] == 2
        assert results['drives_scanned'] == 1

        manifest_path = tmp_consolidation_root / 'manifests' / 'drive_a_source_manifest.json'
        assert manifest_path.exists()

        with open(manifest_path) as f:
            manifest = json.load(f)

        assert manifest['metadata']['total_files'] == 2
        paths = [e['relative_path'] for e in manifest['files']]
        extensions = [Path(p).suffix.lower() for p in paths]
        assert '.jpg' in extensions
        assert '.png' in extensions

    def test_non_media_files_excluded(self, sample_config, tmp_consolidation_root, tmp_path):
        """Non-media files (txt, pdf, etc.) should not appear in scan results."""
        drive_dir = tmp_path / 'drive_b'
        drive_dir.mkdir()
        (drive_dir / 'photo.jpg').write_bytes(b'jpg')
        (drive_dir / 'readme.txt').write_bytes(b'text')
        (drive_dir / 'document.pdf').write_bytes(b'pdf')

        config_data = yaml.safe_load(open(sample_config.config_path))
        config_data['infrastructure']['storage']['source_drives'] = [
            {'path': str(drive_dir), 'label': 'drive_b'}
        ]

        config_path = tmp_path / 'config_filter.yml'
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        config = Config(str(config_path))
        scanner = MediaScanner(config)
        results = scanner.scan_source_drives()

        assert results['total_files'] == 1  # only jpg

    def test_inaccessible_drive_error(self, sample_config, tmp_consolidation_root, tmp_path):
        """Non-existent drive path should produce an error, not crash."""
        config_data = yaml.safe_load(open(sample_config.config_path))
        config_data['infrastructure']['storage']['source_drives'] = [
            {'path': '/nonexistent/drive/path', 'label': 'missing'}
        ]

        config_path = tmp_path / 'config_missing.yml'
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        config = Config(str(config_path))
        scanner = MediaScanner(config)
        results = scanner.scan_source_drives()

        assert results['total_files'] == 0
        assert results['drives_scanned'] == 0
        assert len(results['errors']) == 1
        assert 'not accessible' in results['errors'][0]


class TestCombinedManifest:
    """Test combining per-drive manifests."""

    def test_merges_multiple_drive_manifests(self, sample_config, tmp_consolidation_root):
        """Combined manifest should contain files from all per-drive manifests."""
        manifests_dir = tmp_consolidation_root / 'manifests'

        for label, count in [('drv1', 3), ('drv2', 2)]:
            data = {
                'files': [
                    {'path': f'/data/incoming/{label}/file{i}.jpg',
                     'relative_path': f'file{i}.jpg',
                     'size': 1000 * (i + 1),
                     'hash': f'{label}_hash_{i}'}
                    for i in range(count)
                ],
                'metadata': {'total_files': count},
            }
            with open(manifests_dir / f'{label}_copied_manifest.json', 'w') as f:
                json.dump(data, f)

        scanner = MediaScanner(sample_config)
        combined_path = scanner.create_combined_manifest()

        with open(combined_path) as f:
            combined = json.load(f)

        assert combined['metadata']['total_files'] == 5
        assert len(combined['files']) == 5

    def test_raises_when_no_manifests_exist(self, sample_config, tmp_consolidation_root):
        """Should raise FileNotFoundError when no per-drive manifests found."""
        # Ensure manifests dir is empty (remove any glob matches)
        manifests_dir = tmp_consolidation_root / 'manifests'
        for f in manifests_dir.glob('*_copied_manifest.json'):
            f.unlink()

        scanner = MediaScanner(sample_config)

        with pytest.raises(FileNotFoundError, match="No per-drive copied manifests"):
            scanner.create_combined_manifest()
