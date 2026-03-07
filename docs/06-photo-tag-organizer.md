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

### Tagging individual files

1. Open `https://homelab.nebelung-mercat.ts.net` in browser
2. Navigate to **Files → Consolidated → Photos**
3. Browse subfolders, right-click a photo → **Tags** → type your tag → Enter
4. Progress saves immediately in DB — safe to spread across multiple sessions
5. To review already-tagged files: **Files → Tags → `<tag-name>`**

### Tagging an entire folder (faster)

When you want to tag a large set of photos organised in a folder, tag the folder itself
instead of each file individually:

1. Navigate to **Files → Consolidated → Photos**
2. Right-click the folder → **Tags** → type your tag → Enter
3. **Important**: Nextcloud tags only the folder, not the files inside it.
   Individual files will **not** appear in **Files → Tags → `<tag-name>`** yet.

**Solution**: run the propagate step (Phase 3) to write the tag to every file inside
the tagged folder.  After propagation the tag view shows every individual file and you
can verify them before moving.

> Verify tag counts in the DB:
> ```bash
> docker exec postgres-nextcloud psql -U nextcloud -d nextcloud -c \
>   "SELECT t.name, COUNT(m.objectid) AS items
>    FROM oc_systemtag t
>    JOIN oc_systemtag_object_mapping m ON m.systemtagid = t.id
>    GROUP BY t.name ORDER BY items DESC;"
> ```

---

## Phase 3 — Propagate tags to files inside tagged folders (optional)

Skip this phase if you tagged individual files directly (Phase 2, first approach).

Run this phase when you tagged **folders** and want individual files to appear in the
Nextcloud tag view for verification.

### What propagation does

Finds every folder with the tag in the DB and inserts a tag row for each untagged file
inside it.  Only the Nextcloud DB is modified — no files are moved.  The operation is
**idempotent**: re-running is safe and skips already-tagged files.

### Propagate via Ansible (recommended)

```bash
ansible-playbook -i inventory/homelab tag-organizer.yml \
  -e "tag=wedding propagate_only=true"
```

Output shows how many folders were processed and how many files were tagged.  Check the
Nextcloud tag view (**Files → Tags → wedding**) to confirm individual files appear.

### Propagate directly on the server

```bash
/opt/photo-consolidator/venv/bin/python \
  /opt/photo-consolidator/tag_organizer.py \
  --tag wedding --propagate
```

### After propagation

Open **Files → Tags → `<tag-name>`** in Nextcloud.  Every file inside the tagged
folders should now appear individually.  Browse, zoom in, verify the selection is
correct.  Then proceed to Phase 4 to move them.

---

## Phase 4 — Run the organizer

### Script overview

`scripts/media/tag_organizer.py` — see source for full implementation.

```
Move mode (--folder):
1. Query PostgreSQL → get all {path, size, is_dir} for items tagged <tag>
   (both individual files AND tagged folders are returned)
2. Print summary: N files, N folders, total size
3. Create target folder via WebDAV MKCOL (skips if exists)
4. Process folders first (parents before children), then files:
   - If a parent folder was already moved, skip covered children automatically
   - Build src URL:  Consolidated/<db_path>
   - Compute destination path based on --keep-parents
   - Try MOVE to dst (Overwrite: F)
   - On collision (412): retry with _2, _3 … _99 suffix
   - On success: record as 'moved' or 'renamed'
5. Write timestamped JSON report to /data/logs/: counts + sizes

Propagate mode (--propagate):
1. Look up tag_id in oc_systemtag
2. Find all folders carrying the tag
3. For each folder: INSERT tag row for every untagged file inside
4. Commit — no files are moved, no WebDAV calls made
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

### Recommended workflow when tagging folders

```bash
# Step 1 — Tag a folder in the Nextcloud UI, then propagate the tag to all files inside:
ansible-playbook -i inventory/homelab tag-organizer.yml \
  -e "tag=wedding propagate_only=true"

