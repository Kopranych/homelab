"""Tests for photo consolidation logic."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from photo_consolidator.config import Config
from photo_consolidator.consolidator import PhotoConsolidator, ConsolidationStats
from photo_consolidator.utils import extract_photo_date


class TestGroupReportParsing:
    """Test parsing of duplicate group report files (Bug 1 regression tests)."""

    def test_parses_keep_file_from_multiline_report(
        self, sample_config, tmp_consolidation_root, sample_group_report, create_test_files
    ):
        """Regression test for Bug 1: KEEP and Full: are on separate lines."""
        keep_file = create_test_files('drv/photos/best.jpg', b'best-content')
        remove_file = create_test_files('drv/photos/worse.jpg', b'worse-content')

        sample_group_report(1, [
            {'action': 'KEEP', 'path': str(keep_file), 'score': 85},
            {'action': 'REMOVE', 'path': str(remove_file), 'score': 50},
        ])

        consolidator = PhotoConsolidator(sample_config)
        stats = ConsolidationStats()
        group_file = tmp_consolidation_root / 'duplicates' / 'groups' / 'group_00001.txt'
        consolidator._process_single_group(group_file, stats, dry_run=True)

        # In dry-run the parser should still find best_file and files_to_remove
        # If Bug 1 were present, best_file would be None and we'd get 0 processed
        assert stats.total_processed > 0, "Parser should find files in multiline report"

    def test_multiple_remove_files(
        self, sample_config, tmp_consolidation_root, sample_group_report, create_test_files
    ):
        keep = create_test_files('drv/photos/best.jpg', b'best')
        rm1 = create_test_files('drv/photos/dup1.jpg', b'dup1')
        rm2 = create_test_files('drv/photos/dup2.jpg', b'dup2')

        sample_group_report(2, [
            {'action': 'KEEP', 'path': str(keep), 'score': 90},
            {'action': 'REMOVE', 'path': str(rm1), 'score': 60},
            {'action': 'REMOVE', 'path': str(rm2), 'score': 55},
        ])

        consolidator = PhotoConsolidator(sample_config)
        stats = ConsolidationStats()
        group_file = tmp_consolidation_root / 'duplicates' / 'groups' / 'group_00002.txt'
        consolidator._process_single_group(group_file, stats, dry_run=True)

        # 1 keep + 2 removes = 3 processed
        assert stats.total_processed == 3
        assert stats.files_removed == 2

    def test_missing_group_file_logs_warning(
        self, sample_config, tmp_consolidation_root, caplog
    ):
        consolidator = PhotoConsolidator(sample_config)
        stats = ConsolidationStats()
        fake_file = tmp_consolidation_root / 'duplicates' / 'groups' / 'group_99999.txt'

        with pytest.raises(Exception):
            consolidator._process_single_group(fake_file, stats, dry_run=True)

    def test_empty_group_file_returns_early(
        self, sample_config, tmp_consolidation_root, caplog
    ):
        groups_dir = tmp_consolidation_root / 'duplicates' / 'groups'
        empty_file = groups_dir / 'group_00099.txt'
        empty_file.write_text('', encoding='utf-8')

        consolidator = PhotoConsolidator(sample_config)
        stats = ConsolidationStats()
        consolidator._process_single_group(empty_file, stats, dry_run=True)

        assert stats.total_processed == 0


class TestPathManipulation:
    """Test that drive label is stripped from final destination path."""

    def test_drive_prefix_stripped(
        self, sample_config, tmp_consolidation_root, sample_group_report, create_test_files
    ):
        keep = create_test_files('sdb1/vacation/photo.jpg', b'photo-data')

        sample_group_report(1, [
            {'action': 'KEEP', 'path': str(keep), 'score': 80},
        ])

        consolidator = PhotoConsolidator(sample_config)
        stats = ConsolidationStats()
        group_file = tmp_consolidation_root / 'duplicates' / 'groups' / 'group_00001.txt'

        # Run live (not dry-run) to actually copy
        consolidator._process_single_group(group_file, stats, dry_run=False)

        # Final path should NOT have 'sdb1' prefix
        final_file = tmp_consolidation_root / 'final' / 'vacation' / 'photo.jpg'
        assert final_file.exists(), f"Expected {final_file} to exist"
        assert final_file.read_bytes() == b'photo-data'


class TestDryRun:
    """Test that dry run doesn't copy or remove files."""

    def test_dry_run_no_files_copied_or_removed(
        self, sample_config, tmp_consolidation_root, sample_group_report, create_test_files
    ):
        keep = create_test_files('drv/photos/best.jpg', b'best')
        remove = create_test_files('drv/photos/worse.jpg', b'worse')

        sample_group_report(1, [
            {'action': 'KEEP', 'path': str(keep), 'score': 85},
            {'action': 'REMOVE', 'path': str(remove), 'score': 50},
        ])

        consolidator = PhotoConsolidator(sample_config)
        stats = ConsolidationStats()
        group_file = tmp_consolidation_root / 'duplicates' / 'groups' / 'group_00001.txt'
        consolidator._process_single_group(group_file, stats, dry_run=True)

        # No files should appear in final/
        final_files = list((tmp_consolidation_root / 'final').rglob('*'))
        final_files = [f for f in final_files if f.is_file()]
        assert len(final_files) == 0

        # Remove target should still exist
        assert remove.exists()


