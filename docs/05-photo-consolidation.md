# Phase 5: Photo Consolidation - Complete Guide

**The safest approach to consolidate family photos: Copy everything first, process only the copies, never touch original drives.**

## 🎯 Overview

This guide walks you through safely consolidating photos and videos from multiple old Windows drives into a clean, deduplicated collection. The **copy-first approach** ensures your original photos are never at risk.

### What This Process Achieves

✅ **All unique photos preserved** - No photos lost, ever  
✅ **Only best quality kept** - RAW > high-res JPEG > compressed  
✅ **Intelligent organization** - Meaningful folder structure maintained  
✅ **Storage optimized** - Significant space savings through deduplication  
✅ **Completely safe** - Original drives never modified  
✅ **Human verified** - Web interface for visual confirmation  
✅ **Photos AND videos** - Handles all media formats  
✅ **Fully reversible** - Can restart any phase safely  

## 🔒 Why Copy-First is Safer

### Problems with Direct Processing
❌ **Risky**: Working directly on original drives  
❌ **Irreversible**: Mistakes could lose photos permanently  
❌ **Stressful**: Fear of data loss during process  
❌ **Blocks cleanup**: Can't format drives until certain everything worked  

### Benefits of Copy-First
✅ **100% Safe**: Original drives never touched  
✅ **Reversible**: Can restart anytime  
✅ **Parallel workflow**: Process copies while keeping originals safe  
✅ **Enables immediate cleanup**: Format drives right after successful copy  

## 📋 Complete Workflow

### **Prerequisites**
- Mini PC with Ubuntu Server 22.04 LTS
- `/data` partition with sufficient space (see space calculation below)
- Old Windows drives connected and mounted read-only (see **Mounting Source Drives** below)
- Basic system setup completed (Phases 1-3)
- Python 3.8+ available on mini PC (Ubuntu 22.04 includes Python 3.10)
- Ansible configured on laptop for remote execution (optional)

### **Mounting Source Drives (NTFS/Windows)**

Old Windows-formatted drives must be mounted **read-only** before running the consolidation. This prevents any accidental writes to the original data.

#### Step 1: Install NTFS support
```bash
sudo apt update && sudo apt install -y ntfs-3g
```

#### Step 2: Connect drives and identify them
Physically connect the drives to the mini PC (USB or SATA), then identify them:
```bash
# List all block devices - look for your drives by size
lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT

# Example output:
# sda      500G
# └─sda1   500G  ntfs   old-ssd-1
# sdb        1T
# └─sdb1     1T  ntfs   old-external-1
# nvme0n1  1.8T
# ├─nvme0n1p1  50G  ext4              /
# ├─nvme0n1p2  20G  ext4              /home
# └─nvme0n1p3 911G  ext4              /data

# Get detailed info with UUIDs (useful to confirm the right drive)
sudo blkid | grep ntfs
# /dev/sda1: LABEL="old-ssd-1" UUID="A1B2C3..." TYPE="ntfs"
# /dev/sdb1: LABEL="old-external-1" UUID="D4E5F6..." TYPE="ntfs"
```

**IMPORTANT**: Device names like `/dev/sda` can change between reboots. Always verify with `lsblk` and `blkid` before mounting.

#### Step 3: Create mount points
```bash
sudo mkdir -p /media/sdb1 /media/sdc1
```
Use mount point names that match your `config.yml` `source_drives` paths (`/media/sdb1`, `/media/sdc1`).

#### Step 4: Mount read-only
```bash
# Mount each drive as read-only (ro) - this is critical for safety
sudo mount -t ntfs-3g -o ro,noexec /dev/sda1 /media/sdb1
sudo mount -t ntfs-3g -o ro,noexec /dev/sdb1 /media/sdc1
```

Mount options explained:
- `ro` - Read-only, prevents any writes to the drive
- `noexec` - Prevents execution of files from the drive

**Note**: Map the actual device (`/dev/sda1`) to the config mount point (`/media/sdb1`). The device name and mount point don't need to match.

