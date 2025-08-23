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