class TestUniqueFileProcessing:
    """Test that unique files are copied to final directory."""

    def test_unique_files_copied_to_final(
        self, sample_config, tmp_consolidation_root, sample_manifest, create_test_files
    ):
        from photo_consolidator.utils import calculate_sha256

        f1 = create_test_files('drv/photos/unique1.jpg', b'unique-content-1')
        f2 = create_test_files('drv/photos/unique2.jpg', b'unique-content-2')

        h1 = calculate_sha256(f1)
        h2 = calculate_sha256(f2)

        sample_manifest([
            {'path': str(f1), 'relative_path': 'drv/photos/unique1.jpg',
             'size': f1.stat().st_size, 'hash': h1},
            {'path': str(f2), 'relative_path': 'drv/photos/unique2.jpg',
             'size': f2.stat().st_size, 'hash': h2},
        ])

        consolidator = PhotoConsolidator(sample_config)
        stats = ConsolidationStats()
        consolidator._process_unique_files(stats, dry_run=False)

        # Both unique files should be in final/ (with or without date suffix)
        final_dir = tmp_consolidation_root / 'final'
        final_files = list(final_dir.rglob('unique*.jpg'))
        assert len(final_files) == 2
        assert stats.unique_files_copied == 2


class TestDateSuffix:
    """Test EXIF date suffix on folder names."""

    def test_date_suffix_added_when_exif_present(
        self, sample_config, tmp_consolidation_root, sample_group_report, create_test_files
    ):
        keep = create_test_files('drv/vacation/photo.jpg', b'photo-data')

        sample_group_report(1, [
            {'action': 'KEEP', 'path': str(keep), 'score': 80},
        ])

        consolidator = PhotoConsolidator(sample_config)
        stats = ConsolidationStats()
        group_file = tmp_consolidation_root / 'duplicates' / 'groups' / 'group_00001.txt'

        with patch('photo_consolidator.consolidator.extract_photo_date', return_value=(2020, 7)):
            consolidator._process_single_group(group_file, stats, dry_run=False)

        final_file = tmp_consolidation_root / 'final' / 'vacation_2020-07' / 'photo.jpg'
        assert final_file.exists(), f"Expected {final_file}, found: {list((tmp_consolidation_root / 'final').rglob('*'))}"

    def test_no_suffix_when_no_exif(
        self, sample_config, tmp_consolidation_root, sample_group_report, create_test_files
    ):
        keep = create_test_files('drv/vacation/photo.jpg', b'photo-data')

        sample_group_report(1, [
            {'action': 'KEEP', 'path': str(keep), 'score': 80},
        ])

        consolidator = PhotoConsolidator(sample_config)
        stats = ConsolidationStats()
        group_file = tmp_consolidation_root / 'duplicates' / 'groups' / 'group_00001.txt'

        with patch('photo_consolidator.consolidator.extract_photo_date', return_value=None):
            consolidator._process_single_group(group_file, stats, dry_run=False)

        final_file = tmp_consolidation_root / 'final' / 'vacation' / 'photo.jpg'
        assert final_file.exists()

    def test_date_suffix_in_dry_run(
        self, sample_config, tmp_consolidation_root, sample_group_report, create_test_files
    ):
        keep = create_test_files('drv/vacation/photo.jpg', b'photo-data')

        sample_group_report(1, [
            {'action': 'KEEP', 'path': str(keep), 'score': 80},
        ])

        consolidator = PhotoConsolidator(sample_config)
        stats = ConsolidationStats()
        group_file = tmp_consolidation_root / 'duplicates' / 'groups' / 'group_00001.txt'

        with patch('photo_consolidator.consolidator.extract_photo_date', return_value=(2020, 7)):
            consolidator._process_single_group(group_file, stats, dry_run=True)

        # No files should be created in dry run
        final_files = list((tmp_consolidation_root / 'final').rglob('*.jpg'))
        assert len(final_files) == 0
        assert stats.total_processed > 0


