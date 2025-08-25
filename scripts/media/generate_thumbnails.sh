#!/usr/bin/env bash
set -euo pipefail

# Thumbnail Generation Script
# Creates preview images for visual verification

DUPLICATES_DIR="/data/duplicates"
THUMBNAILS_DIR="$DUPLICATES_DIR/thumbnails"
LOGFILE="/data/logs/thumbnail_generation_$(date +%Y%m%d_%H%M%S).log"

# Configuration
THUMBNAIL_SIZE="300x300"
THUMBNAIL_QUALITY=85
MAX_PARALLEL_JOBS=$(nproc)

# Create directories
mkdir -p "$THUMBNAILS_DIR"/{groups,individual}
mkdir -p "$(dirname "$LOGFILE")"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"
}

# Function to create thumbnail for a single file
create_thumbnail() {
    local source_file="$1"
    local thumbnail_file="$2"

    # Skip if thumbnail already exists and is newer than source
    if [ -f "$thumbnail_file" ] && [ "$thumbnail_file" -nt "$source_file" ]; then
        return 0
    fi

    # Skip if source file doesn't exist
    if [ ! -f "$source_file" ]; then
        log "WARNING: Source file not found: $source_file"
        return 1
    fi

    # Create thumbnail directory if needed
    mkdir -p "$(dirname "$thumbnail_file")"

    # Get file extension
    local ext=$(echo "${source_file##*.}" | tr '[:upper:]' '[:lower:]')

    # Handle different file types
    case "$ext" in
        # Photo formats
        jpg|jpeg|png|tiff|tif|bmp|gif|webp)
            if command -v convert >/dev/null 2>&1; then
                convert "$source_file" -thumbnail "$THUMBNAIL_SIZE>" -quality "$THUMBNAIL_QUALITY" \
                    -background white -gravity center -extent "$THUMBNAIL_SIZE" \
                    "$thumbnail_file" 2>/dev/null || return 1
            else
                log "ERROR: ImageMagick 'convert' not found"
                return 1
            fi
            ;;

        # RAW formats - need special handling
        cr2|nef|arw|dng|raf|orf|rw2|pef|srw|x3f)
            if command -v convert >/dev/null 2>&1; then
                # Try to extract embedded thumbnail first (faster)
                convert "$source_file[0]" -thumbnail "$THUMBNAIL_SIZE>" -quality "$THUMBNAIL_QUALITY" \
                    -background white -gravity center -extent "$THUMBNAIL_SIZE" \
                    "$thumbnail_file" 2>/dev/null || {
                    # Fallback: full RAW conversion (slower but more reliable)
                    convert "$source_file" -thumbnail "$THUMBNAIL_SIZE>" -quality "$THUMBNAIL_QUALITY" \
                        -background white -gravity center -extent "$THUMBNAIL_SIZE" \
                        "$thumbnail_file" 2>/dev/null || return 1
                }
            else
                log "ERROR: ImageMagick not available for RAW processing"
                return 1
            fi
            ;;

        # HEIC/HEIF (modern iPhone format)
        heic|heif)
            if command -v convert >/dev/null 2>&1; then
                convert "$source_file" -thumbnail "$THUMBNAIL_SIZE>" -quality "$THUMBNAIL_QUALITY" \
                    -background white -gravity center -extent "$THUMBNAIL_SIZE" \
                    "$thumbnail_file" 2>/dev/null || return 1
            else
                log "ERROR: ImageMagick not available for HEIC processing"
                return 1
            fi
            ;;

        # Video formats - extract frame thumbnail
        mp4|mov|avi|mkv|wmv|m4v|3gp|mts|m2ts|flv|webm|mpg|mpeg|m2v|vob|ts|asf|rm|rmvb|ogv|divx|xvid)
            if command -v ffmpeg >/dev/null 2>&1; then
                # Extract frame at 10% of video duration
                ffmpeg -i "$source_file" -ss 00:00:01 -vframes 1 -q:v 2 \
                    -vf "scale=$THUMBNAIL_SIZE:force_original_aspect_ratio=decrease,pad=$THUMBNAIL_SIZE:(ow-iw)/2:(oh-ih)/2" \
                    "$thumbnail_file" 2>/dev/null || return 1
            else
                log "ERROR: ffmpeg not found for video thumbnail"
                return 1
            fi
            ;;

        *)
            log "WARNING: Unsupported format for thumbnail: $ext"
            return 1
            ;;
    esac

    return 0
}

