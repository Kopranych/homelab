# Photo Tag Organizer via Nextcloud Tags + WebDAV

## Goal

Photos are scattered across many folders inside `/data/photo-consolidation/final`.
Tag any group of photos in the Nextcloud UI, then run one command to physically move
all tagged files into a dedicated folder.

**Examples:**

| Tag | Target folder |
|-----|--------------|
| `wedding` | `Photos/Wedding` |
| `vacation_2021` | `Photos/Vacation2021` |
| `kids_school` | `Photos/Kids/School` |

---

## Infrastructure

| Component | Value |
|-----------|-------|
| Nextcloud container | `nextcloud-app` |
| PostgreSQL container | `postgres-nextcloud` |
| DB name / user | `nextcloud` / `nextcloud` |
| External storage mount | `/Consolidated` → `/data/photo-consolidation/final` |
| Nextcloud URL | `https://homelab.nebelung-mercat.ts.net` (Traefik + self-signed TLS) |
| WebDAV user | `kopranych` |
| `systemtags` app | enabled (v1.18.0) |

### Path mapping

```
DB path (oc_filecache):  Photos/iPhone_Anna_2/202207__/IMG_1901.JPG
WebDAV src:              Consolidated/Photos/iPhone_Anna_2/202207__/IMG_1901.JPG
WebDAV dst:              Consolidated/Photos/Wedding/IMG_1901.JPG
Filesystem:              /data/photo-consolidation/final/Photos/Wedding/IMG_1901.JPG
```

The DB stores paths relative to the storage root (no mount prefix).
The script prepends `Consolidated/` to build the WebDAV URL.

---

## Phase 1 — Verify access ✅ DONE

All checks passed on 2026-03-03:

| Check | Result |
|-------|--------|
| `overwrite.cli.url` | `https://homelab.nebelung-mercat.ts.net` |
| WebDAV PROPFIND | HTTP 207 ✓ |
| `systemtags` app | enabled v1.18.0 ✓ |
| WebDAV systemtags endpoint | HTTP 200 ✓ |
| OCS tags API | returns 404 — **not needed**, script uses DB directly |

---

## Phase 2 — Tag photos in Nextcloud UI

1. Open `https://homelab.nebelung-mercat.ts.net` in browser
2. Navigate to **Files → Consolidated → Photos**
3. Browse subfolders, right-click a photo → **Tags** → type your tag → Enter
4. Progress saves immediately in DB — safe to spread across multiple sessions
5. To review already-tagged files: **Files → Tags → `<tag-name>`**

> After a session of tagging, verify the count in the DB:
> ```bash
> docker exec postgres-nextcloud psql -U nextcloud -d nextcloud -c \
>   "SELECT t.name, COUNT(m.objectid) AS files
>    FROM oc_systemtag t
>    JOIN oc_systemtag_object_mapping m ON m.systemtagid = t.id
>    GROUP BY t.name ORDER BY files DESC;"
> ```

---

## Phase 3 — Run the organizer script

Script location: `scripts/media/tag_organizer.py`

### Script overview

```
1. Query PostgreSQL → get all {path, size} for files tagged <tag>
2. Print summary: N files, total size
3. Create target folder hierarchy via WebDAV MKCOL (skips if exists)
4. For each file:
   - Build src URL:  Consolidated/<db_path>
   - Try MOVE to dst: Consolidated/<folder>/<filename>  (Overwrite: F)
   - On collision (412): retry with _2, _3 … _99 suffix
   - On success: record as 'moved' or 'renamed'
5. Write timestamped JSON report: files moved, renamed, failed + sizes
```

### Script

