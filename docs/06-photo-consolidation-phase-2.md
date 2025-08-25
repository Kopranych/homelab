# Phase 2: Duplicate Analysis & Visual Verification

**Prerequisites:** Phase 1 completed (discovery manifests created)
**Goal:** Identify duplicates and visually verify removal decisions
**Safety:** Read-only analysis, no files deleted in this phase

---

## Required Scripts (create these as separate .sh files)

### Scripts to Create:
1. `analyze_duplicates.sh` - Finds duplicate groups with quality analysis
2. `visual_verify.sh` - Interactive verification with quality recommendations
3. `generate_thumbnails.sh` - Creates preview images for verification
4. `quality_analyzer.sh` - Analyzes photo quality metrics

---

## Step 7: Analyze Discovery Results

```bash
# First, let's see what we discovered
echo "=== Discovery Summary ==="
wc -l /home/$USER/manifests/*_manifest.sha256
echo ""

echo "=== Sample of files found ==="
head -10 /home/$USER/manifests/source1_manifest.sha256
echo ""

echo "=== File type statistics ==="
cat /home/$USER/manifests/source1_stats.txt
cat /home/$USER/manifests/source2_stats.txt
```

---

## Step 8: Install Image Analysis Tools

```bash
# Install tools for image preview and quality analysis
sudo apt update
sudo apt install -y \
  feh \           # Lightweight image viewer for previews
  imagemagick \   # Already installed, but needed for thumbnails and quality analysis
  sxiv \          # Simple X Image Viewer (alternative)
  ranger \        # File manager with image preview
  w3m-img \       # Terminal image display capability
  jpeginfo \      # JPEG quality and integrity checker
  pngcheck        # PNG integrity checker

# Verify installation
which feh sxiv ranger jpeginfo pngcheck
```

---

## Step 9: Deploy Analysis Scripts

```bash
# Copy scripts from your local development machine
scp scripts/media/analyze_duplicates.sh $USER@$HOMELAB_HOST:/home/$USER/scripts/
scp scripts/media/visual_verify.sh $USER@$HOMELAB_HOST:/home/$USER/scripts/
scp scripts/media/generate_thumbnails.sh $USER@$HOMELAB_HOST:/home/$USER/scripts/
scp scripts/media/quality_analyzer.sh $USER@$HOMELAB_HOST:/home/$USER/scripts/

# Make them executable
chmod +x /home/$USER/scripts/{analyze_duplicates.sh,visual_verify.sh,generate_thumbnails.sh,quality_analyzer.sh}

# Verify deployment
ls -la /home/$USER/scripts/
```

---

## Complete Phase 2 Workflow

### Step 1: Quality Analysis
```bash
screen -S quality_analysis
/home/$USER/scripts/quality_analyzer.sh
# Wait for completion, then detach with Ctrl+A, D
```

### Step 2: Duplicate Analysis with Quality Intelligence
```bash  
screen -S duplicate_analysis
/home/$USER/scripts/analyze_duplicates.sh
# Creates ranked duplicate groups with quality scores
```

### Step 3: Generate Visual Thumbnails
```bash
screen -S thumbnails
/home/$USER/scripts/generate_thumbnails.sh
# Creates preview images for all duplicate groups
```

### Step 4: Visual Verification Session
```bash
screen -S visual_verification
/home/$USER/scripts/visual_verify.sh
# Interactive verification with photo previews
```

### Step 5: Review Results
```bash
# Check duplicate analysis summary
cat /data/duplicates/reports/duplicate_summary.txt

# Check verification results
cat /data/duplicates/verification_summary.txt

# View removal decisions
head -20 /data/duplicates/removal_decisions.txt
```

---

## Quality Analysis Features

### Photo Quality Metrics:
- **Resolution**: Higher resolution preferred (4032x3024 vs 3024x2268)
- **File Size**: Larger size usually indicates less compression
- **JPEG Quality**: Compression level analysis (98% vs 85% vs 75%)
- **Compression Artifacts**: Detection of quality loss from re-encoding
- **Color Depth**: Bit depth analysis (24-bit vs 16-bit)
- **Metadata Preservation**: Complete EXIF data vs stripped metadata