#### Step 5: Verify the mount
```bash
# Confirm drives are mounted read-only
mount | grep media
# /dev/sda1 on /media/sdb1 type fuseblk (ro,noexec,...)
# /dev/sdb1 on /media/sdc1 type fuseblk (ro,noexec,...)

# Browse the contents to confirm correct drives
ls /media/sdb1/
ls /media/sdc1/

# Check total size of media files
du -sh /media/sdb1 /media/sdc1
```

#### Step 6: Update config.yml if needed
Verify that `config.yml` `source_drives` paths match your mount points:
```yaml
infrastructure:
  storage:
    source_drives:
      - path: "/media/sdb1"
        label: "old-ssd-1"
        size: "512GB"
        filesystem: "ntfs"
      - path: "/media/sdc1"
        label: "old-external-1"
        size: "1TB"
        filesystem: "ntfs"
```

#### After consolidation: Unmount safely
```bash
# When done with the entire consolidation process
sudo umount /media/sdb1
sudo umount /media/sdc1

# If unmount fails ("target is busy"), check what's using it
sudo lsof +f -- /media/sdb1
# Then close those processes and retry
```

### **Space Requirements Calculation**
```bash
# Check total source drive space (after mounting)
du -sh /media/sdb1 /media/sdc1
# Ensure /data has: source_total_size + 100GB safety buffer

# Check available space on /data
df -h /data

# Example:
# 450GB /media/sdb1
# 800GB /media/sdc1
# Need: ~1350GB free space on /data partition
```

---

## Ansible Step-by-Step Commands

Each phase can be run independently. Run from the `infra/ansible/` directory on your laptop.

```bash
cd infra/ansible

# Phase 0: Check drives are mounted, verify disk space
ansible-playbook -i inventory/homelab photo-consolidation.yml --tags phase0

# Phase 1: Install packages, create directory structure
ansible-playbook -i inventory/homelab photo-consolidation.yml --tags phase1

# Phase 2: Copy all media from source drives to /data/incoming/
# (long-running, up to 4 hours — use screen)
screen -S photo-copy
ansible-playbook -i inventory/homelab photo-consolidation.yml --tags phase2
# Ctrl+A, D to detach — screen -r photo-copy to reattach

# Phase 3: Analyze duplicates in copied files
ansible-playbook -i inventory/homelab photo-consolidation.yml --tags phase3

# Phase 4: Deploy Nextcloud for visual verification
ansible-playbook -i inventory/homelab photo-consolidation.yml --tags phase4

# Phase 5: Human verification pause (skipped when dry_run: true)
# Phase 6: Final consolidation — remove duplicates, build /data/final/
# (skipped when dry_run: true — set dry_run: false in config.yml to enable)
ansible-playbook -i inventory/homelab photo-consolidation.yml --tags phase5,phase6

# Phase 7: Cleanup temp files, generate completion report
ansible-playbook -i inventory/homelab photo-consolidation.yml --tags phase7
```

Each phase validates its own prerequisites and will fail with a clear message if a prior phase hasn't been run yet.

---

## 🚀 Phase 1: Safe Copy Operation

**Goal**: Copy ALL media files from old drives to `/data/incoming/` without touching originals.

### **Execution Options**

**Option 1: Ansible Automation (Recommended)**
```bash
# Run phases step by step (see command reference above)
ansible-playbook -i inventory/homelab photo-consolidation.yml --tags phase0
ansible-playbook -i inventory/homelab photo-consolidation.yml --tags phase1
ansible-playbook -i inventory/homelab photo-consolidation.yml --tags phase2
```

**Option 2: Python CLI (Recommended for Manual Control)** //TODO: need to copy python script files to mini pc
```bash
# On mini PC, install Python dependencies first
cd scripts/media
pip3 install -r requirements.txt

# Run complete workflow
screen -S photo-consolidation
python3 consolidate.py workflow

# Or run individual phases
python3 consolidate.py scan         # Scan source drives
python3 consolidate.py copy         # Copy files
python3 consolidate.py analyze      # Analyze duplicates
python3 consolidate.py consolidate  # Final consolidation

# Check status anytime
python3 consolidate.py status
```

