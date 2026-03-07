"""Tests for file copying with verification."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from photo_consolidator.config import Config
from photo_consolidator.file_copier import FileCopier
from photo_consolidator.utils import calculate_sha256


class TestCopyWithVerification:
    """Test copy + hash verification (Bug 4 regression)."""

    def test_copied_file_has_correct_hash_in_manifest(
        self, sample_config, tmp_consolidation_root, tmp_path
    ):
        """Regression test for Bug 4: hash in manifest must match actual file content."""
        # Create a source drive with one file
        source_dir = tmp_path / 'source_drive'
        source_dir.mkdir()
        test_file = source_dir / 'photo.jpg'
        test_content = b'JPEG-like test content for hashing'
        test_file.write_bytes(test_content)

        # Configure source drive
        import yaml
        config_data = yaml.safe_load(open(sample_config.config_path))
        config_data['infrastructure']['storage']['source_drives'] = [
            {'path': str(source_dir), 'label': 'testdrive'}
        ]
        config_data['photo_consolidation']['extensions']['photos'] = ['jpg']
        config_data['photo_consolidation']['process']['dry_run'] = False
        config_data['photo_consolidation']['safety']['min_free_space_gb'] = 0

        config_path = tmp_path / 'config_copy.yml'
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        config = Config(str(config_path))
        copier = FileCopier(config)
        results = copier.copy_all_drives(dry_run=False)

        assert results['copied_files'] == 1
        assert results['failed_files'] == 0

        # Check manifest
        manifest_path = tmp_consolidation_root / 'manifests' / 'testdrive_copied_manifest.json'
        assert manifest_path.exists()

        with open(manifest_path) as f:
            manifest = json.load(f)

        entry = manifest['files'][0]
        dst_path = Path(entry['path'])
        assert dst_path.exists()

        # The hash in the manifest should match actual file hash
        actual_hash = calculate_sha256(dst_path)
        assert entry['hash'] == actual_hash
        assert actual_hash != ''

    def test_skip_existing_same_size_file(
        self, sample_config, tmp_consolidation_root, tmp_path
    ):
        """Files already in incoming with same size are skipped."""
        source_dir = tmp_path / 'source_drive2'
        source_dir.mkdir()
        test_file = source_dir / 'photo.jpg'
        content = b'existing-file-content'
        test_file.write_bytes(content)

        # Pre-create destination with same content
        dest_file = tmp_consolidation_root / 'incoming' / 'testdrive2' / 'photo.jpg'
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        dest_file.write_bytes(content)

        import yaml
        config_data = yaml.safe_load(open(sample_config.config_path))
        config_data['infrastructure']['storage']['source_drives'] = [
            {'path': str(source_dir), 'label': 'testdrive2'}
        ]
        config_data['photo_consolidation']['extensions']['photos'] = ['jpg']
        config_data['photo_consolidation']['process']['dry_run'] = False
        config_data['photo_consolidation']['safety']['min_free_space_gb'] = 0

        config_path = tmp_path / 'config_skip.yml'
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        config = Config(str(config_path))
        copier = FileCopier(config)
        results = copier.copy_all_drives(dry_run=False)

        assert results['skipped_files'] == 1
        assert results['copied_files'] == 0

    def test_dry_run_copies_nothing(self, sample_config, tmp_consolidation_root, tmp_path):
        source_dir = tmp_path / 'source_drive3'
        source_dir.mkdir()
        (source_dir / 'photo.jpg').write_bytes(b'data')

        import yaml
        config_data = yaml.safe_load(open(sample_config.config_path))
        config_data['infrastructure']['storage']['source_drives'] = [
            {'path': str(source_dir), 'label': 'testdrive3'}
        ]
        config_data['photo_consolidation']['extensions']['photos'] = ['jpg']

        config_path = tmp_path / 'config_dry.yml'
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        config = Config(str(config_path))
        copier = FileCopier(config)
        results = copier.copy_all_drives(dry_run=True)

        assert results['copied_files'] == 1  # counted but not physically copied
        # No manifest written in dry-run
        manifest_path = tmp_consolidation_root / 'manifests' / 'testdrive3_copied_manifest.json'
        assert not manifest_path.exists()


class TestSpaceCheck:
    """Test disk space verification."""

    def test_insufficient_space_returns_error(
        self, sample_config, tmp_consolidation_root, tmp_path
    ):
        source_dir = tmp_path / 'source_big'
        source_dir.mkdir()
        (source_dir / 'photo.jpg').write_bytes(b'x' * 1000)

        import yaml
        config_data = yaml.safe_load(open(sample_config.config_path))
        config_data['infrastructure']['storage']['source_drives'] = [
            {'path': str(source_dir), 'label': 'bigdrive'}
        ]
        config_data['photo_consolidation']['extensions']['photos'] = ['jpg']
        config_data['photo_consolidation']['process']['dry_run'] = False

        config_path = tmp_path / 'config_space.yml'
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        config = Config(str(config_path))
        copier = FileCopier(config)

        # Mock get_available_space to return very little
        with patch('photo_consolidator.file_copier.get_available_space', return_value=1):
            results = copier.copy_all_drives(dry_run=False)

        assert results['copied_files'] == 0
        assert len(results['errors']) > 0
        assert 'Insufficient space' in results['errors'][0]
