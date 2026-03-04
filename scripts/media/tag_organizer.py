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


def get_tagged_items(tag_name: str) -> list[dict]:
    """Return [{path, size}, …] for all files tagged with tag_name.

    Folders are excluded — use propagate_folder_tags() first so every file
    inside a tagged folder carries the tag individually.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()
    cur.execute("""
        SELECT fc.path,
               GREATEST(fc.size, 0)
        FROM oc_filecache fc
        JOIN oc_systemtag_object_mapping m ON m.objectid = fc.fileid::text
        JOIN oc_systemtag t               ON t.id = m.systemtagid
        JOIN oc_mimetypes mt              ON mt.id = fc.mimetype
        WHERE t.name = %s
          AND m.objecttype = 'files'
          AND mt.mimetype != 'httpd/unix-directory'
          AND fc.path NOT LIKE 'appdata_%%'
        ORDER BY fc.path
    """, (tag_name,))
    items = [{'path': row[0], 'size': row[1] or 0}
             for row in cur.fetchall()]
    cur.close()
    conn.close()
    log.info(f"Found {len(items)} files tagged '{tag_name}'")
    return items


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

    On name collision tries stem_2, stem_3 … stem_99 before giving up.

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


# ── Propagate ─────────────────────────────────────────────────────────────────

def propagate_folder_tags(tag_name: str) -> dict:
    """Write tag_name to every untagged file inside folders that carry tag_name.

    Nextcloud's tag view shows only directly-tagged items.  Tagging a folder
    does NOT automatically surface its contents.  This function tags each file
    recursively so they appear in the tag view for individual verification
    before moving.

    Only regular files are tagged (sub-folders are left unchanged).
    Files that already carry ANY tag are silently skipped — this prevents
    double-tagging files that were individually tagged for a different purpose.

    Returns {'folders_processed': N, 'files_tagged': N}
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()

    # ── Look up tag id ─────────────────────────────────────────────────────────
    cur.execute("SELECT id FROM oc_systemtag WHERE name = %s", (tag_name,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        log.info(f"Tag '{tag_name}' not found in DB — nothing to propagate.")
        return {'folders_processed': 0, 'files_tagged': 0}
    tag_id = row[0]

    # ── Find all tagged folders ────────────────────────────────────────────────
    cur.execute("""
        SELECT DISTINCT fc.fileid, fc.path
        FROM oc_filecache fc
        JOIN oc_systemtag_object_mapping m ON m.objectid = fc.fileid::text
        JOIN oc_systemtag t               ON t.id = m.systemtagid
        JOIN oc_mimetypes mt              ON mt.id = fc.mimetype
        WHERE t.name = %s
          AND m.objecttype = 'files'
          AND mt.mimetype = 'httpd/unix-directory'
          AND fc.path NOT LIKE 'appdata_%%'
        ORDER BY fc.path
    """, (tag_name,))
    folders = cur.fetchall()

    if not folders:
        cur.close()
        conn.close()
        log.info(f"No folders tagged '{tag_name}' — nothing to propagate.")
        return {'folders_processed': 0, 'files_tagged': 0}

    log.info(f"Found {len(folders)} tagged folder(s) — propagating tag to files inside…")
    folders_processed = 0
    files_tagged      = 0
    tagged_in_this_run: set[int] = set()   # guard against nested/overlapping folders

    for folder_id, folder_path in folders:
        folders_processed += 1
        # Files inside this folder not yet tagged
        cur.execute("""
            SELECT fc.fileid, fc.path
            FROM oc_filecache fc
            JOIN oc_mimetypes mt ON mt.id = fc.mimetype
            WHERE fc.path LIKE %s
              AND mt.mimetype != 'httpd/unix-directory'
              AND fc.path NOT LIKE 'appdata_%%'
              AND NOT EXISTS (
                  SELECT 1 FROM oc_systemtag_object_mapping m2
                  WHERE m2.objectid = fc.fileid::text
                    AND m2.objecttype = 'files'
              )
        """, (folder_path + '/%',))
        untagged = [(fid, fpath) for fid, fpath in cur.fetchall()
                    if fid not in tagged_in_this_run]

        log.info(f"  {folder_path}: {len(untagged)} untagged file(s)")
        for file_id, file_path in untagged:
            cur.execute("""
                INSERT INTO oc_systemtag_object_mapping (systemtagid, objectid, objecttype)
                VALUES (%s, %s, 'files')
                ON CONFLICT DO NOTHING
            """, (tag_id, str(file_id)))
            tagged_in_this_run.add(file_id)
            files_tagged += 1

        if untagged:
            log.info(f"  ✓ Tagged {len(untagged)} file(s) in {folder_path}")

    conn.commit()
    cur.close()
    conn.close()

    log.info(
        f"Propagation complete: {folders_processed} folder(s) processed, "
        f"{files_tagged} new file(s) tagged."
    )
    return {'folders_processed': folders_processed, 'files_tagged': files_tagged}


def run_propagate(tag: str) -> dict:
    """Set up a timestamped log file and run propagate_folder_tags."""
    run_ts   = datetime.now()
    run_id   = run_ts.strftime('%Y%m%d_%H%M%S')
    log_dir  = Path(LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"tag_propagate_{tag}_{run_id}.log"
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logging.getLogger().addHandler(fh)
    log.info(f"Log: {log_file}")
    return propagate_folder_tags(tag)


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

    items = get_tagged_items(tag)
    if not items:
        log.info("No tagged files found. Tag some photos first in Nextcloud (run --propagate if needed).")
        return

    total_size = sum(i['size'] for i in items)
    log.info(f"Total to process: {len(items)} files, {format_bytes(total_size)}")

    if dry_run:
        log.info(f"DRY RUN — files that would be moved (keep_parents={keep_parents}):")
        for item in items:
            subfolder, name = _dest_subpath(item['path'], keep_parents)
            dest = f"{subfolder}/{name}" if subfolder else name
            log.info(f"  [FILE] [{format_bytes(item['size']):>10}]  {item['path']} → {dest}")
        return

    ensure_folder(target_folder)

    seen_folders: set[str] = {target_folder}  # avoid redundant MKCOL
    moved, renamed, skipped, failed = [], [], [], []

    for item in sorted(items, key=lambda x: x['path']):
        # Ensure the destination parent folder exists (cached to avoid redundant MKCOL)
        subfolder, _ = _dest_subpath(item['path'], keep_parents)
        dst_parent   = f"{target_folder}/{subfolder}" if subfolder else target_folder
        if dst_parent not in seen_folders:
            ensure_folder(dst_parent)
            seen_folders.add(dst_parent)

        status, dest_name = move_file(item['path'], target_folder, keep_parents)
        entry = {**item, 'dest': dest_name}
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
            'files_total':     len(items),
            'size_total':      total_size,
            'size_total_hr':   format_bytes(total_size),
            'files_moved':     len(moved),
            'files_skipped':   len(skipped),
            'files_failed':    len(failed),
            'size_moved':      moved_size,
            'size_moved_hr':   format_bytes(moved_size),
            'size_skipped':    skipped_size,
            'size_skipped_hr': format_bytes(skipped_size),
            'size_failed':     failed_size,
            'size_failed_hr':  format_bytes(failed_size),
        },
        'moved_items':   moved,
        'renamed_items': renamed,
        'skipped_items': skipped,
        'failed_items':  failed,
    }

    log_path = log_dir / f"tag_move_{tag}_{run_id}.json"
    log_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    log.info(
        f"Done: {len(moved)} moved, {len(renamed)} renamed (collision), "
        f"{len(skipped)} skipped, {len(failed)} failed | "
        f"Moved: {format_bytes(moved_size)} / {format_bytes(total_size)}"
    )
    log.info(f"Report: {log_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Move Nextcloud-tagged photos to a folder via WebDAV.'
    )
    parser.add_argument('--tag',          required=True,
                        help='Nextcloud tag name, e.g. wedding')
    parser.add_argument('--folder',       default='',
                        help='Target path inside Consolidated/, e.g. Photos/Wedding '
                             '(required unless --propagate is used alone)')
    parser.add_argument('--keep-parents', type=int, default=0,
                        help='Parent folders to preserve from original path (0=flat, 1=one level, 2=two levels)')
    parser.add_argument('--dry-run',      action='store_true',
                        help='List files without moving')
    parser.add_argument('--propagate',    action='store_true',
                        help='Tag all files inside tagged folders so they appear '
                             'individually in the Nextcloud tag view for verification')
    args = parser.parse_args()

    if not args.propagate and not args.folder:
        parser.error('--folder is required unless --propagate is used')

    if args.propagate:
        run_propagate(tag=args.tag)
    if args.folder:
        main(tag=args.tag, folder=args.folder,
             dry_run=args.dry_run, keep_parents=args.keep_parents)
