# Step 6: Photo Consolidation & Management

## 🎯 Goal
Safely consolidate, organize, and deduplicate photos from multiple NTFS drives while preserving all important memories.

## 🚨 Your Challenge
You have a complex photo situation that requires careful handling:
- Photos scattered across unknown directories on 2 NTFS drives
- Duplicates between drives AND within each drive
- Need to verify everything is copied safely
- Manual review required before any deletion
- Only then safe to reformat old drives for Linux use
- TODO: Think about which partition install docker in primary disk during consolidaiting photos

## 🛡️ Safety-First Approach
**Golden Rule**: Never delete original photos until you've verified copies and completed manual review through a photo management system.

---

## 📋 Step 6A: Safe Photo Discovery & Copy

### 1. Connect Old Drives Safely
```bash
# Connect old NTFS drives via USB (read-only first)
# This prevents accidental writes to original drives

# Check connected drives
lsblk
sudo fdisk -l

# Expected to see your old drives as /dev/sdb, /dev/sdc, etc.
```

### 2. Mount NTFS Drives Read-Only
```bash
# Install NTFS support
sudo apt update
sudo apt install ntfs-3g

# Create mount points
sudo mkdir -p /mnt/old-drive-1
sudo mkdir -p /mnt/old-drive-2

# Mount drives READ-ONLY (safety first)
sudo mount -t ntfs-3g -o ro,uid=1000,gid=1000 /dev/sdb1 /mnt/old-drive-1
sudo mount -t ntfs-3g -o ro,uid=1000,gid=1000 /dev/sdc1 /mnt/old-drive-2

# Verify mounts
df -h | grep mnt
```

### 3. Discover Photo Locations
```bash
# Find all image files on both drives
# This may take a while - let it run

echo "=== Searching Drive 1 ===" > /home/$USER/photo-inventory.txt
find /mnt/old-drive-1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.tiff" -o -iname "*.raw" -o -iname "*.cr2" -o -iname "*.nef" \) -exec ls -lh {} \; >> /home/$USER/photo-inventory.txt 2>&1

echo "=== Searching Drive 2 ===" >> /home/$USER/photo-inventory.txt
find /mnt/old-drive-2 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.tiff" -o -iname "*.raw" -o -iname "*.cr2" -o -iname "*.nef" \) -exec ls -lh {} \; >> /home/$USER/photo-inventory.txt 2>&1

# Check the inventory
wc -l /home/$USER/photo-inventory.txt
echo "Photo discovery complete. Check photo-inventory.txt for details."
```

### 4. Create Checksums Before Copying
```bash
# Create checksums of ALL image files (this takes time but ensures safety)
echo "Creating checksums for Drive 1..."
find /mnt/old-drive-1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.tiff" -o -iname "*.raw" -o -iname "*.cr2" -o -iname "*.nef" \) -exec sha256sum {} \; > /home/$USER/drive1-checksums.txt

echo "Creating checksums for Drive 2..."
find /mnt/old-drive-2 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.tiff" -o -iname "*.raw" -o -iname "*.cr2" -o -iname "*.nef" \) -exec sha256sum {} \; > /home/$USER/drive2-checksums.txt

echo "Checksums created. These will verify successful copying."
```

### 5. Copy Photos Safely
```bash
# Create destination structure
mkdir -p /home/$USER/photos-consolidation/drive-1-copy
mkdir -p /home/$USER/photos-consolidation/drive-2-copy

# Copy Drive 1 with rsync (preserves structure, shows progress)
echo "Copying photos from Drive 1..."
rsync -avh --progress /mnt/old-drive-1/ /home/$USER/photos-consolidation/drive-1-copy/

# Copy Drive 2 with rsync
echo "Copying photos from Drive 2..."
rsync -avh --progress /mnt/old-drive-2/ /home/$USER/photos-consolidation/drive-2-copy/

echo "Photo copying complete."
```

### 6. Verify Checksums After Copying
```bash
# Verify Drive 1 copy
echo "Verifying Drive 1 copy..."
cd /home/$USER/photos-consolidation/drive-1-copy
find . -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.tiff" -o -iname "*.raw" -o -iname "*.cr2" -o -iname "*.nef" \) -exec sha256sum {} \; > /home/$USER/drive1-copy-checksums.txt

# Verify Drive 2 copy
echo "Verifying Drive 2 copy..."
cd /home/$USER/photos-consolidation/drive-2-copy
find . -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.tiff" -o -iname "*.raw" -o -iname "*.cr2" -o -iname "*.nef" \) -exec sha256sum {} \; > /home/$USER/drive2-copy-checksums.txt

# Compare checksums (manual verification recommended)
cd /home/$USER
echo "Compare original and copy checksums manually to verify successful copying."
echo "Original checksums: drive1-checksums.txt, drive2-checksums.txt"
echo "Copy checksums: drive1-copy-checksums.txt, drive2-copy-checksums.txt"
```

