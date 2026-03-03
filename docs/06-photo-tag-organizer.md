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

> Verify count in the DB after a tagging session:
> ```bash
> docker exec postgres-nextcloud psql -U nextcloud -d nextcloud -c \
>   "SELECT t.name, COUNT(m.objectid) AS files
>    FROM oc_systemtag t
>    JOIN oc_systemtag_object_mapping m ON m.systemtagid = t.id
>    GROUP BY t.name ORDER BY files DESC;"
> ```

---

## Phase 3 — Run the organizer

### Script overview

`scripts/media/tag_organizer.py` — see source for full implementation.

```
1. Query PostgreSQL → get all {path, size} for files tagged <tag>
2. Print summary: N files, total size
3. Create target folder + unique subfolders via WebDAV MKCOL (skips if exists)
4. For each file:
   - Build src URL:  Consolidated/<db_path>
   - Compute destination path based on --keep-parents
   - Try MOVE to dst (Overwrite: F)
   - On collision (412): retry with _2, _3 … _99 suffix
   - On success: record as 'moved' or 'renamed'
5. Write timestamped JSON report to /data/logs/: counts + sizes
```

### Keep-parents mode

By default all files land flat in the target folder. Use `--keep-parents N` to
preserve the last N path components from the original location:

| `--keep-parents` | Source path | Destination inside `Photos/Wedding/` |
|------------------|-------------|--------------------------------------|
| `0` (default) | `Photos/iPhone/202207__/img.jpg` | `img.jpg` |
| `1` | `Photos/iPhone/202207__/img.jpg` | `202207__/img.jpg` |
| `2` | `Photos/iPhone/202207__/img.jpg` | `iPhone/202207__/img.jpg` |

Use this when you have multiple photos named identically (e.g., `IMG_0001.JPG` from
different devices) and want to keep them visually grouped by folder.

---

## Running via Ansible (recommended)

Ansible handles credential injection, SSH reliability, and report display automatically.

### One-time credential setup

Add to `config.local.yml` (gitignored — never committed):

```yaml
nextcloud:
  password: "your-nextcloud-user-password"
  db:
    password: "your-postgres-password"   # docker exec postgres-nextcloud env | grep POSTGRES_PASSWORD
```

`config.yml` already has all non-secret defaults (`url`, `user`, `webdav_root`, etc.).

### Deploy scripts first (if not already done)

```bash
cd infra/ansible
ansible-playbook -i inventory/homelab photo-consolidation.yml --tags phase1
```

This deploys `tag_organizer.py` (and all other scripts) to `/opt/photo-consolidator/` and installs the Python venv with all dependencies.

### Dry run

```bash
ansible-playbook -i inventory/homelab tag-organizer.yml \
  -e "tag=wedding folder='Photos/Wedding' dry_run=true"

# With parent folders preserved (see what the subfolder structure would look like)
ansible-playbook -i inventory/homelab tag-organizer.yml \
  -e "tag=wedding folder='Photos/Wedding' keep_parents=1 dry_run=true"
```

Output shows every file with its original path → destination. No files are touched.

### Full run

```bash
# Flat — all files directly in Photos/Wedding/
ansible-playbook -i inventory/homelab tag-organizer.yml \
  -e "tag=wedding folder='Photos/Wedding'"

# Keep date folder (one parent) — Photos/Wedding/202207__/img.jpg
ansible-playbook -i inventory/homelab tag-organizer.yml \
  -e "tag=wedding folder='Photos/Wedding' keep_parents=1"

# Keep device + date (two parents) — Photos/Wedding/iPhone_Anna/202207__/img.jpg
ansible-playbook -i inventory/homelab tag-organizer.yml \
  -e "tag=wedding folder='Photos/Wedding' keep_parents=2"
```

### Other tags

```bash
ansible-playbook -i inventory/homelab tag-organizer.yml \
  -e "tag=vacation_2021 folder='Photos/Vacation2021' keep_parents=1"

ansible-playbook -i inventory/homelab tag-organizer.yml \
  -e "tag=kids_school folder='Photos/Kids/School'"
```

### What the playbook does

1. Validates `tag`, `folder`, and credentials are all set — fails fast if anything is missing
2. Injects credentials into the deployed script on the server via `lineinfile`
3. Runs the script with `async/poll` (SSH-drop safe, 1 h timeout)
4. Prints the JSON report summary on completion

---

## Running directly on the server (alternative)

Use this when already SSH'd into the server and want a quick run without Ansible.

### First run: fill in credentials

```bash
# Get DB password
docker exec postgres-nextcloud env | grep POSTGRES_PASSWORD

# Edit the script
nano /opt/photo-consolidator/tag_organizer.py
# Set NC_PASS and DB_CONFIG['password']
```

### Dry run

```bash
/opt/photo-consolidator/venv/bin/python \
  /opt/photo-consolidator/tag_organizer.py \
  --tag wedding --folder "Photos/Wedding" --dry-run
```

### Full run

```bash
/opt/photo-consolidator/venv/bin/python \
  /opt/photo-consolidator/tag_organizer.py \
  --tag wedding --folder "Photos/Wedding"
```

### View report

```bash
# Latest run for a tag
ls -t /data/logs/tag_move_wedding_*.json | head -1 | xargs python3 -m json.tool

# Check result on filesystem
find /data/photo-consolidation/final/Photos/Wedding -type f | wc -l
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
the destination name — nothing is lost or silently dropped.

---

## Idempotency

Re-running after a partial run is safe:
- Files already moved → no longer in `oc_filecache` at the old path → DB query skips them
- Tags stay in the DB until manually removed → progress is never lost
- `--dry-run` always shows the current remaining work

---

## Safety properties

| Risk | Protection |
|------|------------|
| Overwriting existing files | `Overwrite: F` + suffix retry — never overwrites |
| Losing progress mid-run | Tags in DB survive crashes; re-run continues from where it stopped |
| Audit trail | Timestamped JSON log per run with file counts and sizes |
| DB out of sync | WebDAV MOVE updates Nextcloud DB automatically |
| Running before ready | `--dry-run` shows full list without touching files |
| Wrong folder | Ansible validates both `tag` and `folder` before touching anything |
| Credentials in git | Passwords live only in `config.local.yml` (gitignored) |

---

## Files

| File | Purpose |
|------|---------|
| `scripts/media/tag_organizer.py` | Main script |
| `scripts/media/tests/test_tag_organizer.py` | Unit tests (39 tests) |
| `infra/ansible/tag-organizer.yml` | Ansible playbook |
| `config.yml` → `nextcloud:` | Non-secret defaults (URL, user, etc.) |
| `config.local.yml` → `nextcloud:` | Passwords — **never commit** |

---

## Status

- [x] External storage mount identified: `/Consolidated`
- [x] DB path format confirmed: `Photos/...` (no mount prefix)
- [x] Target path format confirmed: `Consolidated/Photos/<Folder>`
- [x] NC_URL confirmed: `https://homelab.nebelung-mercat.ts.net`
- [x] WebDAV access verified: PROPFIND → 207, systemtags → 200
- [x] `systemtags` app enabled: v1.18.0
- [x] Script written: `scripts/media/tag_organizer.py`
- [x] Unit tests written: `tests/test_tag_organizer.py` (39 passing)
- [x] Ansible playbook written: `infra/ansible/tag-organizer.yml`
- [x] Credentials pattern: `config.local.yml` (gitignored)
- [ ] `config.local.yml` populated with actual passwords
- [ ] Scripts deployed via `photo-consolidation.yml --tags phase1`
- [ ] Photos tagged in Nextcloud UI
- [ ] Dry run completed
- [ ] Full run completed