# Function to generate thumbnails for all duplicate groups
generate_group_thumbnails() {
    log "Generating thumbnails for duplicate groups..."

    if [ ! -d "$DUPLICATES_DIR/groups" ]; then
        log "ERROR: No duplicate groups found. Run analyze_duplicates.sh first."
        return 1
    fi

    local group_files=("$DUPLICATES_DIR/groups"/group_*.txt)
    local total_groups=${#group_files[@]}
    local processed_groups=0
    local total_thumbnails=0
    local failed_thumbnails=0

    log "Found $total_groups duplicate groups to process"

    # Process each group
    for group_file in "${group_files[@]}"; do
        if [ ! -f "$group_file" ]; then continue; fi

        local group_num=$(basename "$group_file" .txt | sed 's/group_//')
        local group_thumb_dir="$THUMBNAILS_DIR/groups/group_$group_num"

        log "Processing group $group_num..."

        # Create group thumbnail directory
        mkdir -p "$group_thumb_dir"

        # Extract file paths from group file
        local file_index=1
        while IFS= read -r line; do
            if [[ "$line" =~ ^\[([0-9]+)\]\ (.+)$ ]]; then
                local file_path="${BASH_REMATCH[2]}"
                local thumb_name="file_${file_index}.jpg"
                local thumb_path="$group_thumb_dir/$thumb_name"

                # Generate thumbnail
                if create_thumbnail "$file_path" "$thumb_path"; then
                    ((total_thumbnails++))
                    # Create symlink with original filename for reference
                    local orig_name=$(basename "$file_path")
                    ln -sf "$thumb_name" "$group_thumb_dir/${orig_name}_thumb.jpg" 2>/dev/null || true
                else
                    ((failed_thumbnails++))
                    log "Failed to create thumbnail for: $file_path"
                fi

                ((file_index++))
            fi
        done < "$group_file"

        ((processed_groups++))

        # Progress update
        if (( processed_groups % 10 == 0 )); then
            log "Progress: $processed_groups/$total_groups groups processed"
        fi
    done

    log "Thumbnail generation complete:"
    log "  Groups processed: $processed_groups"
    log "  Thumbnails created: $total_thumbnails"
    log "  Failed thumbnails: $failed_thumbnails"
}

# Function to generate individual thumbnails for quick access
generate_individual_thumbnails() {
    log "Generating individual thumbnail index..."

    local individual_dir="$THUMBNAILS_DIR/individual"
    local index_file="$THUMBNAILS_DIR/thumbnail_index.txt"

    mkdir -p "$individual_dir"
    echo "# Thumbnail Index - $(date)" > "$index_file"
    echo "# Format: original_path|thumbnail_path|group_number|file_index" >> "$index_file"

    # Process all group thumbnails and create individual access
    for group_dir in "$THUMBNAILS_DIR/groups"/group_*; do
        if [ ! -d "$group_dir" ]; then continue; fi

        local group_num=$(basename "$group_dir" | sed 's/group_//')
        local group_file="$DUPLICATES_DIR/groups/group_$(printf "%05d" "$group_num").txt"

        if [ ! -f "$group_file" ]; then continue; fi

        # Read group file to get original paths
        local file_index=1
        while IFS= read -r line; do
            if [[ "$line" =~ ^\[([0-9]+)\]\ (.+)$ ]]; then
                local file_path="${BASH_REMATCH[2]}"
                local thumb_source="$group_dir/file_${file_index}.jpg"

                if [ -f "$thumb_source" ]; then
                    # Create individual thumbnail with unique name
                    local thumb_hash=$(echo "$file_path" | sha256sum | cut -c1-16)
                    local individual_thumb="$individual_dir/${thumb_hash}.jpg"

                    # Copy or link thumbnail
                    cp "$thumb_source" "$individual_thumb" 2>/dev/null || \
                    ln -sf "$thumb_source" "$individual_thumb" 2>/dev/null

                    # Update index
                    echo "$file_path|$individual_thumb|$group_num|$file_index" >> "$index_file"
                fi

                ((file_index++))
            fi
        done < "$group_file"
    done

    log "Individual thumbnail index created: $index_file"
}

# Function to create thumbnail grid for each group
create_group_grids() {
    log "Creating thumbnail grids for visual comparison..."

    local grids_dir="$THUMBNAILS_DIR/grids"
    mkdir -p "$grids_dir"

    for group_dir in "$THUMBNAILS_DIR/groups"/group_*; do
        if [ ! -d "$group_dir" ]; then continue; fi

        local group_num=$(basename "$group_dir" | sed 's/group_//')
        local grid_file="$grids_dir/group_${group_num}_grid.jpg"

        # Count thumbnails in group
        local thumb_count=$(find "$group_dir" -name "file_*.jpg" | wc -l)

        if [ "$thumb_count" -eq 0 ]; then continue; fi

        # Calculate grid dimensions
        local cols=3
        if [ "$thumb_count" -le 2 ]; then cols=$thumb_count; fi
        if [ "$thumb_count" -gt 6 ]; then cols=4; fi

        # Create montage grid
        if command -v montage >/dev/null 2>&1; then
            montage "$group_dir"/file_*.jpg -tile "${cols}x" -geometry "+5+5" \
                -background white -title "Duplicate Group $group_num" \
                "$grid_file" 2>/dev/null || {
                log "Failed to create grid for group $group_num"
            }
        fi
    done

    log "Thumbnail grids created in: $grids_dir"
}

# Function to generate summary report
generate_thumbnail_report() {
    local report_file="$THUMBNAILS_DIR/thumbnail_report.txt"

    log "Generating thumbnail summary report..."

    cat > "$report_file" << EOL
=== THUMBNAIL GENERATION REPORT ===
Generated: $(date)

=== DIRECTORY STRUCTURE ===
$THUMBNAILS_DIR/
├── groups/           # Thumbnails organized by duplicate group
│   ├── group_00001/  # Individual group thumbnails
│   ├── group_00002/
│   └── ...
├── individual/       # All thumbnails with unique names
├── grids/           # Comparison grids for each group
└── thumbnail_index.txt  # Index of all thumbnails

=== STATISTICS ===
EOL

    # Count statistics
    local total_groups=$(find "$THUMBNAILS_DIR/groups" -maxdepth 1 -type d -name "group_*" | wc -l)
    local total_thumbnails=$(find "$THUMBNAILS_DIR/groups" -name "file_*.jpg" | wc -l)
    local total_grids=$(find "$THUMBNAILS_DIR/grids" -name "*.jpg" 2>/dev/null | wc -l)
    local index_entries=$(grep -c "^[^#]" "$THUMBNAILS_DIR/thumbnail_index.txt" 2>/dev/null || echo 0)

    cat >> "$report_file" << EOL
• Duplicate groups with thumbnails: $total_groups
• Total thumbnails generated: $total_thumbnails
• Comparison grids created: $total_grids
• Index entries: $index_entries

=== USAGE ===
1. View group thumbnails: ls $THUMBNAILS_DIR/groups/group_XXXXX/
2. View comparison grid: feh $THUMBNAILS_DIR/grids/group_XXXXX_grid.jpg
3. Individual access: Use thumbnail_index.txt to find specific thumbnails
4. Integration with visual_verify.sh for interactive review

=== FILE SIZES ===
EOL

    # Directory sizes
    if command -v du >/dev/null 2>&1; then
        echo "Thumbnail storage usage:" >> "$report_file"
        du -sh "$THUMBNAILS_DIR"/* 2>/dev/null >> "$report_file" || echo "Could not calculate sizes" >> "$report_file"
    fi

    cat >> "$report_file" << EOL

=== LOG FILE ===
Full generation log: $LOGFILE
EOL

    log "Thumbnail report generated: $report_file"
}

# Function to verify thumbnail quality
verify_thumbnails() {
    log "Verifying thumbnail quality and coverage..."

    local verification_report="$THUMBNAILS_DIR/verification.txt"
    echo "=== THUMBNAIL VERIFICATION ===" > "$verification_report"
    echo "Checked: $(date)" >> "$verification_report"
    echo "" >> "$verification_report"

    local good_thumbs=0
    local bad_thumbs=0
    local missing_thumbs=0

    # Check each group
    for group_dir in "$THUMBNAILS_DIR/groups"/group_*; do
        if [ ! -d "$group_dir" ]; then continue; fi

        local group_num=$(basename "$group_dir" | sed 's/group_//')
        echo "Group $group_num:" >> "$verification_report"

        for thumb_file in "$group_dir"/file_*.jpg; do
            if [ -f "$thumb_file" ]; then
                # Check if thumbnail is valid
                if identify "$thumb_file" >/dev/null 2>&1; then
                    local size=$(identify -format "%wx%h" "$thumb_file" 2>/dev/null || echo "unknown")
                    echo "  ✓ $(basename "$thumb_file"): $size" >> "$verification_report"
                    ((good_thumbs++))
                else
                    echo "  ✗ $(basename "$thumb_file"): corrupted" >> "$verification_report"
                    ((bad_thumbs++))
                fi
            else
                ((missing_thumbs++))
            fi
        done
    done

    echo "" >> "$verification_report"
    echo "Summary:" >> "$verification_report"
    echo "  Good thumbnails: $good_thumbs" >> "$verification_report"
    echo "  Bad thumbnails: $bad_thumbs" >> "$verification_report"
    echo "  Missing thumbnails: $missing_thumbs" >> "$verification_report"

    log "Verification complete: $good_thumbs good, $bad_thumbs bad, $missing_thumbs missing"
    log "Verification report: $verification_report"
}

# Main execution
main() {
    log "=== Thumbnail Generation Started ==="

    # Check dependencies
    local missing_tools=()
    for tool in convert montage identify; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools+=("$tool")
        fi
    done

    if [ ${#missing_tools[@]} -gt 0 ]; then
        log "ERROR: Missing required tools: ${missing_tools[*]}"
        log "Install with: sudo apt install imagemagick"
        exit 1
    fi

    # Check for ffmpeg (optional, for video thumbnails)
    if ! command -v ffmpeg >/dev/null 2>&1; then
        log "WARNING: ffmpeg not found. Video thumbnails will be skipped."
        log "Install with: sudo apt install ffmpeg"
    fi

    # Check if duplicate groups exist
    if [ ! -d "$DUPLICATES_DIR/groups" ] || [ -z "$(ls -A "$DUPLICATES_DIR/groups"/*.txt 2>/dev/null)" ]; then
        log "ERROR: No duplicate groups found. Run analyze_duplicates.sh first."
        exit 1
    fi

    # Generate thumbnails
    generate_group_thumbnails

    # Create individual thumbnail access
    generate_individual_thumbnails

    # Create comparison grids
    create_group_grids

    # Generate reports
    generate_thumbnail_report

    # Verify thumbnail quality
    verify_thumbnails

    log "=== Thumbnail Generation Complete ==="
    log "Thumbnails: $THUMBNAILS_DIR/"
    log "Report: $THUMBNAILS_DIR/thumbnail_report.txt"
    log "Ready for visual verification!"
}

# Run main function
main "$@"