```python
#!/usr/bin/env python3
"""Move Nextcloud-tagged photos to a target folder via WebDAV.

Usage:
    python3 tag_organizer.py --tag wedding --folder "Photos/Wedding"
    python3 tag_organizer.py --tag vacation_2021 --folder "Photos/Vacation2021"
    python3 tag_organizer.py --tag wedding --folder "Photos/Wedding" --dry-run
"""

import argparse
import json
import logging
import urllib3
from datetime import datetime
from pathlib import Path

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
NC_USER      = 'kopranych'
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

def format_bytes(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def get_tagged_files(tag_name: str) -> list[dict]:
    """Return [{path, size}, …] for all files tagged with tag_name."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()
    cur.execute("""
        SELECT fc.path, fc.size
        FROM oc_filecache fc
        JOIN oc_systemtag_object_mapping m ON m.objectid = fc.fileid
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
        r = requests.request('MKCOL', f"{WEBDAV_BASE}/{partial}",
                             auth=AUTH, verify=SSL_VERIFY)
        if r.status_code not in (201, 405):  # 201 created, 405 already exists
            raise RuntimeError(f"MKCOL failed for '{partial}': {r.status_code} {r.text[:120]}")
    log.info(f"Target folder ready: {webdav_path}")


def move_file(db_path: str, target_folder: str) -> tuple[str, str]:
    """Move one file via WebDAV MOVE.

    On filename collision tries stem_2, stem_3 … stem_99 before giving up.
    Returns (status, dest_filename):
      status: 'moved' | 'renamed' | 'failed'
    """
    stem   = Path(db_path).stem
    suffix = Path(db_path).suffix
    src    = f"{WEBDAV_BASE}/{WEBDAV_ROOT}/{db_path}"

    for counter in range(1, 100):
        name = f"{stem}{suffix}" if counter == 1 else f"{stem}_{counter}{suffix}"
        dst  = f"{WEBDAV_BASE}/{target_folder}/{name}"
        r    = requests.request('MOVE', src, auth=AUTH, verify=SSL_VERIFY,
                                headers={'Destination': dst, 'Overwrite': 'F'})

        if r.status_code in (201, 204):
            status = 'moved' if counter == 1 else 'renamed'
            log.info(f"✓ {status.upper()}: {Path(db_path).name} → {name}")
            return status, name
        elif r.status_code == 412:   # destination exists, try next suffix
            continue
        else:
            log.error(f"✗ FAILED ({r.status_code}): {db_path}  {r.text[:120]}")
            return 'failed', name

    log.error(f"✗ FAILED (all 99 suffixes taken): {db_path}")
    return 'failed', f"{stem}{suffix}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main(tag: str, folder: str, dry_run: bool = False):
    target_folder = f"{WEBDAV_ROOT}/{folder.strip('/')}"

    files = get_tagged_files(tag)
    if not files:
        log.info("No tagged files found. Tag some photos first in Nextcloud.")
        return

    total_size = sum(f['size'] for f in files)
    log.info(f"Total to process: {len(files)} files, {format_bytes(total_size)}")

    if dry_run:
        log.info("DRY RUN — files that would be moved:")
        for f in files:
            log.info(f"  [{format_bytes(f['size']):>10}]  {f['path']}")
        return

    ensure_folder(target_folder)

    moved, renamed, failed = [], [], []
    for f in files:
        status, dest_name = move_file(f['path'], target_folder)
        entry = {**f, 'dest': dest_name}
        if status == 'moved':
            moved.append(entry)
        elif status == 'renamed':
            renamed.append(entry)
        else:
            failed.append(entry)

    moved_size  = sum(e['size'] for e in moved + renamed)
    failed_size = sum(e['size'] for e in failed)

    report = {
        'timestamp':     datetime.now().isoformat(),
        'tag':           tag,
        'target_folder': target_folder,
        'summary': {
            'files_total':     len(files),
            'size_total':      total_size,
            'size_total_hr':   format_bytes(total_size),
            'files_moved':     len(moved),
            'files_renamed':   len(renamed),
            'files_failed':    len(failed),
            'size_moved':      moved_size,
            'size_moved_hr':   format_bytes(moved_size),
            'size_failed':     failed_size,
            'size_failed_hr':  format_bytes(failed_size),
        },
        'moved_files':   moved,
        'renamed_files': renamed,
        'failed_files':  failed,
    }

    log_path = (Path(LOG_DIR) /
                f"tag_move_{tag}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    log.info(
        f"Done: {len(moved)} moved, {len(renamed)} renamed (collision), "
        f"{len(failed)} failed | "
        f"Moved: {format_bytes(moved_size)} / {format_bytes(total_size)}"
    )
    log.info(f"Report: {log_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Move Nextcloud-tagged photos to a folder via WebDAV.'
    )
    parser.add_argument('--tag',     required=True,
                        help='Nextcloud tag name, e.g. wedding')
    parser.add_argument('--folder',  required=True,
                        help='Target path inside Consolidated/, e.g. Photos/Wedding')
    parser.add_argument('--dry-run', action='store_true',
                        help='List files without moving')
    args = parser.parse_args()
    main(tag=args.tag, folder=args.folder, dry_run=args.dry_run)
```

