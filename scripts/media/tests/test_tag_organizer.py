"""Tests for tag_organizer.py — Nextcloud tag-based photo mover."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# tag_organizer.py is a script in the parent directory, not a package module.
# psycopg2 is not installed on the dev machine, so stub it out before import.
# sys.path.insert(0, str(Path(__file__).parent.parent))
# if 'psycopg2' not in sys.modules:
#     sys.modules['psycopg2'] = MagicMock()
import tag_organizer


# ── Helpers ───────────────────────────────────────────────────────────────────

def _http(status_code, text=''):
    """Minimal requests.Response stand-in."""
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    return r


def _db_mock(rows):
    """Return (mock_connect, mock_cursor) with fetchall() yielding rows."""
    cur = MagicMock()
    cur.fetchall.return_value = rows
    conn = MagicMock()
    conn.cursor.return_value = cur
    return MagicMock(return_value=conn), cur


# ── format_bytes ──────────────────────────────────────────────────────────────

class TestFormatBytes:

    def test_should_format_zero_bytes(self):
        assert tag_organizer.format_bytes(0) == '0.0 B'

    def test_should_format_bytes_when_below_1024(self):
        assert tag_organizer.format_bytes(500) == '500.0 B'
        assert tag_organizer.format_bytes(1023) == '1023.0 B'

    def test_should_format_kilobytes_when_exactly_1024(self):
        assert tag_organizer.format_bytes(1024) == '1.0 KB'

    def test_should_format_fractional_kilobytes(self):
        assert tag_organizer.format_bytes(1536) == '1.5 KB'

    def test_should_format_megabytes_when_value_is_megabyte(self):
        assert tag_organizer.format_bytes(1024 ** 2) == '1.0 MB'
        assert tag_organizer.format_bytes(5 * 1024 ** 2) == '5.0 MB'

    def test_should_format_gigabytes_when_value_is_gigabyte(self):
        assert tag_organizer.format_bytes(1024 ** 3) == '1.0 GB'

    def test_should_format_terabytes_when_value_is_terabyte(self):
        assert tag_organizer.format_bytes(1024 ** 4) == '1.0 TB'


# ── get_tagged_items ──────────────────────────────────────────────────────────

class TestGetTaggedItems:

    def test_should_return_files(self):
        rows = [
            ('Photos/Wedding/IMG_001.JPG', 1_048_576),
            ('Photos/Anna/IMG_002.JPG',   2_097_152),
        ]
        mock_connect, _ = _db_mock(rows)

        with patch('tag_organizer.psycopg2.connect', mock_connect):
            result = tag_organizer.get_tagged_items('wedding')

        assert len(result) == 2
        assert result[0] == {'path': 'Photos/Wedding/IMG_001.JPG', 'size': 1_048_576}
        assert result[1] == {'path': 'Photos/Anna/IMG_002.JPG',   'size': 2_097_152}

    def test_should_return_empty_list_when_tag_has_no_matches(self):
        mock_connect, _ = _db_mock([])

        with patch('tag_organizer.psycopg2.connect', mock_connect):
            result = tag_organizer.get_tagged_items('nonexistent')

        assert result == []

    def test_should_use_zero_size_when_db_returns_none(self):
        mock_connect, _ = _db_mock([('Photos/file.JPG', None)])

        with patch('tag_organizer.psycopg2.connect', mock_connect):
            result = tag_organizer.get_tagged_items('wedding')

        assert result[0]['size'] == 0

    def test_should_query_db_with_correct_tag_name(self):
        mock_connect, cur = _db_mock([])

        with patch('tag_organizer.psycopg2.connect', mock_connect):
            tag_organizer.get_tagged_items('vacation_2021')

        cur.execute.assert_called_once()
        _, params = cur.execute.call_args[0]
        assert params == ('vacation_2021',)

    def test_should_close_connection_after_query(self):
        mock_connect, cur = _db_mock([])

        with patch('tag_organizer.psycopg2.connect', mock_connect):
            tag_organizer.get_tagged_items('wedding')

        cur.close.assert_called_once()
        mock_connect.return_value.close.assert_called_once()


# ── _webdav_url ───────────────────────────────────────────────────────────────

class TestWebdavUrl:

    def test_should_return_base_plus_ascii_path_unchanged(self):
        url = tag_organizer._webdav_url('Consolidated/Photos/Wedding')
        assert url == f"{tag_organizer.WEBDAV_BASE}/Consolidated/Photos/Wedding"

    def test_should_percent_encode_cyrillic_characters(self):
        url = tag_organizer._webdav_url('Consolidated/Видео/img.jpg')
        assert 'Видео' not in url
        assert '%' in url

    def test_should_preserve_slash_separators(self):
        url = tag_organizer._webdav_url('a/b/c')
        assert url.endswith('/a/b/c')

    def test_should_encode_spaces_in_path(self):
        url = tag_organizer._webdav_url('Consolidated/Видео Жени/img.jpg')
        assert ' ' not in url
        assert 'Видео' not in url


# ── ensure_folder ─────────────────────────────────────────────────────────────

class TestEnsureFolder:

    def test_should_succeed_when_folder_created_201(self):
        with patch('tag_organizer.requests.request', return_value=_http(201)):
            tag_organizer.ensure_folder('Consolidated/Photos/Wedding')  # no exception

    def test_should_succeed_when_folder_already_exists_405(self):
        with patch('tag_organizer.requests.request', return_value=_http(405)):
            tag_organizer.ensure_folder('Consolidated/Photos/Wedding')  # no exception

    def test_should_send_mkcol_for_each_path_component(self):
        with patch('tag_organizer.requests.request', return_value=_http(405)) as mock_req:
            tag_organizer.ensure_folder('Consolidated/Photos/Wedding')

        assert mock_req.call_count == 3
        methods = [c[0][0] for c in mock_req.call_args_list]
        assert all(m == 'MKCOL' for m in methods)

    def test_should_create_components_from_root_to_leaf(self):
        with patch('tag_organizer.requests.request', return_value=_http(405)) as mock_req:
            tag_organizer.ensure_folder('Consolidated/Photos/Vacation2021')

        urls = [c[0][1] for c in mock_req.call_args_list]
        assert urls[0].endswith('/Consolidated')
        assert urls[1].endswith('/Consolidated/Photos')
        assert urls[2].endswith('/Consolidated/Photos/Vacation2021')

    def test_should_raise_when_mkcol_returns_error_status(self):
        with patch('tag_organizer.requests.request', return_value=_http(500, 'server error')):
            with pytest.raises(RuntimeError, match='MKCOL failed'):
                tag_organizer.ensure_folder('Consolidated/Photos/Wedding')

    def test_should_stop_at_failing_component_when_nested_path(self):
        """Raise on first MKCOL error, not after processing all components."""
        responses = [_http(405), _http(500)]
        with patch('tag_organizer.requests.request', side_effect=responses) as mock_req:
            with pytest.raises(RuntimeError):
                tag_organizer.ensure_folder('Consolidated/Photos/Wedding')

        assert mock_req.call_count == 2  # stopped after second component failed

    def test_should_percent_encode_cyrillic_in_mkcol_url(self):
        with patch('tag_organizer.requests.request', return_value=_http(201)) as mock_req:
            tag_organizer.ensure_folder('Consolidated/Видео/Жени')

        urls = [c[0][1] for c in mock_req.call_args_list]
        for url in urls:
            assert 'Видео' not in url
            assert 'Жени' not in url


# ── _dest_subpath ─────────────────────────────────────────────────────────────

class TestDestSubpath:

    def test_should_return_empty_subfolder_when_keep_parents_0(self):
        sf, fn = tag_organizer._dest_subpath('Photos/iPhone/202207__/img.jpg', 0)
        assert sf == ''
        assert fn == 'img.jpg'

    def test_should_return_one_parent_when_keep_parents_1(self):
        sf, fn = tag_organizer._dest_subpath('Photos/iPhone/202207__/img.jpg', 1)
        assert sf == '202207__'
        assert fn == 'img.jpg'

    def test_should_return_two_parents_when_keep_parents_2(self):
        sf, fn = tag_organizer._dest_subpath('Photos/iPhone/202207__/img.jpg', 2)
        assert sf == 'iPhone/202207__'
        assert fn == 'img.jpg'

    def test_should_clamp_when_keep_parents_exceeds_path_depth(self):
        sf, fn = tag_organizer._dest_subpath('Photos/img.jpg', 5)
        assert sf == 'Photos'
        assert fn == 'img.jpg'

    def test_should_return_empty_subfolder_when_file_has_no_parent(self):
        sf, fn = tag_organizer._dest_subpath('img.jpg', 2)
        assert sf == ''
        assert fn == 'img.jpg'


# ── move_file ─────────────────────────────────────────────────────────────────

class TestMoveFile:

    def test_should_return_skipped_when_already_at_destination(self):
        # File DB path already matches the computed destination — no HTTP call
        with patch('tag_organizer.requests.request') as mock_req:
            status, name = tag_organizer.move_file(
                'Photos/Wedding/IMG_001.JPG',
                'Consolidated/Photos/Wedding',
                keep_parents=0,
            )

        mock_req.assert_not_called()
        assert status == 'skipped'
        assert name == 'IMG_001.JPG'

    def test_should_return_skipped_with_subfolder_when_already_at_destination(self):
        # keep_parents=1: file is already at Wedding/202207__/img.jpg
        with patch('tag_organizer.requests.request') as mock_req:
            status, name = tag_organizer.move_file(
                'Photos/Wedding/202207__/img.jpg',
                'Consolidated/Photos/Wedding',
                keep_parents=1,
            )

        mock_req.assert_not_called()
        assert status == 'skipped'
        assert name == '202207__/img.jpg'

    def test_should_return_moved_when_201(self):
        with patch('tag_organizer.requests.request', return_value=_http(201)):
            status, name = tag_organizer.move_file(
                'Photos/Album/IMG_001.JPG', 'Consolidated/Photos/Wedding'
            )

        assert status == 'moved'
        assert name == 'IMG_001.JPG'

    def test_should_return_moved_when_204(self):
        with patch('tag_organizer.requests.request', return_value=_http(204)):
            status, name = tag_organizer.move_file(
                'Photos/Album/IMG_001.JPG', 'Consolidated/Photos/Wedding'
            )

        assert status == 'moved'
        assert name == 'IMG_001.JPG'

    def test_should_return_renamed_when_first_name_collides(self):
        responses = [_http(412), _http(201)]  # IMG_001.JPG taken, IMG_001_2.JPG free
        with patch('tag_organizer.requests.request', side_effect=responses):
            status, name = tag_organizer.move_file(
                'Photos/Album/IMG_001.JPG', 'Consolidated/Photos/Wedding'
            )

        assert status == 'renamed'
        assert name == 'IMG_001_2.JPG'

    def test_should_keep_trying_suffixes_when_multiple_collisions(self):
        responses = [_http(412), _http(412), _http(412), _http(201)]
        with patch('tag_organizer.requests.request', side_effect=responses):
            status, name = tag_organizer.move_file(
                'Photos/Album/IMG_001.JPG', 'Consolidated/Photos/Wedding'
            )

        assert status == 'renamed'
        assert name == 'IMG_001_4.JPG'

    def test_should_preserve_extension_in_renamed_file(self):
        responses = [_http(412), _http(201)]
        with patch('tag_organizer.requests.request', side_effect=responses):
            _, name = tag_organizer.move_file(
                'Photos/Album/photo.HEIC', 'Consolidated/Photos/Wedding'
            )

        assert name == 'photo_2.HEIC'

    def test_should_return_failed_when_http_error(self):
        with patch('tag_organizer.requests.request', return_value=_http(500)):
            status, name = tag_organizer.move_file(
                'Photos/Album/IMG_001.JPG', 'Consolidated/Photos/Wedding'
            )

        assert status == 'failed'
        assert name == 'IMG_001.JPG'

    def test_should_return_failed_when_all_99_suffixes_taken(self):
        with patch('tag_organizer.requests.request', return_value=_http(412)):
            status, name = tag_organizer.move_file(
                'Photos/Album/IMG_001.JPG', 'Consolidated/Photos/Wedding'
            )

        assert status == 'failed'
        assert name == 'IMG_001.JPG'

    def test_should_include_webdav_root_in_src_url(self):
        with patch('tag_organizer.requests.request', return_value=_http(201)) as mock_req:
            tag_organizer.move_file(
                'Photos/iPhone_Anna/IMG_001.JPG', 'Consolidated/Photos/Wedding'
            )

        src_url = mock_req.call_args[0][1]
        assert 'Consolidated/Photos/iPhone_Anna/IMG_001.JPG' in src_url

    def test_should_use_correct_destination_url(self):
        with patch('tag_organizer.requests.request', return_value=_http(201)) as mock_req:
            tag_organizer.move_file(
                'Photos/iPhone_Anna/IMG_001.JPG', 'Consolidated/Photos/Wedding'
            )

        headers = mock_req.call_args[1]['headers']
        assert 'Consolidated/Photos/Wedding/IMG_001.JPG' in headers['Destination']

    def test_should_send_overwrite_false_header(self):
        with patch('tag_organizer.requests.request', return_value=_http(201)) as mock_req:
            tag_organizer.move_file('Photos/IMG_001.JPG', 'Consolidated/Photos/Wedding')

        headers = mock_req.call_args[1]['headers']
        assert headers['Overwrite'] == 'F'

    def test_should_percent_encode_cyrillic_in_src_url(self):
        with patch('tag_organizer.requests.request', return_value=_http(201)) as mock_req:
            tag_organizer.move_file(
                'Photos/Свадьба/img.jpg', 'Consolidated/Photos/Wedding'
            )

        src_url = mock_req.call_args[0][1]
        assert 'Свадьба' not in src_url
        assert '%' in src_url

    def test_should_percent_encode_cyrillic_in_destination_header(self):
        with patch('tag_organizer.requests.request', return_value=_http(201)) as mock_req:
            tag_organizer.move_file(
                'Photos/iPhone/Видео Жени/img.jpg',
                'Consolidated/Photos/Wedding',
                keep_parents=1,
            )

        dst = mock_req.call_args[1]['headers']['Destination']
        assert 'Видео' not in dst
        assert ' ' not in dst
        assert '%' in dst


# ── move_file with keep_parents ───────────────────────────────────────────────

class TestMoveFileWithParents:

    def test_should_return_subfolder_path_when_keep_parents_1(self):
        with patch('tag_organizer.requests.request', return_value=_http(201)):
            status, dest = tag_organizer.move_file(
                'Photos/iPhone/202207__/img.jpg',
                'Consolidated/Photos/Wedding',
                keep_parents=1,
            )
        assert status == 'moved'
        assert dest == '202207__/img.jpg'

    def test_should_return_two_level_path_when_keep_parents_2(self):
        with patch('tag_organizer.requests.request', return_value=_http(201)):
            status, dest = tag_organizer.move_file(
                'Photos/iPhone/202207__/img.jpg',
                'Consolidated/Photos/Wedding',
                keep_parents=2,
            )
        assert status == 'moved'
        assert dest == 'iPhone/202207__/img.jpg'

    def test_should_include_subfolder_in_destination_url(self):
        with patch('tag_organizer.requests.request', return_value=_http(201)) as mock_req:
            tag_organizer.move_file(
                'Photos/iPhone/202207__/img.jpg',
                'Consolidated/Photos/Wedding',
                keep_parents=1,
            )
        headers = mock_req.call_args[1]['headers']
        assert 'Photos/Wedding/202207__/img.jpg' in headers['Destination']

    def test_should_rename_with_suffix_inside_subfolder_when_collision(self):
        responses = [_http(412), _http(201)]
        with patch('tag_organizer.requests.request', side_effect=responses):
            status, dest = tag_organizer.move_file(
                'Photos/iPhone/202207__/img.jpg',
                'Consolidated/Photos/Wedding',
                keep_parents=1,
            )
        assert status == 'renamed'
        assert dest == '202207__/img_2.jpg'

    def test_should_use_flat_dest_when_keep_parents_0(self):
        with patch('tag_organizer.requests.request', return_value=_http(201)):
            status, dest = tag_organizer.move_file(
                'Photos/iPhone/202207__/img.jpg',
                'Consolidated/Photos/Wedding',
                keep_parents=0,
            )
        assert status == 'moved'
        assert dest == 'img.jpg'


# ── main ──────────────────────────────────────────────────────────────────────

class TestMain:

    _FILES = [
        {'path': 'Photos/iPhone_Anna/IMG_001.JPG', 'size': 1_000_000},
        {'path': 'Photos/iPhone_Ilya/DSC_001.JPG', 'size': 2_000_000},
    ]

    def test_should_not_call_ensure_folder_when_no_tagged_items(self):
        with patch('tag_organizer.get_tagged_items', return_value=[]), \
             patch('tag_organizer.ensure_folder') as mock_folder, \
             patch('tag_organizer.move_file') as mock_move:
            tag_organizer.main(tag='wedding', folder='Photos/Wedding')

        mock_folder.assert_not_called()
        mock_move.assert_not_called()

    def test_should_not_move_files_when_dry_run(self):
        with patch('tag_organizer.get_tagged_items', return_value=self._FILES), \
             patch('tag_organizer.ensure_folder') as mock_folder, \
             patch('tag_organizer.move_file') as mock_move:
            tag_organizer.main(tag='wedding', folder='Photos/Wedding', dry_run=True)

        mock_folder.assert_not_called()
        mock_move.assert_not_called()

    def test_should_write_json_report_after_run(self, tmp_path):
        with patch('tag_organizer.get_tagged_items', return_value=self._FILES), \
             patch('tag_organizer.ensure_folder'), \
             patch('tag_organizer.move_file', return_value=('moved', 'IMG_001.JPG')), \
             patch('tag_organizer.LOG_DIR', str(tmp_path)):
            tag_organizer.main(tag='wedding', folder='Photos/Wedding')

        reports = list(tmp_path.glob('tag_move_wedding_*.json'))
        assert len(reports) == 1
        data = json.loads(reports[0].read_text())
        assert data['tag'] == 'wedding'
        assert data['target_folder'] == 'Consolidated/Photos/Wedding'

    def test_should_count_all_moved_when_all_succeed(self, tmp_path):
        move_results = [('moved', 'IMG_001.JPG'), ('moved', 'DSC_001.JPG')]
        with patch('tag_organizer.get_tagged_items', return_value=self._FILES), \
             patch('tag_organizer.ensure_folder'), \
             patch('tag_organizer.move_file', side_effect=move_results), \
             patch('tag_organizer.LOG_DIR', str(tmp_path)):
            tag_organizer.main(tag='wedding', folder='Photos/Wedding')

        report = json.loads(list(tmp_path.glob('tag_move_*.json'))[0].read_text())
        assert report['summary']['files_moved']   == 2
        assert report['summary']['files_failed']  == 0

    def test_should_count_renamed_separately_from_moved(self, tmp_path):
        move_results = [('moved', 'IMG_001.JPG'), ('renamed', 'DSC_001_2.JPG')]
        with patch('tag_organizer.get_tagged_items', return_value=self._FILES), \
             patch('tag_organizer.ensure_folder'), \
             patch('tag_organizer.move_file', side_effect=move_results), \
             patch('tag_organizer.LOG_DIR', str(tmp_path)):
            tag_organizer.main(tag='wedding', folder='Photos/Wedding')

        report = json.loads(list(tmp_path.glob('tag_move_*.json'))[0].read_text())
        assert report['summary']['files_moved']   == 1
        assert len(report['renamed_items'])       == 1
        assert report['renamed_items'][0]['dest'] == 'DSC_001_2.JPG'

    def test_should_count_skipped_files_in_report(self, tmp_path):
        move_results = [('moved', 'IMG_001.JPG'), ('skipped', 'DSC_001.JPG')]
        with patch('tag_organizer.get_tagged_items', return_value=self._FILES), \
             patch('tag_organizer.ensure_folder'), \
             patch('tag_organizer.move_file', side_effect=move_results), \
             patch('tag_organizer.LOG_DIR', str(tmp_path)):
            tag_organizer.main(tag='wedding', folder='Photos/Wedding')

        report = json.loads(list(tmp_path.glob('tag_move_*.json'))[0].read_text())
        assert report['summary']['files_skipped'] == 1
        assert report['summary']['files_moved']   == 1
        assert len(report['skipped_items'])       == 1

    def test_should_count_failed_files_in_report(self, tmp_path):
        move_results = [('moved', 'IMG_001.JPG'), ('failed', 'DSC_001.JPG')]
        with patch('tag_organizer.get_tagged_items', return_value=self._FILES), \
             patch('tag_organizer.ensure_folder'), \
             patch('tag_organizer.move_file', side_effect=move_results), \
             patch('tag_organizer.LOG_DIR', str(tmp_path)):
            tag_organizer.main(tag='wedding', folder='Photos/Wedding')

        report = json.loads(list(tmp_path.glob('tag_move_*.json'))[0].read_text())
        assert report['summary']['files_failed'] == 1
        assert len(report['failed_items'])       == 1

    def test_should_compute_size_totals_correctly_when_mixed_results(self, tmp_path):
        move_results = [('moved', 'IMG_001.JPG'), ('failed', 'DSC_001.JPG')]
        with patch('tag_organizer.get_tagged_items', return_value=self._FILES), \
             patch('tag_organizer.ensure_folder'), \
             patch('tag_organizer.move_file', side_effect=move_results), \
             patch('tag_organizer.LOG_DIR', str(tmp_path)):
            tag_organizer.main(tag='wedding', folder='Photos/Wedding')

        report = json.loads(list(tmp_path.glob('tag_move_*.json'))[0].read_text())
        assert report['summary']['size_total']  == 3_000_000
        assert report['summary']['size_moved']  == 1_000_000
        assert report['summary']['size_failed'] == 2_000_000

    def test_should_include_renamed_size_in_moved_total(self, tmp_path):
        move_results = [('moved', 'IMG_001.JPG'), ('renamed', 'DSC_001_2.JPG')]
        with patch('tag_organizer.get_tagged_items', return_value=self._FILES), \
             patch('tag_organizer.ensure_folder'), \
             patch('tag_organizer.move_file', side_effect=move_results), \
             patch('tag_organizer.LOG_DIR', str(tmp_path)):
            tag_organizer.main(tag='wedding', folder='Photos/Wedding')

        report = json.loads(list(tmp_path.glob('tag_move_*.json'))[0].read_text())
        assert report['summary']['size_moved'] == 3_000_000

    def test_should_prepend_webdav_root_to_target_folder(self, tmp_path):
        with patch('tag_organizer.get_tagged_items', return_value=self._FILES), \
             patch('tag_organizer.ensure_folder'), \
             patch('tag_organizer.move_file', return_value=('moved', 'x.jpg')), \
             patch('tag_organizer.LOG_DIR', str(tmp_path)):
            tag_organizer.main(tag='vacation_2021', folder='Photos/Vacation2021')

        report = json.loads(list(tmp_path.glob('tag_move_*.json'))[0].read_text())
        assert report['target_folder'] == 'Consolidated/Photos/Vacation2021'

    def test_should_strip_leading_and_trailing_slashes_from_folder(self, tmp_path):
        with patch('tag_organizer.get_tagged_items', return_value=self._FILES), \
             patch('tag_organizer.ensure_folder'), \
             patch('tag_organizer.move_file', return_value=('moved', 'x.jpg')), \
             patch('tag_organizer.LOG_DIR', str(tmp_path)):
            tag_organizer.main(tag='wedding', folder='/Photos/Wedding/')

        report = json.loads(list(tmp_path.glob('tag_move_*.json'))[0].read_text())
        assert report['target_folder'] == 'Consolidated/Photos/Wedding'

    def test_should_include_human_readable_sizes_in_report(self, tmp_path):
        with patch('tag_organizer.get_tagged_items', return_value=self._FILES), \
             patch('tag_organizer.ensure_folder'), \
             patch('tag_organizer.move_file', return_value=('moved', 'x.jpg')), \
             patch('tag_organizer.LOG_DIR', str(tmp_path)):
            tag_organizer.main(tag='wedding', folder='Photos/Wedding')

        report = json.loads(list(tmp_path.glob('tag_move_*.json'))[0].read_text())
        assert 'size_total_hr' in report['summary']
        assert 'size_moved_hr' in report['summary']
        assert 'size_failed_hr' in report['summary']
        assert report['summary']['size_total_hr'] == '2.9 MB'

    def test_should_deduplicate_ensure_folder_calls_for_same_parent(self, tmp_path):
        files = [
            {'path': 'Photos/iPhone/202207__/img1.jpg', 'size': 1000},
            {'path': 'Photos/Android/202208__/img2.jpg', 'size': 2000},
            {'path': 'Photos/iPhone/202207__/img3.jpg', 'size': 1000},
        ]
        with patch('tag_organizer.get_tagged_items', return_value=files), \
             patch('tag_organizer.ensure_folder') as mock_folder, \
             patch('tag_organizer.move_file', return_value=('moved', 'x/img.jpg')), \
             patch('tag_organizer.LOG_DIR', str(tmp_path)):
            tag_organizer.main(tag='wedding', folder='Photos/Wedding', keep_parents=1)

        folder_calls = [c[0][0] for c in mock_folder.call_args_list]
        assert 'Consolidated/Photos/Wedding' in folder_calls
        assert 'Consolidated/Photos/Wedding/202207__' in folder_calls
        assert 'Consolidated/Photos/Wedding/202208__' in folder_calls
        assert folder_calls.count('Consolidated/Photos/Wedding/202207__') == 1

    def test_should_pass_keep_parents_to_move_file(self, tmp_path):
        with patch('tag_organizer.get_tagged_items', return_value=self._FILES), \
             patch('tag_organizer.ensure_folder'), \
             patch('tag_organizer.move_file', return_value=('moved', 'x.jpg')) as mock_move, \
             patch('tag_organizer.LOG_DIR', str(tmp_path)):
            tag_organizer.main(tag='wedding', folder='Photos/Wedding', keep_parents=2)

        for c in mock_move.call_args_list:
            assert c[0][2] == 2  # third positional arg is keep_parents


# ── propagate_folder_tags ─────────────────────────────────────────────────────

class TestPropagateFolderTags:
    """Unit tests for propagate_folder_tags().

    The function makes several DB calls in sequence:
      1. fetchone()  — look up tag_id from oc_systemtag
      2. fetchall()  — get list of tagged folders
      3. fetchall()  — for each folder, get untagged files inside it
      4. execute()   — INSERT for each untagged file
    """

    def _db_for_propagate(self, tag_id, folders, files_per_folder):
        """Return (mock_connect, cur, conn) wired for propagate_folder_tags calls."""
        cur = MagicMock()
        conn = MagicMock()
        conn.cursor.return_value = cur
        mock_connect = MagicMock(return_value=conn)

        cur.fetchone.return_value = (tag_id,) if tag_id is not None else None
        # fetchall: first call → folders list, then one call per folder → untagged files
        cur.fetchall.side_effect = [folders] + list(files_per_folder)
        return mock_connect, cur, conn

    def test_should_return_zeros_when_tag_not_found(self):
        cur = MagicMock()
        cur.fetchone.return_value = None
        conn = MagicMock()
        conn.cursor.return_value = cur
        mock_connect = MagicMock(return_value=conn)

        with patch('tag_organizer.psycopg2.connect', mock_connect):
            result = tag_organizer.propagate_folder_tags('nonexistent')

        assert result == {'folders_processed': 0, 'files_tagged': 0}
        conn.commit.assert_not_called()

    def test_should_return_zeros_when_no_tagged_folders(self):
        mock_connect, cur, conn = self._db_for_propagate(
            tag_id=42, folders=[], files_per_folder=[]
        )
        with patch('tag_organizer.psycopg2.connect', mock_connect):
            result = tag_organizer.propagate_folder_tags('wedding')

        assert result == {'folders_processed': 0, 'files_tagged': 0}
        conn.commit.assert_not_called()

    def test_should_tag_untagged_files_in_folder(self):
        folders = [(10, 'Photos/Свадьба')]
        untagged = [(101, 'Photos/Свадьба/IMG_001.JPG'),
                    (102, 'Photos/Свадьба/video.MTS')]
        mock_connect, cur, conn = self._db_for_propagate(42, folders, [untagged])

        with patch('tag_organizer.psycopg2.connect', mock_connect):
            result = tag_organizer.propagate_folder_tags('wedding')

        assert result == {'folders_processed': 1, 'files_tagged': 2}
        conn.commit.assert_called_once()

    def test_should_skip_files_that_already_have_any_tag(self):
        # DB query returns empty list — files already carry some tag (any tag),
        # so NOT EXISTS filters them out at the SQL level.
        folders = [(10, 'Photos/Свадьба')]
        untagged = []  # query returns nothing → files already tagged
        mock_connect, cur, conn = self._db_for_propagate(42, folders, [untagged])

        with patch('tag_organizer.psycopg2.connect', mock_connect):
            result = tag_organizer.propagate_folder_tags('wedding')

        assert result == {'folders_processed': 1, 'files_tagged': 0}
        insert_calls = [c for c in cur.execute.call_args_list
                        if 'INSERT' in str(c)]
        assert len(insert_calls) == 0

    def test_should_not_tag_file_that_has_different_tag(self):
        # file_id=101 already has tag A; DB NOT EXISTS returns it as absent
        # from untagged list (empty), so propagation skips it.
        folders = [(10, 'Photos/Wedding')]
        untagged = []  # file already has tag A → filtered by NOT EXISTS
        mock_connect, cur, conn = self._db_for_propagate(42, folders, [untagged])

        with patch('tag_organizer.psycopg2.connect', mock_connect):
            result = tag_organizer.propagate_folder_tags('wedding')

        assert result['files_tagged'] == 0
        insert_calls = [c for c in cur.execute.call_args_list if 'INSERT' in str(c)]
        assert len(insert_calls) == 0

    def test_should_process_multiple_folders(self):
        folders = [(10, 'Photos/Свадьба'), (20, 'Photos/Отпуск')]
        files1 = [(101, 'Photos/Свадьба/img1.jpg')]
        files2 = [(201, 'Photos/Отпуск/img2.jpg'), (202, 'Photos/Отпуск/img3.jpg')]
        mock_connect, cur, conn = self._db_for_propagate(42, folders, [files1, files2])

        with patch('tag_organizer.psycopg2.connect', mock_connect):
            result = tag_organizer.propagate_folder_tags('vacation')

        assert result == {'folders_processed': 2, 'files_tagged': 3}

    def test_should_not_double_tag_file_covered_by_two_tagged_folders(self):
        # Parent folder AND child subfolder are both tagged.
        # file_id=101 appears in BOTH untagged result sets (simulating a DB
        # NOT EXISTS that hasn't committed yet, or duplicate folder entries).
        folders = [(10, 'Photos/Wedding'), (11, 'Photos/Wedding/Sub')]
        files1 = [(101, 'Photos/Wedding/Sub/img.jpg')]   # found under parent
        files2 = [(101, 'Photos/Wedding/Sub/img.jpg')]   # same file under child
        mock_connect, cur, conn = self._db_for_propagate(42, folders, [files1, files2])

        with patch('tag_organizer.psycopg2.connect', mock_connect):
            result = tag_organizer.propagate_folder_tags('wedding')

        # File should only be tagged once despite appearing twice
        assert result == {'folders_processed': 2, 'files_tagged': 1}
        insert_calls = [c for c in cur.execute.call_args_list if 'INSERT' in str(c)]
        assert len(insert_calls) == 1

    def test_should_insert_with_correct_tag_id_and_file_id(self):
        folders = [(10, 'Photos/Folder')]
        untagged = [(555, 'Photos/Folder/img.jpg')]
        mock_connect, cur, conn = self._db_for_propagate(tag_id=99, folders=folders,
                                                         files_per_folder=[untagged])
        with patch('tag_organizer.psycopg2.connect', mock_connect):
            tag_organizer.propagate_folder_tags('mytag')

        insert_calls = [c for c in cur.execute.call_args_list
                        if 'INSERT' in str(c)]
        assert len(insert_calls) == 1
        params = insert_calls[0][0][1]  # second positional arg = params tuple
        assert params == (99, '555')    # tag_id=99, file_id='555' (cast to text)

    def test_should_close_connection_after_run(self):
        mock_connect, cur, conn = self._db_for_propagate(42, [], [])

        with patch('tag_organizer.psycopg2.connect', mock_connect):
            tag_organizer.propagate_folder_tags('wedding')

        cur.close.assert_called_once()
        conn.close.assert_called_once()

    def test_should_close_connection_when_tag_not_found(self):
        cur = MagicMock()
        cur.fetchone.return_value = None
        conn = MagicMock()
        conn.cursor.return_value = cur
        mock_connect = MagicMock(return_value=conn)

        with patch('tag_organizer.psycopg2.connect', mock_connect):
            tag_organizer.propagate_folder_tags('no_such_tag')

        cur.close.assert_called_once()
        conn.close.assert_called_once()


# ── run_propagate ─────────────────────────────────────────────────────────────

class TestRunPropagate:

    def test_should_call_propagate_folder_tags_and_return_result(self, tmp_path):
        expected = {'folders_processed': 2, 'files_tagged': 5}
        with patch('tag_organizer.propagate_folder_tags', return_value=expected) as mock_prop, \
             patch('tag_organizer.LOG_DIR', str(tmp_path)):
            result = tag_organizer.run_propagate('wedding')

        mock_prop.assert_called_once_with('wedding')
        assert result == expected

    def test_should_create_log_file(self, tmp_path):
        with patch('tag_organizer.propagate_folder_tags',
                   return_value={'folders_processed': 0, 'files_tagged': 0}), \
             patch('tag_organizer.LOG_DIR', str(tmp_path)):
            tag_organizer.run_propagate('wedding')

        logs = list(tmp_path.glob('tag_propagate_wedding_*.log'))
        assert len(logs) == 1