class TestSafeDestPath:
    """Test that files with same path but different content are not overwritten."""

    def test_no_collision_first_file(self, sample_config, tmp_consolidation_root):
        consolidator = PhotoConsolidator(sample_config)
        dest = tmp_consolidation_root / 'final' / 'photos' / 'img.jpg'
        source = tmp_consolidation_root / 'incoming' / 'drv' / 'img.jpg'
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b'content-a')

        result = consolidator._safe_dest_path(dest, source)
        assert result == dest

    def test_same_content_no_rename(
        self, sample_config, tmp_consolidation_root
    ):
        """Same-size file at dest → treat as same file, no rename."""
        consolidator = PhotoConsolidator(sample_config)

        source = tmp_consolidation_root / 'incoming' / 'drv' / 'img.jpg'
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b'same-content')

        dest = tmp_consolidation_root / 'final' / 'photos' / 'img.jpg'
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b'same-content')  # same size

        result = consolidator._safe_dest_path(dest, source)
        assert result == dest

    def test_different_content_gets_renamed(
        self, sample_config, tmp_consolidation_root
    ):
        """Different-size file at dest → rename to avoid overwrite."""
        consolidator = PhotoConsolidator(sample_config)

        source = tmp_consolidation_root / 'incoming' / 'drv' / 'img.jpg'
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b'short')

        dest = tmp_consolidation_root / 'final' / 'photos' / 'img.jpg'
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b'different-and-longer-content')

        result = consolidator._safe_dest_path(dest, source)
        assert result == tmp_consolidation_root / 'final' / 'photos' / 'img_2.jpg'

    def test_multiple_collisions_increment_counter(
        self, sample_config, tmp_consolidation_root
    ):
        """Multiple collisions → _2, _3, etc."""
        consolidator = PhotoConsolidator(sample_config)

        source = tmp_consolidation_root / 'incoming' / 'drv' / 'img.jpg'
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b'new')

        dest_dir = tmp_consolidation_root / 'final' / 'photos'
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / 'img.jpg').write_bytes(b'existing-content-1')
        (dest_dir / 'img_2.jpg').write_bytes(b'existing-content-22')

        dest = dest_dir / 'img.jpg'
        result = consolidator._safe_dest_path(dest, source)
        assert result == dest_dir / 'img_3.jpg'

    def test_collision_in_full_group_processing(
        self, sample_config, tmp_consolidation_root, sample_group_report, create_test_files
    ):
        """End-to-end: two groups with same dest path but different content."""
        # Pre-create a file at the destination
        final_dir = tmp_consolidation_root / 'final' / 'photos'
        final_dir.mkdir(parents=True, exist_ok=True)
        (final_dir / 'img.jpg').write_bytes(b'already-here-different')

        keep = create_test_files('drv/photos/img.jpg', b'new-content')

        sample_group_report(1, [
            {'action': 'KEEP', 'path': str(keep), 'score': 80},
        ])

        consolidator = PhotoConsolidator(sample_config)
        stats = ConsolidationStats()
        group_file = tmp_consolidation_root / 'duplicates' / 'groups' / 'group_00001.txt'

        with patch('photo_consolidator.consolidator.extract_photo_date', return_value=None):
            consolidator._process_single_group(group_file, stats, dry_run=False)

        # Original file untouched
        assert (final_dir / 'img.jpg').read_bytes() == b'already-here-different'
        # New file saved with _2 suffix
        assert (final_dir / 'img_2.jpg').exists()
        assert (final_dir / 'img_2.jpg').read_bytes() == b'new-content'
