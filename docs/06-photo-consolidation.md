# Safe Photo Consolidation - Complete Guide

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
- Old Windows drives mounted (e.g., `/media/sdb1`, `/media/sdc1`)
- Basic system setup completed (Phases 1-5)

### **Space Requirements Calculation**
```bash
# Check total source drive space
du -sh /media/sdb1 /media/sdc1
# Ensure /data has: source_total_size + 100GB safety buffer

# Example output:
# 450GB /media/sdb1
# 800GB /media/sdc1  
# Need: ~1350GB free space on /data partition
```

---

## 🚀 Phase 1: Safe Copy Operation

**Goal**: Copy ALL media files from old drives to `/data/incoming/` without touching originals.

### **Execution**
```bash
# Recommended: Use screen for long-running operations
screen -S photo-copy
./scripts/media/copy_all_media.sh

# Detach from screen: Ctrl+A, then D
# Reattach later: screen -r photo-copy
```

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
./scripts/setup/setup_nextcloud_verification.sh
```

### **What Happens**
1. **Deploys Nextcloud** via Docker on port 8080
2. **Mounts verification folders** for web browsing
3. **Creates verification guide** with detailed instructions
4. **Generates access credentials** automatically

### **Web Access**
- **URL**: `http://your-server:8080`
- **Login**: Auto-generated admin credentials (displayed after setup)
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

**Goal**: Format original drives for reuse in Phase 7 Storage Setup.

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

### **Connection to Phase 7 - Storage Setup**
After photo consolidation completion:
1. **✅ Photos safely consolidated** in `/data/final/`
2. **✅ Old drives formatted** and ready for additional storage roles  
3. **✅ Space optimized** through intelligent deduplication
4. **➡️ Ready for Phase 7**: Use clean drives for expanded storage
5. **➡️ Photo management**: Deploy Immich or PhotoPrism on consolidated collection

### **Next Steps**
- Set up automated backups of `/data/final/`
- Deploy photo management software (Immich recommended)
- Configure additional storage using formatted drives
- Set up development environment for personal projects

---

**The safe copy-first approach ensures your family photos are never at risk while achieving professional-grade consolidation results. Your original drives remain untouched throughout the entire process, giving you complete confidence in the outcome.**