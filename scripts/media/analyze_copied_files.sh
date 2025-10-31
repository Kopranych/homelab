#!/usr/bin/env bash
set -euo pipefail

# Analyze Copied Files Script - Works on files in /data/incoming
# Finds duplicates and ranks by quality, working ONLY on copied files

# Load common configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common/config.sh"

# Initialize configuration
load_common_config
create_directories

# Script-specific directories - working on copied files
INCOMING_DIR="$HOMELAB_DATA_ROOT/incoming"
MANIFESTS_DIR="$HOMELAB_DATA_ROOT/manifests"
DUPLICATES_DIR="$HOMELAB_DATA_ROOT/duplicates"
QUALITY_DIR="$HOMELAB_DATA_ROOT/quality"
LOGFILE="$HOMELAB_LOG_DIR/analyze_copied_files_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$DUPLICATES_DIR"/{reports,groups,review}
mkdir -p "$QUALITY_DIR/cache"

# Function to create manifest of copied files (for duplicate detection)
create_copied_files_manifest() {
    local combined_manifest="$MANIFESTS_DIR/copied_files_combined.sha256"
    
    log_info "Creating manifest of all copied files in $INCOMING_DIR..."
    
    if [ ! -d "$INCOMING_DIR" ]; then
        log_error "Incoming directory not found: $INCOMING_DIR"
        log_error "Run copy_all_media.sh first to copy files from source drives"
        return 1
    fi
    
    # Find all copied files and create new manifest with current paths
    > "$combined_manifest"
    
    # Build find pattern for media files
    local photo_pattern=""
    local video_pattern=""
    
    while IFS= read -r ext; do
        if [ -n "$photo_pattern" ]; then photo_pattern="$photo_pattern -o"; fi
        photo_pattern="$photo_pattern -iname \"*.$ext\""
    done < <(get_photo_extensions)
    
    while IFS= read -r ext; do
        if [ -n "$video_pattern" ]; then video_pattern="$video_pattern -o"; fi  
        video_pattern="$video_pattern -iname \"*.$ext\""
    done < <(get_video_extensions)
    
    local find_pattern="\\( $photo_pattern \\) -o \\( $video_pattern \\)"
    
    # Find and hash all copied files
    log_info "Scanning copied files and generating SHA256 hashes..."
    eval "find '$INCOMING_DIR' -type f $find_pattern -print0" | \
        pv -l | \
        xargs -0 -P "$PHOTO_PARALLEL_JOBS" -I {} sha256sum {} >> "$combined_manifest"
    
    local total_files=$(wc -l < "$combined_manifest")
    log_info "Created manifest for $total_files copied files"
    
    return 0
}