# Step 2 — Open Nextcloud → Files → Tags → wedding
#           Verify every file looks correct.

# Step 3 — Dry run to preview the move:
ansible-playbook -i inventory/homelab tag-organizer.yml \
  -e "tag=wedding folder='Photos/Wedding' dry_run=true"

# Step 4 — Move files:
ansible-playbook -i inventory/homelab tag-organizer.yml \
  -e "tag=wedding folder='Photos/Wedding'"
```

### Dry run (move preview)

```bash
ansible-playbook -i inventory/homelab tag-organizer.yml \
  -e "tag=wedding folder='Photos/Wedding' dry_run=true"

# With parent folders preserved (see what the subfolder structure would look like)
ansible-playbook -i inventory/homelab tag-organizer.yml \
  -e "tag=wedding folder='Photos/Wedding' keep_parents=1 dry_run=true"
```

Output shows every file with its original path → destination. No files are touched.

### Full move run

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

1. Validates `tag`, `folder` (or `propagate_only`), and credentials — fails fast if anything is missing
2. Injects credentials into the deployed script on the server via `lineinfile`
3. Runs the script with `async/poll` (SSH-drop safe, 1 h timeout)
4. For propagate-only: logs folder/file counts; for move: prints the JSON report summary

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

### Propagate tags to files inside a tagged folder

```bash
/opt/photo-consolidator/venv/bin/python \
  /opt/photo-consolidator/tag_organizer.py \
  --tag wedding --propagate
```

### Dry run (move preview)

```bash
/opt/photo-consolidator/venv/bin/python \
  /opt/photo-consolidator/tag_organizer.py \
  --tag wedding --folder "Photos/Wedding" --dry-run
```

### Full move run

```bash
/opt/photo-consolidator/venv/bin/python \
  /opt/photo-consolidator/tag_organizer.py \
  --tag wedding --folder "Photos/Wedding"
```

### Propagate then move (combined)

```bash
# Propagate first, then move in one script invocation
/opt/photo-consolidator/venv/bin/python \
  /opt/photo-consolidator/tag_organizer.py \
  --tag wedding --propagate --folder "Photos/Wedding"
```

### View reports

```bash
# Latest move report for a tag
ls -t /data/logs/tag_move_wedding_*.json | head -1 | xargs python3 -m json.tool

# Latest propagate log
ls -t /data/logs/tag_propagate_wedding_*.log | head -1 | xargs tail -20

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

The JSON report has a `renamed_items` list with both the original path and
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
| Audit trail | Timestamped log per run (`.log` + `.json` for moves, `.log` for propagate) |
| DB out of sync | WebDAV MOVE updates Nextcloud DB automatically |
| Moving wrong files | `--propagate` + tag view verification before `--folder` move |
| Running before ready | `--dry-run` shows full list without touching files |
| Wrong folder | Ansible validates `tag` and `folder` before touching anything |
| Credentials in git | Passwords live only in `config.local.yml` (gitignored) |

---

## Files

| File | Purpose |
|------|---------|
| `scripts/media/tag_organizer.py` | Main script (move + propagate) |
| `scripts/media/tests/test_tag_organizer.py` | Unit tests |
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
- [x] Folder tagging support: move entire subtrees, skip covered children
- [x] Propagate mode: `--propagate` tags files inside tagged folders
- [x] Unit tests written: `tests/test_tag_organizer.py`
- [x] Ansible playbook written: `infra/ansible/tag-organizer.yml`
- [x] Credentials pattern: `config.local.yml` (gitignored)
- [ ] `config.local.yml` populated with actual passwords
- [ ] Scripts deployed via `photo-consolidation.yml --tags phase1`
- [ ] Photos/folders tagged in Nextcloud UI
- [ ] Propagate run (if folders were tagged): `propagate_only=true`
- [ ] Tag view verified in Nextcloud UI
- [ ] Dry run completed
- [ ] Full run completed
