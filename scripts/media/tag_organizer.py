#!/usr/bin/env python3
"""Move Nextcloud-tagged photos to a target folder via WebDAV.

Usage:
    python3 tag_organizer.py --tag wedding --folder "Photos/Wedding"
    python3 tag_organizer.py --tag wedding --folder "Photos/Wedding" --keep-parents 1
    python3 tag_organizer.py --tag wedding --folder "Photos/Wedding" --keep-parents 2 --dry-run

--keep-parents N preserves the last N folders from the original path:
    N=0  Photos/iPhone/202207__/img.jpg  →  Wedding/img.jpg          (flat, default)
    N=1  Photos/iPhone/202207__/img.jpg  →  Wedding/202207__/img.jpg
    N=2  Photos/iPhone/202207__/img.jpg  →  Wedding/iPhone/202207__/img.jpg

See docs/06-photo-tag-organizer.md for full documentation.
"""

import argparse
import json
import logging
import urllib3
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import psycopg2
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Config ────────────────────────────────────────────────────────────────────
DB_CONFIG = {
    'host':     'localhost',
    'port':     5432,
    'user':     'nextcloud',
    'password': 'CHANGEME',   # get with: docker exec postgres-nextcloud env | grep POSTGRES_PASSWORD
    'dbname':   'nextcloud',
}

NC_URL       = 'https://homelab.nebelung-mercat.ts.net'
NC_USER      = 'admin'
NC_PASS      = 'CHANGEME'
LOG_DIR      = '/data/logs'
WEBDAV_ROOT  = 'Consolidated'   # external storage mount name in Nextcloud

# ── Setup ─────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)
AUTH        = (NC_USER, NC_PASS)
WEBDAV_BASE = f"{NC_URL}/remote.php/dav/files/{NC_USER}"
SSL_VERIFY  = False   # Traefik uses self-signed cert


# ── Helpers ───────────────────────────────────────────────────────────────────

def _webdav_url(path: str) -> str:
    """Build a WebDAV URL with the path percent-encoded (handles non-ASCII filenames)."""
    return f"{WEBDAV_BASE}/{quote(path, safe='/')}"