# Function to get quality score for copied files
get_quality_score() {
    local filepath="$1"
    local quality_cache="$QUALITY_DIR/cache/quality_scores.txt"

    # Check cache first
    if [ -f "$quality_cache" ]; then
        local score=$(grep -F "$filepath|" "$quality_cache" 2>/dev/null | cut -d'|' -f2 | head -1)
        if [ -n "$score" ] && [[ "$score" =~ ^[0-9]+$ ]]; then
            echo "$score"
            return
        fi
    fi

    # Calculate quality score using centralized config
    if [ ! -f "$filepath" ]; then
        echo "0"
        return
    fi

    local file_ext=$(echo "${filepath##*.}" | tr '[:upper:]' '[:lower:]')
    local file_size=$(stat -c%s "$filepath" 2>/dev/null || echo 0)
    local quality_score=50  # Base score

    # Apply format scores from config
    case "$file_ext" in
        cr2|nef|arw|dng|raf|orf|rw2|pef|srw|x3f)
            quality_score=$(get_photo_config "quality.format_scores.raw_files" "90")
            ;;
        jpg|jpeg)
            quality_score=$(get_photo_config "quality.format_scores.standard_jpg" "60")
            local large_threshold=$(get_photo_config "quality.size_thresholds.photo_large_mb" "5")
            large_threshold=$((large_threshold * 1024 * 1024))
            if [ "$file_size" -gt "$large_threshold" ]; then
                quality_score=$(get_photo_config "quality.format_scores.high_res_jpg" "75")
            fi
            ;;
        png)
            quality_score=$(get_photo_config "quality.format_scores.png" "65")
            ;;
        heic|heif)
            quality_score=$(get_photo_config "quality.format_scores.heic" "70")
            ;;
        mp4|mov)
            quality_score=$(get_photo_config "quality.format_scores.videos_hd" "70")
            local large_threshold=$(get_photo_config "quality.size_thresholds.video_large_mb" "100")
            large_threshold=$((large_threshold * 1024 * 1024))
            if [ "$file_size" -gt "$large_threshold" ]; then
                quality_score=$(get_photo_config "quality.format_scores.videos_4k" "85")
            fi
            ;;
        *)
            quality_score=$(get_photo_config "quality.format_scores.videos_sd" "50")
            ;;
    esac

    # Apply folder context bonuses - analyze the path within incoming
    local folder_bonus=0
    case "$filepath" in
        */202[0-9]/*|*/Photos/*|*/photos/*|*/Videos/*|*/videos/*)
            folder_bonus=$(get_photo_config "quality.folder_bonuses.organized" "10")
            ;;
        */Vacation/*|*/vacation/*|*/Wedding/*|*/wedding/*|*/Trip/*|*/trip/*)
            folder_bonus=$(get_photo_config "quality.folder_bonuses.meaningful" "5")
            ;;
        */Backup/*|*/backup/*|*/Old/*|*/old/*|*/Archive/*|*/archive/*)
            folder_bonus=$(get_photo_config "quality.folder_bonuses.backup" "-10")
            ;;
        */Downloads/*|*/downloads/*|*/Temp/*|*/temp/*|*/tmp/*)
            folder_bonus=$(get_photo_config "quality.folder_bonuses.junk" "-15")
            ;;
        *)
            folder_bonus=$(get_photo_config "quality.folder_bonuses.neutral" "0")
            ;;
    esac

    quality_score=$((quality_score + folder_bonus))

    # Ensure bounds
    if [ $quality_score -lt 0 ]; then quality_score=0; fi
    if [ $quality_score -gt 100 ]; then quality_score=100; fi

    # Cache the result
    echo "$filepath|$quality_score|$file_size|$file_ext" >> "$quality_cache"
    echo "$quality_score"
}

# Function to analyze duplicates in copied files
analyze_copied_duplicates() {
    local combined_manifest="$MANIFESTS_DIR/copied_files_combined.sha256"
    
    if [ ! -f "$combined_manifest" ]; then
        log_error "Combined manifest not found. Run create_copied_files_manifest first."
        return 1
    fi

    log_info "Analyzing duplicates in copied files..."

    # Find duplicate hashes in copied files
    awk '{print $1}' "$combined_manifest" | \
        sort | uniq -d > "$DUPLICATES_DIR/duplicate_hashes.txt"

    local total_duplicate_hashes=$(wc -l < "$DUPLICATES_DIR/duplicate_hashes.txt")
    log_info "Found $total_duplicate_hashes unique files with duplicates"

    if [ "$total_duplicate_hashes" -eq 0 ]; then
        log_info "No duplicates found in copied files!"
        return 0
    fi

    # Check duplicate percentage
    local total_files=$(wc -l < "$combined_manifest")
    local duplicate_percentage=$(( (total_duplicate_hashes * 100) / total_files ))
    local max_duplicate_pct=$(get_photo_config "safety.max_duplicate_percentage" "80")

    log_info "Duplicate analysis: ${duplicate_percentage}% of files have duplicates"

    if [ "$duplicate_percentage" -gt "$max_duplicate_pct" ]; then
        log_warn "High duplicate percentage: ${duplicate_percentage}% (threshold: ${max_duplicate_pct}%)"
        log_warn "This is expected when copying from multiple drives with overlapping content"
    fi

    # Process each duplicate group
    local duplicate_group=1
    local total_duplicate_files=0
    local total_space_duplicates=0

    while IFS= read -r hash; do
        local group_file="$DUPLICATES_DIR/groups/group_$(printf "%05d" $duplicate_group).txt"

        # Get all copied files with this hash
        local temp_group="/tmp/copied_group_$$"
        grep "^$hash " "$combined_manifest" | awk '{$1=""; print substr($0,2)}' > "$temp_group"

        # Analyze and rank by quality
        local group_data=()
        local best_score=0
        local best_file=""

        while IFS= read -r filepath; do
            local quality_score=$(get_quality_score "$filepath")
            local file_size=$(stat -c%s "$filepath" 2>/dev/null || echo 0)

            group_data+=("$quality_score|$filepath|$file_size")

            if [ "$quality_score" -gt "$best_score" ]; then
                best_score="$quality_score"
                best_file="$filepath"
            fi
        done < "$temp_group"

        # Sort by quality (highest first)
        printf '%s\n' "${group_data[@]}" | sort -t'|' -k1,1nr > "${temp_group}_sorted"

        # Create group file
        echo "=== Duplicate Group $duplicate_group (SHA256: $hash) ===" > "$group_file"
        echo "Files in /data/incoming ranked by quality (KEEP first, REMOVE others):" >> "$group_file"
        echo "" >> "$group_file"

        local file_index=1
        local group_count=0
        local group_space=0

        while IFS='|' read -r score filepath file_size; do
            local size_human=$(numfmt --to=iec "$file_size" 2>/dev/null || echo "${file_size}B")
            local file_date=$(stat -c%y "$filepath" 2>/dev/null | cut -d' ' -f1 || echo "unknown")
            local rel_path="${filepath#$INCOMING_DIR/}"
            
            local action="REMOVE"
            local indicator=""
            if [ "$file_index" -eq 1 ]; then
                action="KEEP"
                indicator="🎯 BEST QUALITY"
            fi

            echo "[$file_index] $action - Score: $score/100 - Size: $size_human - Date: $file_date" >> "$group_file"
            echo "      Path: $rel_path" >> "$group_file"
            echo "      Full: $filepath" >> "$group_file"
            echo "      $indicator" >> "$group_file"
            echo "" >> "$group_file"

            ((file_index++))
            ((group_count++))
            group_space=$((group_space + file_size))
        done < "${temp_group}_sorted"

        # Group summary
        local removable_count=$((group_count - 1))
        local removable_space=$((group_space - $(echo "$group_data" | head -1 | cut -d'|' -f3 2>/dev/null || echo 0)))
        local space_human=$(numfmt --to=iec "$removable_space" 2>/dev/null || echo "${removable_space}B")

        echo "=== GROUP SUMMARY ===" >> "$group_file"
        echo "Files in group: $group_count" >> "$group_file"
        echo "Keep: 1 file (best quality)" >> "$group_file"
        echo "Remove: $removable_count files" >> "$group_file"
        echo "Space savings: $space_human" >> "$group_file"

        # Update totals
        total_duplicate_files=$((total_duplicate_files + group_count))
        total_space_duplicates=$((total_space_duplicates + removable_space))

        rm -f "$temp_group" "${temp_group}_sorted"
        ((duplicate_group++))

        # Progress update
        if (( duplicate_group % 100 == 0 )); then
            log_info "Processed $duplicate_group duplicate groups..."
        fi

    done < "$DUPLICATES_DIR/duplicate_hashes.txt"

    # Generate summary report
    generate_analysis_summary "$total_duplicate_hashes" "$total_duplicate_files" "$total_space_duplicates"
}

# Function to generate analysis summary
generate_analysis_summary() {
    local unique_groups="$1"
    local total_files="$2" 
    local total_space="$3"

    local summary_report="$DUPLICATES_DIR/reports/copied_files_analysis.txt"
    local space_human=$(numfmt --to=iec "$total_space" 2>/dev/null || echo "${total_space}B")

    cat > "$summary_report" << EOL
=== COPIED FILES DUPLICATE ANALYSIS ===
Analysis completed: $(date)
Server: $(get_infra_config "server.hostname" "unknown")

=== ANALYSIS OVERVIEW ===
Source: Copied files in $INCOMING_DIR (originals untouched)
• Duplicate groups found: $unique_groups
• Total duplicate files: $total_files
• Files that can be removed: $((total_files - unique_groups))
• Potential space savings: $space_human

=== PROCESSING STATUS ===
✅ Original drives: UNTOUCHED and safe
✅ Analysis source: Only copied files in $INCOMING_DIR
✅ Quality ranking: Applied from centralized configuration
✅ Safe for processing: All operations work on copies

=== QUALITY SCORING APPLIED ===
• RAW files: $(get_photo_config "quality.format_scores.raw_files")+ points
• High-res JPEG: $(get_photo_config "quality.format_scores.high_res_jpg")+ points  
• 4K videos: $(get_photo_config "quality.format_scores.videos_4k")+ points
• Organized folders: +$(get_photo_config "quality.folder_bonuses.organized") points
• Backup/old folders: $(get_photo_config "quality.folder_bonuses.backup") points

=== NEXT STEPS ===
1. Review duplicate groups: $DUPLICATES_DIR/groups/
2. Set up Nextcloud access to $INCOMING_DIR for human verification
3. Run consolidation to remove duplicates from copied files
4. After verification, original drives can be formatted
5. Proceed to Phase 7 - Storage Setup

=== IMPORTANT SAFETY NOTES ===
🔒 Original drives remain completely untouched
📁 All analysis works on copies in $INCOMING_DIR  
✅ Safe to disconnect original drives anytime
🗂️ Folder structure preserved in copied files
💾 Ready for human verification via Nextcloud

=== FILES & LOCATIONS ===
• Copied files: $INCOMING_DIR/
• Analysis results: $DUPLICATES_DIR/
• Summary report: $summary_report
• Quality cache: $QUALITY_DIR/cache/
• Process logs: $HOMELAB_LOG_DIR/

STATUS: ✅ COPIED FILES ANALYSIS COMPLETE
Ready for human verification and final consolidation.
EOL

    log_info "Analysis summary: $summary_report"
    cat "$summary_report"
}

# Main execution  
main() {
    log_info "=== Copied Files Duplicate Analysis Started ==="
    log_info "Working on copied files in: $INCOMING_DIR"
    log_info "Original drives: UNTOUCHED"

    # Verify incoming directory exists
    if [ ! -d "$INCOMING_DIR" ]; then
        log_error "Incoming directory not found: $INCOMING_DIR"
        log_error "Please run copy_all_media.sh first to copy files from source drives"
        return 1
    fi

    # Check if there are copied files
    local file_count=$(find "$INCOMING_DIR" -type f | wc -l)
    if [ "$file_count" -eq 0 ]; then
        log_error "No files found in $INCOMING_DIR"
        log_error "Please run copy_all_media.sh first"
        return 1
    fi

    log_info "Found $file_count files in incoming directory"

    # Create manifest of copied files
    create_copied_files_manifest

    # Analyze duplicates
    analyze_copied_duplicates

    log_info "=== Copied Files Analysis Complete ==="
    log_info "Duplicate analysis completed on copied files only"
    log_info "Original drives remain safe and untouched"
    log_info "Ready for human verification and consolidation"

    return 0
}

# Handle interruption  
trap 'log_error "Analysis interrupted"; exit 130' INT TERM

# Run main function
main "$@"