### RAW vs JPEG Priority:
- **RAW files** (CR2, NEF, ARW) always ranked highest (uncompressed)
- **High-quality JPEG** from camera ranked second
- **Re-compressed JPEG** ranked lower
- **Heavily compressed** or resized versions ranked lowest

### Folder Context Scoring:
- **Meaningful folders** ("2022/Summer", "Moscow Trip") get bonus points
- **Backup folders** ("Backup", "Copy", "Old") get lower priority
- **Random folders** ("Random", "Temp", "Downloads") get lowest priority

### Smart Recommendations:
```bash
Quality Score Calculation:
- Base score: File size + resolution
- JPEG quality bonus: +10 for >95%, +5 for >85%  
- RAW file bonus: +20 points
- Folder context: +10 meaningful, -5 backup, -10 random
- EXIF completeness: +5 for complete metadata
- Final score: 0-100 (higher is better)
```

### Enhanced Decision Making with Quality Analysis:
```bash
# Example verification session with quality recommendations:
=== Duplicate Group 00123 ===
[1] /media/source1/Photos/2022/Summer/IMG_001.jpg 
      Size: 2.1MB | Date: 2022-07-15 | Quality Score: 95/100 ⭐ BEST
      Resolution: 4032x3024 | JPEG Quality: 98% | No compression artifacts
      Directory: /media/source1/Photos/2022/Summer
      Photo taken: 2022:07:15 14:30:22

[2] /media/source1/Backup/copy_of_IMG_001.jpg     
      Size: 1.8MB | Date: 2022-08-20 | Quality Score: 78/100
      Resolution: 4032x3024 | JPEG Quality: 85% | Minor compression artifacts
      Directory: /media/source1/Backup/Old Photos
      Photo taken: 2022:07:15 14:30:22

[3] /media/source2/Random/IMG_001_backup.jpg      
      Size: 1.2MB | Date: 2022-09-05 | Quality Score: 65/100
      Resolution: 3024x2268 | JPEG Quality: 75% | Heavy compression, lower resolution
      Directory: /media/source2/Random
      Photo taken: 2022:07:15 14:30:22

🎯 RECOMMENDATION: Keep [1] (highest quality, best folder location)
   Remove [2,3] (lower quality, less meaningful locations)

Options:
  auto    - Accept quality-based recommendation  
  k 1     - Keep file 1, remove others (same as recommendation)
  r 2 3   - Remove files 2 and 3, keep file 1
  v 1     - View file 1 in image viewer
  c 1 2 3 - Compare all files side-by-side
  i 1     - Show detailed EXIF info for file 1
  s       - Skip this group
  q       - Quit verification
```

---

## Script File Structure

**Your local development structure:**
```
scripts/
└── media/
    ├── discover_media.sh           # From Phase 1
    ├── analyze_duplicates.sh       # New - finds duplicate groups
    ├── visual_verify.sh           # New - interactive verification
    ├── generate_thumbnails.sh     # New - creates preview images
    └── safe_remove.sh             # For Phase 3
```

---

## Expected Results After Phase 2

1. **Duplicate Analysis Report** (`/data/duplicates/reports/duplicate_summary.txt`):
    - Total duplicate groups found
    - Potential space savings
    - File type breakdown

2. **Duplicate Groups** (`/data/duplicates/groups/group_*.txt`):
    - Each file contains one group of identical files
    - Organized for systematic verification

3. **Thumbnail Collection** (`/data/duplicates/thumbnails/`):
    - Small preview images for quick verification
    - Organized by group number

4. **Removal Decisions** (`/data/duplicates/removal_decisions.txt`):
    - Your verified decisions about which files to remove
    - Safe input for Phase 3

5. **Verification Log** (`/data/logs/visual_verification_*.log`):
    - Complete record of your verification session
    - Can resume if interrupted

---

## Time Estimates

- **Duplicate Analysis**: 30-60 minutes (automatic)
- **Thumbnail Generation**: 1-2 hours (automatic)
- **Visual Verification**: 2-8 hours (depends on duplicate count and your review speed)

---

## Next: Phase 3

Once Phase 2 is complete, you'll have a safe, verified list of files to remove. Phase 3 will execute the removal with multiple safety checks and verification steps.

**Ready to start Phase 2?**