**Option 3: Legacy Bash Scripts**
```bash
# On mini PC, run individual phases (legacy)
screen -S photo-copy
./scripts/media/copy_all_media.sh

# Detach from screen: Ctrl+A, then D
# Reattach later: screen -r photo-copy
```

**Choose Based On:**
- **Ansible**: Full automation, best for production
- **Python CLI**: Better control, progress bars, robust error handling
- **Bash Scripts**: Legacy option, simpler but less reliable

**Why use screen/tmux?**
- Photo copying can take several hours
- Protects against SSH disconnections  
- Allows you to disconnect and check progress later
- Essential for network stability during large operations

### **What Happens**
1. **Scans all configured drives** for photos/videos
2. **Preserves folder structure** completely 
3. **Creates SHA256 manifests** for integrity verification
4. **Shows progress** with visual indicators
5. **Verifies each copy** with hash comparison
6. **Never modifies originals** - purely read operations

### **Result Structure**
```
/data/incoming/
├── sdb1/                    # Files from first old drive
│   ├── Photos/
│   ├── Videos/  
│   └── [original folder structure]
└── sdc1/                    # Files from second old drive
    ├── 2023/
    ├── 2024/
    └── [original folder structure]
```

### **Safety Check**
```bash
# After completion:
ls -la /data/incoming/
# Should see your drive folders with all photos copied

# Verify manifests created:
ls -la /data/manifests/
# Should see: sdb1_original_manifest.sha256, sdc1_original_manifest.sha256
```

**🔓 MILESTONE: Original drives now safe to disconnect!**

---

## 🔍 Phase 2: Duplicate Analysis

**Goal**: Find duplicates and rank by quality, working ONLY on copied files.

### **Execution**  
```bash
# Continue in screen session or start new one
screen -r photo-copy  # or screen -S photo-analysis
./scripts/media/analyze_copied_files.sh
```

### **What Happens**
1. **Creates new manifest** from copied files in `/data/incoming/`
2. **Finds identical files** using SHA256 hash comparison
3. **Applies quality scoring** from centralized configuration
4. **Ranks duplicates** (RAW > high-res JPEG > compressed)
5. **Considers folder context** (organized > backup > random)
6. **Generates detailed reports** with recommendations

### **Quality Scoring Example**
```
=== Duplicate Group 00042 ===
Files ranked by quality (KEEP first, REMOVE others):

[1] KEEP - Score: 90/100 🎯 BEST QUALITY
    Path: sdb1/2023/Wedding/Canon_RAW/IMG_5847.CR2
    Format: Canon RAW file  
    Size: 24.5MB
    Factors: +20 RAW bonus, +10 organized folder
    
[2] REMOVE - Score: 72/100
    Path: sdc1/Photos/Wedding_JPEG/IMG_5847.jpg
    Format: High-quality JPEG
    Size: 8.2MB  
    Factors: +15 high-res JPEG, +10 organized folder
    
[3] REMOVE - Score: 45/100  
    Path: sdb1/Backup/Old_Photos/IMG_5847_small.jpg
    Format: Compressed JPEG
    Size: 3.1MB
    Factors: +5 standard JPEG, -10 backup folder

Space savings: 11.3MB
```

### **Result Files**
```
/data/duplicates/
├── reports/
│   └── copied_files_analysis.txt    # Summary of all findings
└── groups/
    ├── group_00001.txt             # Individual duplicate group
    ├── group_00002.txt
    └── [one file per group...]
```

---

## 👁️ Phase 3: Human Verification

**Goal**: Visual confirmation through web interface before any destructive operations.

### **Execution**
```bash
# Nextcloud is already installed from Phase 4
# Access the web interface to review photos and analysis
```