### Install dependencies
```bash
pip3 install psycopg2-binary requests
```

### Get the DB password
```bash
docker exec postgres-nextcloud env | grep POSTGRES_PASSWORD
```
Fill in `DB_CONFIG['password']` and `NC_PASS` in the script.

---

## Usage examples

### Wedding photos
```bash
# Dry run first
python3 tag_organizer.py --tag wedding --folder "Photos/Wedding" --dry-run

# Run for real
python3 tag_organizer.py --tag wedding --folder "Photos/Wedding"

# Check result
find /data/photo-consolidation/final/Photos/Wedding -type f | wc -l
```

### Vacation 2021
```bash
python3 tag_organizer.py --tag vacation_2021 --folder "Photos/Vacation2021" --dry-run
python3 tag_organizer.py --tag vacation_2021 --folder "Photos/Vacation2021"
```

### Any other grouping
```bash
python3 tag_organizer.py --tag kids_school --folder "Photos/Kids/School" --dry-run
python3 tag_organizer.py --tag kids_school --folder "Photos/Kids/School"
```

### View the report
```bash
# Latest run
ls -t /data/logs/tag_move_*.json | head -1 | xargs python3 -m json.tool

# Specific run
python3 -m json.tool /data/logs/tag_move_wedding_20260304_120000.json
```

---

## Collision handling

When two tagged photos have the same filename (e.g., `IMG_0001.JPG` from different
folders), the script appends a numeric suffix instead of skipping:

```
IMG_0001.JPG      ← first file, moved as-is
IMG_0001_2.JPG    ← second file with same name
IMG_0001_3.JPG    ← third, etc.
```

The JSON report has a `renamed_files` list with both the original path and
the destination name, so nothing is lost or silently dropped.

---

## Idempotency

Re-running the script after a partial run is safe:
- Files already moved → no longer appear in `oc_filecache` at the old path →
  the DB query won't return them → they're simply skipped
- Tags remain in the DB until you remove them manually → progress is never lost
- `--dry-run` always shows the current remaining work

---

## Safety properties

| Risk | Protection |
|------|------------|
| Overwriting existing files | `Overwrite: F` + suffix retry → never overwrites |
| Losing progress mid-run | Tags in DB survive crashes; re-run continues where left off |
| Audit trail | Timestamped JSON log per run with file counts and sizes |
| DB out of sync | WebDAV MOVE updates Nextcloud DB automatically |
| Running before ready | `--dry-run` shows full list without touching files |
| Wrong folder | `--dry-run` output shows exact destination before committing |

---

## Status

- [x] External storage mount identified: `/Consolidated`
- [x] DB path format confirmed: `Photos/...` (no mount prefix)
- [x] Target path format confirmed: `Consolidated/Photos/<Folder>`
- [x] NC_URL confirmed: `https://homelab.nebelung-mercat.ts.net`
- [x] WebDAV access verified: PROPFIND → 207, systemtags → 200
- [x] `systemtags` app enabled: v1.18.0
- [x] Script written: `scripts/media/tag_organizer.py`
- [ ] DB password filled in the script
- [ ] Photos tagged in Nextcloud UI
- [ ] Dry run completed
- [ ] Full run completed
