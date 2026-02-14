"""Tests for duplicate detection and quality scoring."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from photo_consolidator.config import Config
from photo_consolidator.duplicates import DuplicateDetector, DuplicateGroup, FileInfo


class TestQualityScoring:
    """Test quality score calculation."""

    def _make_detector(self, sample_config):
        return DuplicateDetector(sample_config)

    def _make_file(self, ext='jpg', size=1_000_000, path='/data/incoming/drv/photos/img.jpg'):
        return FileInfo(
            path=path,
            relative_path='drv/photos/img.jpg',
            size=size,
            hash='abc123',
            extension=ext,
        )

    def test_raw_file_gets_90_points(self, sample_config):
        detector = self._make_detector(sample_config)
        for ext in ['cr2', 'nef', 'arw', 'dng']:
            fi = self._make_file(ext=ext)
            score = detector._calculate_quality_score(fi)
            assert score >= 90, f"RAW extension {ext} should score >= 90, got {score}"

    def test_large_jpeg_gets_high_res_score(self, sample_config):
        detector = self._make_detector(sample_config)
        fi = self._make_file(ext='jpg', size=6 * 1024 * 1024)  # 6 MB > 5 MB threshold
        score = detector._calculate_quality_score(fi)
        assert score >= 75

    def test_small_jpeg_gets_standard_score(self, sample_config):
        detector = self._make_detector(sample_config)
        fi = self._make_file(ext='jpg', size=2 * 1024 * 1024)  # 2 MB < 5 MB threshold
        score = detector._calculate_quality_score(fi)
        assert score >= 60
        assert score < 75  # should not reach high-res tier

    def test_png_score(self, sample_config):
        detector = self._make_detector(sample_config)
        fi = self._make_file(ext='png')
        score = detector._calculate_quality_score(fi)
        assert score >= 65

    def test_heic_score(self, sample_config):
        detector = self._make_detector(sample_config)
        fi = self._make_file(ext='heic')
        score = detector._calculate_quality_score(fi)
        assert score >= 70

    def test_size_bonus_50mb_gets_10_points(self, sample_config):
        """Regression test for Bug 2: 50 MB file must get +10, not +5."""
        detector = self._make_detector(sample_config)
        # Use PNG to avoid JPEG size-based format score variation
        large = self._make_file(ext='png', size=60 * 1024 * 1024,
                                path='/data/incoming/drv/stuff/img.png')
        medium = self._make_file(ext='png', size=15 * 1024 * 1024,
                                 path='/data/incoming/drv/stuff/img.png')
        small = self._make_file(ext='png', size=1 * 1024 * 1024,
                                path='/data/incoming/drv/stuff/img.png')

        score_large = detector._calculate_quality_score(large)
        score_medium = detector._calculate_quality_score(medium)
        score_small = detector._calculate_quality_score(small)

        # large should get +10, medium should get +5, small gets +0
        assert score_large - score_small == 10, (
            f"60 MB file should be 10 points above 1 MB file, "
            f"got {score_large} vs {score_small}"
        )
        assert score_medium - score_small == 5, (
            f"15 MB file should be 5 points above 1 MB file, "
            f"got {score_medium} vs {score_small}"
        )

    def test_organized_folder_bonus(self, sample_config):
        detector = self._make_detector(sample_config)
        organized = self._make_file(path='/data/incoming/drv/vacation/img.jpg')
        neutral = self._make_file(path='/data/incoming/drv/stuff/img.jpg')
        score_org = detector._calculate_quality_score(organized)
        score_neu = detector._calculate_quality_score(neutral)
        assert score_org > score_neu

    def test_backup_folder_penalty(self, sample_config):
        detector = self._make_detector(sample_config)
        backup = self._make_file(path='/data/incoming/drv/backup/img.jpg')
        neutral = self._make_file(path='/data/incoming/drv/stuff/img.jpg')
        score_bak = detector._calculate_quality_score(backup)
        score_neu = detector._calculate_quality_score(neutral)
        assert score_bak < score_neu

    def test_score_clamped_0_to_100(self, sample_config):
        detector = self._make_detector(sample_config)
        # Junk folder with small unknown format → might go negative
        fi = self._make_file(ext='bmp', size=100, path='/data/incoming/drv/temp/x.bmp')
        score = detector._calculate_quality_score(fi)
        assert 0 <= score <= 100


class TestDuplicateDetection:
    """Test duplicate grouping logic."""

    def test_same_hash_grouped_together(self, sample_config, sample_manifest, create_test_files):
        detector = DuplicateDetector(sample_config)
        fa = create_test_files('drv/a.jpg', b'aaa')
        fb = create_test_files('drv/b.jpg', b'aaa')
        fc = create_test_files('drv/c.jpg', b'ccc')
        files = [
            {'path': str(fa), 'relative_path': 'drv/a.jpg',
             'size': 1000, 'hash': 'aaa'},
            {'path': str(fb), 'relative_path': 'drv/b.jpg',
             'size': 1000, 'hash': 'aaa'},
            {'path': str(fc), 'relative_path': 'drv/c.jpg',
             'size': 2000, 'hash': 'bbb'},
        ]
        sample_manifest(files)
        results = detector.analyze_duplicates()
        assert results['duplicate_groups'] == 1
        assert results['unique_files'] == 1

    def test_unique_files_not_grouped(self, sample_config, sample_manifest, create_test_files):
        detector = DuplicateDetector(sample_config)
        fa = create_test_files('drv/a.jpg', b'aaa')
        fb = create_test_files('drv/b.jpg', b'bbb')
        files = [
            {'path': str(fa), 'relative_path': 'drv/a.jpg',
             'size': 1000, 'hash': 'aaa'},
            {'path': str(fb), 'relative_path': 'drv/b.jpg',
             'size': 2000, 'hash': 'bbb'},
        ]
        sample_manifest(files)
        results = detector.analyze_duplicates()
        assert results['duplicate_groups'] == 0
        assert results['unique_files'] == 2

    def test_empty_hash_skipped(self, sample_config, sample_manifest, create_test_files):
        detector = DuplicateDetector(sample_config)
        fa = create_test_files('drv/a.jpg', b'aaa')
        files = [
            {'path': str(fa), 'relative_path': 'drv/a.jpg',
             'size': 1000, 'hash': ''},
        ]
        sample_manifest(files)
        results = detector.analyze_duplicates()
        assert results['duplicate_groups'] == 0
        assert results['unique_files'] == 0

    def test_best_file_has_highest_score(self, sample_config, sample_manifest, create_test_files):
        detector = DuplicateDetector(sample_config)
        f_small = create_test_files('drv/backup/small.jpg', b'sm')
        f_big = create_test_files('drv/vacation/big.cr2', b'x' * 100)
        files = [
            {'path': str(f_small), 'relative_path': 'drv/backup/small.jpg',
             'size': 100, 'hash': 'dup'},
            {'path': str(f_big), 'relative_path': 'drv/vacation/big.cr2',
             'size': 20_000_000, 'hash': 'dup'},
        ]
        sample_manifest(files)
        results = detector.analyze_duplicates()
        assert results['duplicate_groups'] == 1
        # Just check the report was generated
        groups_dir = Path(sample_config.get_consolidation_root()) / 'duplicates' / 'groups'
        group_files = list(groups_dir.glob('group_*.txt'))
        assert len(group_files) == 1
        content = group_files[0].read_text(encoding='utf-8')
        # First file entry should be KEEP
        assert content.index('KEEP') < content.index('REMOVE')


class TestSafetyCheck:
    """Test safety threshold checks."""

    def test_duplicate_percentage_uses_file_count_not_group_count(self, sample_config, sample_manifest, create_test_files):
        """Regression test for Bug 3: percentage should use file count, not group count."""
        detector = DuplicateDetector(sample_config)
        # 10 files total, 1 group with 6 duplicate files → 60% by files, 10% by groups
        for i in range(6):
            create_test_files(f'drv/dup{i}.jpg', f'dup{i}'.encode())
        for i in range(4):
            create_test_files(f'drv/unique{i}.jpg', f'uniq{i}'.encode())
        root = str(Path(sample_config.get_consolidation_root()) / 'incoming')
        files = [
            {'path': f'{root}/drv/dup{i}.jpg', 'relative_path': f'drv/dup{i}.jpg',
             'size': 1000 + i, 'hash': 'same_hash'}
            for i in range(6)
        ] + [
            {'path': f'{root}/drv/unique{i}.jpg', 'relative_path': f'drv/unique{i}.jpg',
             'size': 2000 + i, 'hash': f'unique_{i}'}
            for i in range(4)
        ]
        sample_manifest(files)
        results = detector.analyze_duplicates()

        # Should be 60% (6/10 files), not 10% (1 group / 10 files)
        assert results['duplicate_percentage'] == pytest.approx(60.0)

    def test_warning_when_threshold_exceeded(self, sample_config, sample_manifest, create_test_files):
        """When duplicate percentage exceeds max, a warning is issued."""
        detector = DuplicateDetector(sample_config)
        # Create enough duplicates to exceed 80% threshold
        for i in range(9):
            create_test_files(f'drv/dup{i}.jpg', f'dup{i}'.encode())
        create_test_files('drv/unique.jpg', b'unique')
        root = str(Path(sample_config.get_consolidation_root()) / 'incoming')
        files = [
            {'path': f'{root}/drv/dup{i}.jpg', 'relative_path': f'drv/dup{i}.jpg',
             'size': 1000 + i, 'hash': 'same'}
            for i in range(9)
        ] + [
            {'path': f'{root}/drv/unique.jpg', 'relative_path': 'drv/unique.jpg',
             'size': 5000, 'hash': 'only_one'},
        ]
        sample_manifest(files)
        results = detector.analyze_duplicates()
        assert len(results['warnings']) >= 1
        assert 'High duplicate percentage' in results['warnings'][0]
