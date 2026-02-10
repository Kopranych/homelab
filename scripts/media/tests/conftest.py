"""Shared fixtures for photo consolidation tests."""

import json
import os
import textwrap
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml


@pytest.fixture
def tmp_consolidation_root(tmp_path):
    """Create a temporary consolidation directory tree."""
    dirs = ['incoming', 'duplicates/reports', 'duplicates/groups',
            'final', 'manifests', 'logs', 'backup/consolidation']
    for d in dirs:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def sample_config(tmp_consolidation_root, tmp_path):
    """Create a Config-compatible object backed by a temp config file."""
    config_data = {
        'infrastructure': {
            'storage': {
                'data_root': str(tmp_path),
                'consolidation_root': str(tmp_consolidation_root),
                'source_drives': [],
            }
        },
        'photo_consolidation': {
            'extensions': {
                'photos': ['jpg', 'jpeg', 'png', 'heic', 'heif',
                           'cr2', 'nef', 'arw', 'dng'],
                'videos': ['mp4', 'mov', 'avi', 'mkv'],
            },
            'quality': {
                'format_scores': {
                    'raw_files': 90,
                    'high_res_jpg': 75,
                    'standard_jpg': 60,
                    'png': 65,
                    'heic': 70,
                    'videos_hd': 70,
                    'videos_sd': 50,
                },
                'folder_bonuses': {
                    'organized': 10,
                    'meaningful': 5,
                    'backup': -10,
                    'junk': -15,
                },
                'size_thresholds': {
                    'photo_large_mb': 5,
                    'video_large_mb': 100,
                },
            },
            'safety': {
                'min_free_space_gb': 100,
                'max_duplicate_percentage': 80,
                'backup_before_removal': False,
            },
            'process': {
                'parallel_jobs': 4,
                'preserve_structure': True,
                'dry_run': True,
            },
        },
    }

    config_path = tmp_path / 'config.yml'
    with open(config_path, 'w') as f:
        yaml.dump(config_data, f)

    from photo_consolidator.config import Config
    return Config(str(config_path))


@pytest.fixture
def create_test_files(tmp_consolidation_root):
    """Factory fixture: create files in the consolidation tree with given content."""

    def _create(relative_path, content=b'test-content', base='incoming'):
        full_path = tmp_consolidation_root / base / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)
        return full_path

    return _create


@pytest.fixture
def sample_manifest(tmp_consolidation_root):
    """Factory fixture: write a JSON manifest file and return its path."""

    def _write(files, filename='copied_files_combined.json'):
        manifest = {
            'files': files,
            'metadata': {
                'created': '2024-01-01T00:00:00',
                'total_files': len(files),
                'total_size': sum(f.get('size', 0) for f in files),
            },
        }
        manifest_path = tmp_consolidation_root / 'manifests' / filename
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)
        return manifest_path

    return _write


@pytest.fixture
def sample_group_report(tmp_consolidation_root):
    """Factory fixture: write a group report file and return its path."""

    def _write(group_number, entries):
        """Write a group report.

        entries: list of dicts with keys 'action' ('KEEP'/'REMOVE'),
                 'path', 'score', 'size', 'ext', 'folder'.
        """
        groups_dir = tmp_consolidation_root / 'duplicates' / 'groups'
        groups_dir.mkdir(parents=True, exist_ok=True)
        group_file = groups_dir / f'group_{group_number:05d}.txt'

        lines = [
            f"=== Duplicate Group {group_number:05d} ===",
            f"Hash: abc123",
            f"Files: {len(entries)}",
            f"Total size: 10MB",
            f"Space savings: 5MB",
            "",
            "Files ranked by quality (KEEP first, REMOVE others):",
            "",
        ]

        for i, entry in enumerate(entries):
            action = entry['action']
            score = entry.get('score', 75)
            indicator = " \U0001f3af BEST QUALITY" if action == 'KEEP' else ""
            lines.append(f"[{i+1}] {action} - Score: {score}/100{indicator}")
            lines.append(f"    Full: {entry['path']}")
            lines.append(f"    Size: {entry.get('size', '5MB')}")
            lines.append(f"    Format: {entry.get('ext', 'JPG')}")
            lines.append(f"    Folder: {entry.get('folder', 'photos')}")
            lines.append("")

        lines.append(f"Recommendation: Keep file [1], remove files [2-{len(entries)}]")
        lines.append(f"Space saved by removing duplicates: 5MB")

        group_file.write_text('\n'.join(lines), encoding='utf-8')
        return group_file

    return _write