### 7. Create Initial Backup
```bash
# Create backup of copied photos before any organization
echo "Creating backup of copied photos..."
mkdir -p /home/$USER/photos-backup
rsync -avh /home/$USER/photos-consolidation/ /home/$USER/photos-backup/
echo "Backup complete. Original photos are now safe to work with."
```

---

## 📋 Step 6B: Photo Management System Setup

### Option 1: NextCloud (Web-based file management with photo gallery)
```bash
# Install NextCloud via Snap (easiest method)
sudo snap install nextcloud

# Configure NextCloud
sudo nextcloud.manual-install your-username your-password

# Set up data directory to point to your photos
sudo nextcloud.occ config:system:set datadirectory --value="/home/$USER/photos-consolidation"

# Access NextCloud at: http://your-server-ip (usually http://192.168.1.100)
echo "NextCloud available at: http://$(hostname -I | awk '{print $1}')"
```

### Option 2: PhotoPrism (AI-powered photo management)
```bash
# Install Docker if not already installed
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Create PhotoPrism directory structure
mkdir -p /home/$USER/photoprism/{config,storage,photos}

# Link your photos to PhotoPrism
ln -s /home/$USER/photos-consolidation /home/$USER/photoprism/photos/consolidation

# Run PhotoPrism container
docker run -d \
  --name photoprism \
  --security-opt seccomp=unconfined \
  --security-opt apparmor=unconfined \
  -p 2342:2342 \
  -e PHOTOPRISM_UPLOAD_NSFW="true" \
  -e PHOTOPRISM_ADMIN_PASSWORD="your-admin-password" \
  -v /home/$USER/photoprism/photos:/photoprism/originals \
  -v /home/$USER/photoprism/storage:/photoprism/storage \
  photoprism/photoprism:latest

# Access PhotoPrism at: http://your-server-ip:2342
echo "PhotoPrism available at: http://$(hostname -I | awk '{print $1}'):2342"
```

---

## 📋 Step 6C: Manual Review & Organization

### 1. Browse Photos Through Management System
```bash
# Access your chosen photo management system via web browser from your Windows PC
# NextCloud: http://192.168.1.100
# PhotoPrism: http://192.168.1.100:2342

# Browse through all photos by directory structure
# Look for obvious duplicates and organize by themes/dates
```

### 2. Create Organization Structure
```bash
# While browsing, plan your organization structure
mkdir -p /home/$USER/photos-organized/{
2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025,
events/{birthdays,holidays,vacations,family},
people/{family,friends},
places/{home,travel},
unsorted,
duplicates-review
}

# This gives you a framework to organize while reviewing
```

### 3. Manual Review Process
```
1. Use web interface to browse photos by location
2. Identify obvious duplicates (same photo in multiple locations)
3. Note photos that need organizing vs. duplicates to remove
4. Create lists of:
   - Photos to keep and organize
   - Obvious duplicates to remove
   - Photos needing closer inspection
```

---

## 📋 Step 6D: Safe Deduplication

### 1. Install Deduplication Tools
```bash
# Install duplicate finding tools
sudo apt install fdupes rmlint

# Install additional helpful tools
sudo apt install exiftool imagemagick
```

### 2. Find Duplicates with Multiple Tools
```bash
# Method 1: fdupes (simple, reliable)
echo "Finding duplicates with fdupes..."
fdupes -r /home/$USER/photos-consolidation > /home/$USER/duplicates-fdupes.txt

# Method 2: rmlint (advanced duplicate detection)
echo "Finding duplicates with rmlint..."
rmlint /home/$USER/photos-consolidation --type=duplicates --config=sh:handler=clone > /home/$USER/duplicates-rmlint.txt

# Method 3: Find by EXIF data (for photos that may be resized copies)
echo "Finding potential EXIF duplicates..."
find /home/$USER/photos-consolidation -name "*.jpg" -exec exiftool -T -filename -filesize -imagesize -datetimeoriginal {} \; | sort > /home/$USER/exif-analysis.txt
```

### 3. Cross-Reference with Manual Review
```bash
# Compare automated findings with your manual review
echo "Review these files:"
echo "1. duplicates-fdupes.txt - Simple duplicate detection"
echo "2. duplicates-rmlint.txt - Advanced duplicate analysis" 
echo "3. exif-analysis.txt - EXIF-based comparison"
echo "4. Your manual notes from web interface review"

# Create safe duplicate removal plan
mkdir -p /home/$USER/duplicates-to-remove
echo "Move confirmed duplicates here before deletion"
```

### 4. Safe Duplicate Removal Process
```bash
# NEVER delete directly - always move to review folder first
# Example process for confirmed duplicates:

# 1. Move (don't delete) confirmed duplicates
# mv /path/to/duplicate/photo /home/$USER/duplicates-to-remove/

# 2. Review moved files one more time
# 3. Only delete after final confirmation

echo "Only delete after you've verified through the web interface that originals are safe!"
```