### **What's Available**
1. **Nextcloud already deployed** via Docker on port 8080 (from Phase 4)
2. **Verification folders mounted** for web browsing
3. **Analysis results available** for review
4. **Admin credentials** from Phase 4 setup

### **Web Access**
- **URL**: `http://your-server:8080`
- **Login**: Admin credentials from Phase 4 setup
- **Navigation**: Files → verification

### **Verification Interface Structure**
```
📁 verification/
├── 📄 VERIFICATION_GUIDE.md          # Step-by-step instructions
├── 📁 incoming/                      # Browse your copied photos
│   ├── 📁 sdb1/                     # First drive photos
│   └── 📁 sdc1/                     # Second drive photos  
└── 📁 duplicates/                    # Analysis results
    ├── 📁 reports/                   # Summary reports
    └── 📁 groups/                    # Individual duplicate groups
```

### **Verification Checklist**
- [ ] **Browse photos** - Confirm important photos are present
- [ ] **Check folder structure** - Verify organization makes sense
- [ ] **Review duplicate analysis** - Read summary report
- [ ] **Spot-check groups** - Verify quality rankings look correct
- [ ] **Confirm space savings** - Check if savings are reasonable

### **Common Verification Questions**
- ✅ Are RAW files ranked higher than JPEG versions?
- ✅ Are organized folders preferred over backup locations?
- ✅ Do large files rank higher than small versions?
- ✅ Are important family photos preserved?
- ✅ Does the duplicate percentage seem reasonable?

### **Refreshing Nextcloud File Index**

If you add files manually on the server or they don't appear in the web interface, scan them with Nextcloud's indexer:

```bash
# Navigate to Nextcloud docker-compose directory
cd ~/docker-compose/nextcloud

# Scan all files for all users
docker compose exec -u www-data nextcloud-app php occ files:scan --all

# Scan files for specific user (faster)
docker compose exec -u www-data nextcloud-app php occ files:scan admin

# Scan with verbose output to see progress
docker compose exec -u www-data nextcloud-app php occ files:scan --all -v
```

**Common scenarios requiring file scan**:
- After photo consolidation completes and creates new files
- When manually copying files to Nextcloud data directory
- If files appear on disk but not in web interface
- After mounting external storage directories

---

## ✨ Phase 4: Final Consolidation

**Goal**: Remove duplicates from copied files and create final clean collection.

### **Execution**
```bash
# Continue in screen session 
screen -r photo-copy  # or screen -S photo-consolidate
./scripts/media/consolidate_copied_files.sh
```

### **What Happens**
1. **Processes each duplicate group** according to analysis
2. **Keeps the highest quality file** from each group
3. **Removes lower quality duplicates** from `/data/incoming/`
4. **Copies best versions** to `/data/final/`
5. **Creates backups** of removed files (if configured)
6. **Processes unique files** (no duplicates found)
7. **Generates comprehensive report** with statistics

### **Safety Features**
- **Original drives untouched** - Ultimate backup always available
- **Optional backup** - Additional backup of removed files (disabled by default)
- **Detailed logging** - Complete record of all operations
- **Space verification** - Confirms expected space savings
- **Integrity checks** - Verifies all operations completed successfully

### **Result Structure**
```
/data/final/                         # Clean consolidated collection
├── 2023/
│   ├── Wedding/
│   └── Vacation/
├── 2024/
│   └── Family_Photos/
└── [organized structure]

/data/backup/consolidation/          # Optional backups (disabled by default)
├── group_00001/                     # Only if backup_before_removal: true
└── group_00002/                     # Original drives are the real backup
```

---

## 🧹 Phase 5: Original Drive Cleanup

**Goal**: Format original drives for reuse in Phase 6 Storage Setup.

### **Manual Drive Formatting**
```bash
# List drives to confirm which ones to format
lsblk

# Format each old drive (AFTER verifying final collection)
sudo fdisk /dev/sdb    # Format first old drive
sudo fdisk /dev/sdc    # Format second old drive

# Alternative: Quick format
sudo mkfs.ext4 /dev/sdb1
sudo mkfs.ext4 /dev/sdc1
```