def format_bytes(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _dest_subpath(db_path: str, keep_parents: int) -> tuple[str, str]:
    """Split db_path into (subfolder, filename) based on keep_parents.

    keep_parents=0: ('', 'img.jpg')
    keep_parents=1: ('202207__', 'img.jpg')
    keep_parents=2: ('iPhone/202207__', 'img.jpg')

    If keep_parents exceeds available depth, all available parents are used.
    """
    parts = Path(db_path).parts
    filename = parts[-1]
    if keep_parents == 0 or len(parts) <= 1:
        return '', filename
    n = min(keep_parents, len(parts) - 1)
    subfolder = '/'.join(parts[-(n + 1):-1])
    return subfolder, filename


def get_tagged_files(tag_name: str) -> list[dict]:
    """Return [{path, size}, …] for all files tagged with tag_name."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()
    cur.execute("""
        SELECT fc.path, fc.size
        FROM oc_filecache fc
        JOIN oc_systemtag_object_mapping m ON m.objectid = fc.fileid::text
        JOIN oc_systemtag t               ON t.id = m.systemtagid
        WHERE t.name = %s
          AND m.objecttype = 'files'
          AND fc.path NOT LIKE 'appdata_%%'
          AND fc.size > 0
        ORDER BY fc.path
    """, (tag_name,))
    files = [{'path': row[0], 'size': row[1] or 0} for row in cur.fetchall()]
    cur.close()
    conn.close()
    log.info(f"Found {len(files)} files tagged '{tag_name}'")
    return files


def ensure_folder(webdav_path: str):
    """Create WebDAV folder hierarchy if it does not exist."""
    parts = webdav_path.strip('/').split('/')
    for i in range(1, len(parts) + 1):
        partial = '/'.join(parts[:i])
        r = requests.request('MKCOL', _webdav_url(partial),
                             auth=AUTH, verify=SSL_VERIFY)
        if r.status_code not in (201, 405):  # 201 created, 405 already exists
            raise RuntimeError(f"MKCOL failed for '{partial}': {r.status_code} {r.text[:120]}")
    log.info(f"Target folder ready: {webdav_path}")


def move_file(db_path: str, target_folder: str, keep_parents: int = 0) -> tuple[str, str]:
    """Move one file via WebDAV MOVE.

    On filename collision tries stem_2, stem_3 … stem_99 before giving up.

    Returns (status, dest_relative_path) where dest_relative_path is
    relative to target_folder:
      keep_parents=0: 'img.jpg'
      keep_parents=1: '202207__/img.jpg'
    status: 'moved' | 'renamed' | 'skipped' | 'failed'
    """
    subfolder, filename = _dest_subpath(db_path, keep_parents)
    dst_folder = f"{target_folder}/{subfolder}" if subfolder else target_folder
    rel_dest   = f"{subfolder}/{filename}" if subfolder else filename

    # Idempotency: file is already at the destination (e.g. rerun after success)
    if f"{WEBDAV_ROOT}/{db_path}" == f"{dst_folder}/{filename}":
        log.info(f"✓ ALREADY IN PLACE: {filename} (skipping)")
        return 'skipped', rel_dest

    stem   = Path(filename).stem
    suffix = Path(filename).suffix
    src    = _webdav_url(f"{WEBDAV_ROOT}/{db_path}")

    for counter in range(1, 100):
        name     = f"{stem}{suffix}" if counter == 1 else f"{stem}_{counter}{suffix}"
        rel_dest = f"{subfolder}/{name}" if subfolder else name
        dst      = _webdav_url(f"{dst_folder}/{name}")
        r        = requests.request('MOVE', src, auth=AUTH, verify=SSL_VERIFY,
                                    headers={'Destination': dst, 'Overwrite': 'F'})

        if r.status_code in (201, 204):
            status = 'moved' if counter == 1 else 'renamed'
            log.info(f"✓ {status.upper()}: {filename} → {rel_dest}")
            return status, rel_dest
        elif r.status_code == 412:   # destination exists, try next suffix
            continue
        else:
            log.error(f"✗ FAILED ({r.status_code}): {db_path}  {r.text[:120]}")
            return 'failed', rel_dest

    log.error(f"✗ FAILED (all 99 suffixes taken): {db_path}")
    return 'failed', f"{subfolder}/{filename}" if subfolder else filename


# ── Main ──────────────────────────────────────────────────────────────────────

def main(tag: str, folder: str, dry_run: bool = False, keep_parents: int = 0):
    target_folder = f"{WEBDAV_ROOT}/{folder.strip('/')}"
    run_ts  = datetime.now()
    run_id  = run_ts.strftime('%Y%m%d_%H%M%S')
    log_dir = Path(LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"tag_move_{tag}_{run_id}.log"
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logging.getLogger().addHandler(fh)
    log.info(f"Log: {log_file}")

    files = get_tagged_files(tag)
    if not files:
        log.info("No tagged files found. Tag some photos first in Nextcloud.")
        return

    total_size = sum(f['size'] for f in files)
    log.info(f"Total to process: {len(files)} files, {format_bytes(total_size)}")

    if dry_run:
        log.info(f"DRY RUN — files that would be moved (keep_parents={keep_parents}):")
        for f in files:
            subfolder, filename = _dest_subpath(f['path'], keep_parents)
            dest = f"{subfolder}/{filename}" if subfolder else filename
            log.info(f"  [{format_bytes(f['size']):>10}]  {f['path']} → {dest}")
        return

    ensure_folder(target_folder)

    # Pre-create unique destination subfolders (avoids redundant MKCOL per file)
    if keep_parents > 0:
        seen_subfolders: set[str] = set()
        for f in files:
            subfolder, _ = _dest_subpath(f['path'], keep_parents)
            if subfolder and subfolder not in seen_subfolders:
                ensure_folder(f"{target_folder}/{subfolder}")
                seen_subfolders.add(subfolder)

    moved, renamed, skipped, failed = [], [], [], []
    for f in files:
        status, dest_name = move_file(f['path'], target_folder, keep_parents)
        entry = {**f, 'dest': dest_name}
        if status == 'moved':
            moved.append(entry)
        elif status == 'renamed':
            renamed.append(entry)
        elif status == 'skipped':
            skipped.append(entry)
        else:
            failed.append(entry)

    moved_size   = sum(e['size'] for e in moved + renamed)
    skipped_size = sum(e['size'] for e in skipped)
    failed_size  = sum(e['size'] for e in failed)

    report = {
        'timestamp':     run_ts.isoformat(),
        'tag':           tag,
        'target_folder': target_folder,
        'keep_parents':  keep_parents,
        'summary': {
            'files_total':     len(files),
            'size_total':      total_size,
            'size_total_hr':   format_bytes(total_size),
            'files_moved':     len(moved),
            'files_renamed':   len(renamed),
            'files_skipped':   len(skipped),
            'files_failed':    len(failed),
            'size_moved':      moved_size,
            'size_moved_hr':   format_bytes(moved_size),
            'size_skipped':    skipped_size,
            'size_skipped_hr': format_bytes(skipped_size),
            'size_failed':     failed_size,
            'size_failed_hr':  format_bytes(failed_size),
        },
        'moved_files':   moved,
        'renamed_files': renamed,
        'skipped_files': skipped,
        'failed_files':  failed,
    }

    log_path = log_dir / f"tag_move_{tag}_{run_id}.json"
    log_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    log.info(
        f"Done: {len(moved)} moved, {len(renamed)} renamed (collision), "
        f"{len(skipped)} skipped (already in place), {len(failed)} failed | "
        f"Moved: {format_bytes(moved_size)} / {format_bytes(total_size)}"
    )
    log.info(f"Report: {log_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Move Nextcloud-tagged photos to a folder via WebDAV.'
    )
    parser.add_argument('--tag',          required=True,
                        help='Nextcloud tag name, e.g. wedding')
    parser.add_argument('--folder',       required=True,
                        help='Target path inside Consolidated/, e.g. Photos/Wedding')
    parser.add_argument('--keep-parents', type=int, default=0,
                        help='Parent folders to preserve from original path (0=flat, 1=one level, 2=two levels)')
    parser.add_argument('--dry-run',      action='store_true',
                        help='List files without moving')
    args = parser.parse_args()
    main(tag=args.tag, folder=args.folder,
         dry_run=args.dry_run, keep_parents=args.keep_parents)