---

## 📋 Step 6E: Final Organization & Verification

### 1. Create Final Organized Structure
```bash
# Based on your manual review, organize photos into final structure
# Use rsync to copy (not move) initially for safety

echo "Organizing photos based on manual review..."
# Example organization commands (customize based on your review):

# Organize by year (example)
# rsync -av /home/$USER/photos-consolidation/drive-1-copy/Photos2020/ /home/$USER/photos-organized/2020/

# Organize by events (example)
# rsync -av /home/$USER/photos-consolidation/drive-2-copy/Vacation/ /home/$USER/photos-organized/events/vacations/

echo "Customize organization based on your specific photo structure discovered during review"
```

### 2. Final Verification Through Management System
```bash
# Point your photo management system to the organized photos
# NextCloud: Configure to scan /home/$USER/photos-organized
# PhotoPrism: Link organized photos directory

echo "Browse organized photos through web interface to confirm all important photos are preserved"
```

### 3. Create Final Backup
```bash
# Create final backup of organized photos
echo "Creating final backup of organized photos..."
mkdir -p /home/$USER/photos-final-backup
rsync -avh /home/$USER/photos-organized/ /home/$USER/photos-final-backup/

echo "Final backup complete."
```

### 4. Safe Old Drive Cleanup
```bash
# ONLY after complete verification through photo management system
echo "=== DANGER ZONE ==="
echo "Only proceed if you've verified ALL photos are safely organized and backed up"
echo "Steps to clean old drives:"
echo "1. Unmount old drives: sudo umount /mnt/old-drive-1 /mnt/old-drive-2"
echo "2. Disconnect USB drives"
echo "3. Reformat for Linux use in Step 7"
echo ""
echo "DO NOT proceed until you've browsed your organized photos and confirmed everything important is preserved!"
```

---

## 🛠️ Tools Summary

### File Operations
- **rsync**: Safe copying with progress and verification
- **sha256sum**: Create file checksums for integrity verification

### Photo Management Systems
- **NextCloud**: Web-based file management with photo galleries
- **PhotoPrism**: AI-powered photo organization and face recognition

### Duplicate Detection
- **fdupes**: Simple, reliable duplicate file detection
- **rmlint**: Advanced duplicate detection with multiple algorithms
- **exiftool**: EXIF data analysis for photo metadata comparison

### File Analysis
- **find**: Locate files by type and characteristics
- **ls**: File listing with details
- **wc**: Count files and lines in reports

---

## 📊 Expected Timeline

### Phase Breakdown
- **Discovery & Copying**: 2-4 hours (depending on photo count)
- **Checksum Creation**: 1-2 hours
- **Management System Setup**: 30-60 minutes
- **Manual Review**: 4-8 hours (depends on photo count and organization needs)
- **Duplicate Detection**: 1-2 hours
- **Final Organization**: 2-4 hours
- **Verification**: 1-2 hours

### Total Time
**Estimated: 12-24 hours spread over several days**

This is time well invested to ensure no precious memories are lost!

---

## 🔍 Troubleshooting

### NTFS Mount Issues
```bash
# If drive won't mount
sudo ntfs-3g /dev/sdb1 /mnt/old-drive-1 -o force

# If permission issues
sudo chown -R $USER:$USER /mnt/old-drive-1
```

### Checksum Verification Failures
```bash
# If checksums don't match, don't panic
# Copy the file again and re-verify
# Some files may have been corrupted on original drive
```

### Photo Management System Issues
```bash
# NextCloud permissions
sudo chown -R www-data:www-data /var/snap/nextcloud/current/nextcloud/data

# PhotoPrism container restart
docker restart photoprism
```

### Large File Handling
```bash
# For very large photo collections, process in batches
# Split by directory or file type
find /mnt/old-drive-1 -name "*.jpg" | head -1000 > batch1.txt
```

---

## ✅ Step 6 Complete!

After completing this step, you will have:

- ✅ **All photos safely copied** from NTFS drives with checksum verification
- ✅ **Photo management system** running for visual review and organization
- ✅ **Duplicates identified and safely removed** using multiple detection methods
- ✅ **Photos organized** into logical directory structure
- ✅ **Multiple backups** of organized photos
- ✅ **Old drives ready** for reformatting in Step 7
- ✅ **Web-based photo access** for ongoing management

## 🔄 Next Step

**Ready for Step 7: System Optimization & Final Partitioning** where you'll:
- Reformat old drives for Linux use
- Implement the final optimized partition layout
- Set up multi-drive configuration for production use
- Migrate from Phase 1 to Phase 2 system architecture

---

**💡 Pro Tips**:
- Take your time with manual review - rushing leads to lost photos
- Always verify through the web interface before deleting anything
- Keep multiple backups until you're 100% confident
- Document your organization system for future reference