### **Safety Reminders**
- ✅ **Verify final collection** first - Check `/data/final/` thoroughly
- ✅ **Test photo access** - Open some random photos to confirm they work
- ✅ **Keep Nextcloud running** - For continued access to photos
- ✅ **Only format after** complete satisfaction with results

---

## ⚙️ Configuration Customization

### **Quality Scoring Adjustment**
```yaml
# In config.yml or config.local.yml
photo_consolidation:
  quality:
    format_scores:
      raw_files: 95        # Increase RAW file priority
      high_res_jpg: 80     # Increase large JPEG priority
      
    folder_bonuses:
      organized: 15        # Bigger bonus for organized folders
      backup: -15          # Bigger penalty for backup folders
```

### **Process Control**
```yaml
photo_consolidation:
  process:
    parallel_jobs: 6       # Match your CPU cores
    preserve_structure: true # Keep original folder organization
    
  safety:
    min_free_space_gb: 200 # More conservative space buffer
    backup_before_removal: false # Optional backup (default: off, originals are safe)
    # backup_before_removal: true # Enable for extra paranoia
```

---

## 🚨 Troubleshooting

### **Common Issues**

**"Not enough space for copy"**
- Free up space on `/data` partition
- Copy drives one at a time if needed
- Adjust `min_free_space_gb` in configuration

**"No files copied"**
- Check source drive mount points: `df -h`
- Verify permissions: `ls -la /media/`
- Check configuration: `./scripts/common/config.sh`

**"Nextcloud won't start"**
- Ensure Docker is running: `systemctl status docker`
- Check port 8080 is available: `netstat -ln | grep 8080`
- Review Docker logs: `docker-compose logs nextcloud`

**"High duplicate percentage warning"**
- Expected when same photos exist on multiple drives
- Review if backup folders contain duplicates
- Adjust `max_duplicate_percentage` threshold if needed

### **Recovery Procedures**

**Start completely over:**
```bash
# Remove all copied files and restart
sudo rm -rf /data/incoming /data/duplicates /data/manifests
./scripts/media/copy_all_media.sh
```

**Re-analyze without re-copying:**
```bash
# If copies are good but analysis needs redoing
./scripts/media/analyze_copied_files.sh
```

**Reset verification interface:**
```bash
# Restart Nextcloud
docker-compose -f /data/../apps/nextcloud/docker-compose.yml down
./scripts/setup/setup_nextcloud_verification.sh
```

---

## 🎯 Expected Results

### **Typical Outcomes**
- **Space savings**: 30-60% reduction through deduplication
- **Processing time**: 2-8 hours depending on photo count
- **Quality improvement**: Only best versions of each photo kept
- **Organization**: Clean, structured photo collection

### **Success Indicators**
- ✅ Final collection in `/data/final/` contains all unique photos
- ✅ RAW files preferred over JPEG versions
- ✅ Organized folders maintained
- ✅ Significant storage space saved
- ✅ Original drives safely formatted for reuse
- ✅ Ready for photo management software deployment

---

## 🔗 Integration with Homelab Journey

### **Connection to Phase 6 - Storage Setup**
After photo consolidation completion:
1. **✅ Photos safely consolidated** in `/data/final/`
2. **✅ Old drives formatted** and ready for additional storage roles  
3. **✅ Space optimized** through intelligent deduplication
4. **➡️ Ready for Phase 6**: Use clean drives for expanded storage
5. **➡️ Photo management**: Deploy Immich or PhotoPrism on consolidated collection

### **Next Steps**
- Set up automated backups of `/data/final/`
- Deploy photo management software (Immich recommended)
- Configure additional storage using formatted drives
- Set up development environment for personal projects

---

**The safe copy-first approach ensures your family photos are never at risk while achieving professional-grade consolidation results. Your original drives remain untouched throughout the entire process, giving you complete confidence in the outcome.**