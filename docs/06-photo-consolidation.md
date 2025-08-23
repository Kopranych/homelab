# Complete Photo Recovery & Deduplication Guide

**System Setup:**
- Mini PC with 1TB NVMe drive (optimized partitioning)
- Two old drives: 512GB SSD (sdb) and 1TB External (sdc)
- Millions of files with potential duplicates across complex folder structures
- Goal: Clean, organized photo collection in `/data` with verification

---

## Phase 1: System Preparation & Discovery

### Step 1: Verify System Setup
```bash
# Check your partition layout
lsblk

# Expected output:
# nvme0n1         1TB NVMe
# ├─nvme0n1p1     1G  EFI
# ├─nvme0n1p2     1G  Boot  
# ├─nvme0n1p3    50G  Root /
# ├─nvme0n1p4    20G  Home /home
# ├─nvme0n1p5   911GB Photos /data
# └─nvme0n1p6    16G  Swap
# sdb             512G SSD (source drive 1)
# sdc             1TB External (source drive 2)

# Verify mount points
df -h | grep -E "(nvme0n1|sdb|sdc)"

# Check available space on target partition
df -h /data
```

### Step 2: Create Working Directories
```bash
# Create organized structure on target drive
sudo mkdir -p /data/{incoming,staging,final,duplicates,logs}
sudo mkdir -p /data/staging/{verified,rejected}
sudo mkdir -p /data/final/{by-date,by-folder,metadata}

# Set proper ownership
sudo chown -R $USER:$USER /data

# Create temporary working space
mkdir -p /home/$USER/{scripts,manifests,reports}
```

### Step 3: Install Required Tools
```bash
# Update system
sudo apt update

# Install deduplication and analysis tools
sudo apt install -y \
  fdupes \        # Find and remove duplicate files by comparing content
  rdfind \        # Advanced duplicate finder with dry-run capabilities
  exiftool \      # Read/write metadata from photos/videos (dates, GPS, camera info)
  imagemagick \   # Image processing toolkit (convert, resize, analyze images)
  ffmpeg \        # Video processing toolkit (convert, analyze, extract info from videos)
  tree \          # Display directory structure in tree format for verification
  pv \            # Pipe Viewer - shows progress bars for long-running operations
  parallel \      # Run commands in parallel for faster processing
  jq \            # JSON processor for handling metadata and configuration files
  sqlite3         # Database for organizing and querying file information

# Verify installation
echo "Tools installed successfully:"
which fdupes rdfind exiftool convert ffmpeg pv parallel jq
```

### Step 4: Deploy Discovery Script
```bash
# Option A: Copy from your local development machine (RECOMMENDED)
# From your local machine, copy the script to your mini PC:
scp scripts/media/discover_media.sh $USER@$HOMELAB_HOST:/home/$USER/scripts/discover_media.sh

# Make it executable on the remote machine
ssh $USER@$HOMELAB_HOST "chmod +x /home/$USER/scripts/discover_media.sh"

# Option B: Create script directly on mini PC (if needed)
# Only use this if you can't use scp
cat > /home/$USER/scripts/discover_media.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Configuration - Comprehensive photo and video formats
PHOTO_EXT='jpg|jpeg|png|heic|heif|gif|bmp|tiff|tif|webp|cr2|nef|arw|dng|raf|orf|rw2|pef|srw|x3f'
VIDEO_EXT='mp4|mov|avi|mkv|wmv|m4v|3gp|mts|m2ts|flv|webm|mpg|mpeg|m2v|vob|ts|asf|rm|rmvb|ogv|divx|xvid'
EXT="${PHOTO_EXT}|${VIDEO_EXT}"
LOGFILE="/data/logs/discovery_$(date +%Y%m%d_%H%M%S).log"
MANIFEST_DIR="/home/$USER/manifests"

# Ensure output directory exists
mkdir -p "$MANIFEST_DIR"
mkdir -p "$(dirname "$LOGFILE")"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"
}

# Function to discover files from a source
discover_source() {
    local source="$1"
    local output_name="$2"
    local manifest="$MANIFEST_DIR/${output_name}_manifest.sha256"
    local stats="$MANIFEST_DIR/${output_name}_stats.txt"
    
    log "Starting discovery of: $source"
    log "Output manifest: $manifest"
    
    # Clear previous results
    > "$manifest"
    > "$stats"
    
    # Count total files first (for progress)
    log "Counting files in $source..."
    local total_files
    total_files=$(find "$source" -type f -iregex ".*\.($EXT)$" | wc -l)
    log "Found $total_files media files to process"
    
    # Create manifest with progress
    log "Creating SHA256 manifest..."
    find "$source" -type f -iregex ".*\.($EXT)$" -print0 | \
        pv -l -s "$total_files" | \
        xargs -0 -P "$(nproc)" -I {} sha256sum {} >> "$manifest"
    
    # Generate statistics
    echo "=== Discovery Statistics for $source ===" > "$stats"
    echo "Total files: $total_files" >> "$stats"
    echo "Manifest created: $(date)" >> "$stats"
    echo "Source path: $source" >> "$stats"
    echo "" >> "$stats"
    
    # File type breakdown
    echo "=== File Types Found ===" >> "$stats"
    echo "Photos:" >> "$stats"
    awk '{print $2}' "$manifest" | \
        sed 's/.*\.//' | \
        tr '[:upper:]' '[:lower:]' | \
        grep -E "^($PHOTO_EXT)$" | \
        sort | uniq -c | sort -nr >> "$stats"
    
    echo "" >> "$stats"
    echo "Videos:" >> "$stats"
    awk '{print $2}' "$manifest" | \
        sed 's/.*\.//' | \
        tr '[:upper:]' '[:lower:]' | \
        grep -E "^($VIDEO_EXT)$" | \
        sort | uniq -c | sort -nr >> "$stats"
    
    echo "" >> "$stats"
    echo "All formats:" >> "$stats"
    awk '{print $2}' "$manifest" | \
        sed 's/.*\.//' | \
        tr '[:upper:]' '[:lower:]' | \
        sort | uniq -c | sort -nr >> "$stats"
    
    log "Discovery complete for $source"
    log "Files processed: $total_files"
    log "Manifest: $manifest"
    log "Statistics: $stats"
}

# Main execution
main() {
    if [ $# -eq 0 ]; then
        echo "Usage: $0 <source1> [source2] ..."
        echo "Example: $0 /media/sdb1 /media/sdc1"
        exit 1
    fi
    
    log "=== Media Discovery Started ==="
    log "Processing ${#@} source(s): $*"
    
    local source_num=1
    for source in "$@"; do
        if [ ! -d "$source" ]; then
            log "ERROR: Source directory '$source' does not exist"
            continue
        fi
        
        discover_source "$source" "source${source_num}"
        ((source_num++))
    done
    
    log "=== Discovery Complete ==="
    log "Check manifests in: $MANIFEST_DIR"
    log "Full log: $LOGFILE"
}

# Run main function
main "$@"
EOF

# Make script executable
chmod +x /home/$USER/scripts/discover_media.sh

# Verify the script
ls -la /home/$USER/scripts/discover_media.sh
```

### Step 5: Mount Source Drives (if not already mounted)
```bash
# Check if drives are already mounted
lsblk | grep -E "(sdb|sdc)"

# If not mounted, create mount points and mount
sudo mkdir -p /media/{source1,source2}

# Mount the drives (adjust partition numbers as needed)
sudo mount /dev/sdb1 /media/source1
sudo mount /dev/sdc1 /media/source2

# Verify mounts
df -h | grep -E "(source1|source2)"
```

### Step 6: Run Initial Discovery
```bash
# Start the comprehensive discovery process
# This will take a while - run in screen for safety (prevents interruption if SSH disconnects)
screen -S discovery

# In the screen session, run the discovery:
/home/$USER/scripts/discover_media.sh /media/source1 /media/source2

# To detach from screen: Ctrl+A, then D
# To reattach later: screen -r discovery

# Monitor progress (from another terminal):
tail -f /data/logs/discovery_*.log

# When complete, check results:
ls -la /home/$USER/manifests/

# Screen commands reference:
# screen -S discovery     # Create new session named 'discovery'
# screen -r discovery     # Reattach to session
# screen -list           # List all sessions
# Ctrl+A, D             # Detach from session
# Ctrl+A, K             # Kill current session
```

---

## What This Step Accomplishes

1. **System Verification** - Confirms your optimized partition layout is working
2. **Tool Installation** - Installs all necessary deduplication and media processing tools
3. **Directory Structure** - Creates organized workspace for the entire process
4. **Discovery Script** - Professional-grade script that:
   - Uses parallel processing for speed
   - Shows progress bars for large operations
   - Creates SHA256 manifests for duplicate detection
   - Generates detailed statistics
   - Logs everything with timestamps
5. **Safe Execution** - Runs in screen to prevent interruption

## Next Steps Preview

- **Phase 2**: Duplicate Analysis & Removal
- **Phase 3**: Content Verification & Sorting
- **Phase 4**: Final Organization & Validation

**Time Estimate for Step 1**: 30 minutes setup + 2-6 hours for discovery (depending on file count)