#!/usr/bin/env bash
set -euo pipefail

# Duplicate Analysis Script with Quality Intelligence
# Finds duplicate groups and ranks them by quality

MANIFEST_DIR="/home/$USER/manifests"
QUALITY_DIR="/data/quality"
DUPLICATES_DIR="/data/duplicates"
LOGFILE="/data/logs/duplicate_analysis_$(date +%Y%m%d_%H%M%S).log"

# Create directories
mkdir -p "$DUPLICATES_DIR"/{reports,groups,review}
mkdir -p "$(dirname "$LOGFILE")"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"
}

# Function to get quality score for a file
get_quality_score() {
    local filepath="$1"
    local quality_cache="$QUALITY_DIR/cache/quality_scores.txt"

    if [ -f "$quality_cache" ]; then
        # Look up quality score from cache
        local score=$(grep -F "$filepath|" "$quality_cache" 2>/dev/null | cut -d'|' -f2 | head -1)
        if [ -n "$score" ] && [[ "$score" =~ ^[0-9]+$ ]]; then
            echo "$score"
        else
            echo "50"  # Default middle score if not found
        fi
    else
        echo "50"  # Default if no quality analysis available
    fi
}

# Function to get file details with quality info
get_file_details() {
    local filepath="$1"
    local quality_cache="$QUALITY_DIR/cache/quality_scores.txt"

    if [ ! -f "$filepath" ]; then
        echo "FILE_NOT_FOUND|0|unknown|N/A|N/A|N/A|0|0"
        return
    fi

    # Basic file info
    local file_size=$(stat -c%s "$filepath" 2>/dev/null || echo 0)
    local file_date=$(stat -c%y "$filepath" 2>/dev/null | cut -d' ' -f1)
    local file_ext=$(echo "${filepath##*.}" | tr '[:upper:]' '[:lower:]')

    # Get quality info from cache if available
    if [ -f "$quality_cache" ]; then
        local quality_line=$(grep -F "$filepath|" "$quality_cache" 2>/dev/null | head -1)
        if [ -n "$quality_line" ]; then
            echo "$quality_line|$file_date|$file_ext"
            return
        fi
    fi

    # Fallback: basic quality estimation
    local basic_score=50
    case "$file_ext" in
        cr2|nef|arw|dng|raf|orf|rw2|pef|srw|x3f)
            basic_score=80  # RAW files get high score
            ;;
        jpg|jpeg)
            if [ "$file_size" -gt 2000000 ]; then basic_score=65; fi  # Large JPEG
            ;;
    esac

    echo "$filepath|$basic_score|unknown|N/A|N/A|N/A|0|$file_size|$file_date|$file_ext"
}

# Function to create enhanced duplicate groups
create_duplicate_groups() {
    local combined_manifest="$DUPLICATES_DIR/combined_manifest.sha256"

    log "Combining manifests from all sources..."
    cat "$MANIFEST_DIR"/*_manifest.sha256 > "$combined_manifest"

    log "Identifying duplicate groups..."

    # Find duplicates (same hash appearing multiple times)
    awk '{print $1}' "$combined_manifest" | \
        sort | uniq -d > "$DUPLICATES_DIR/duplicate_hashes.txt"

    local total_duplicate_hashes=$(wc -l < "$DUPLICATES_DIR/duplicate_hashes.txt")
    log "Found $total_duplicate_hashes unique files with duplicates"

    if [ "$total_duplicate_hashes" -eq 0 ]; then
        log "No duplicates found! Your collection is already clean."
        return 0
    fi

    # Create detailed duplicate groups with quality analysis
    local duplicate_group=1
    local total_duplicate_files=0
    local total_space_duplicates=0

    while IFS= read -r hash; do
        local group_file="$DUPLICATES_DIR/groups/group_$(printf "%05d" $duplicate_group).txt"

        log "Processing duplicate group $duplicate_group..."

        # Get all files with this hash and their quality info
        local temp_group="/tmp/group_temp_$$"
        grep "^$hash " "$combined_manifest" | awk '{$1=""; print substr($0,2)}' > "$temp_group"

        # Analyze each file in the group and collect quality data
        local group_data=()
        local best_score=0
        local best_file=""

        while IFS= read -r filepath; do
            local file_details=$(get_file_details "$filepath")
            local quality_score=$(echo "$file_details" | cut -d'|' -f2)

            group_data+=("$quality_score|$filepath|$file_details")

            # Track best quality file
            if [ "$quality_score" -gt "$best_score" ]; then
                best_score="$quality_score"
                best_file="$filepath"
            fi
        done < "$temp_group"

        # Sort group by quality score (highest first)
        printf '%s\n' "${group_data[@]}" | sort -t'|' -k1,1nr > "${temp_group}_sorted"

        # Create detailed group file
        echo "=== Duplicate Group $duplicate_group (SHA256: $hash) ===" > "$group_file"
        echo "Files sorted by quality (best first):" >> "$group_file"
        echo "" >> "$group_file"

        local file_index=1
        local group_count=0
        local group_space=0

        while IFS='|' read -r score filepath details; do
            local file_size=$(echo "$details" | cut -d'|' -f8)
            local file_date=$(echo "$details" | cut -d'|' -f9)
            local file_ext=$(echo "$details" | cut -d'|' -f10)
            local dimensions=$(echo "$details" | cut -d'|' -f3)
            local jpeg_quality=$(echo "$details" | cut -d'|' -f4)
            local folder_bonus=$(echo "$details" | cut -d'|' -f7)

            # Format file size
            local size_human=$(numfmt --to=iec "$file_size" 2>/dev/null || echo "${file_size}B")

            # Quality indicator
            local quality_indicator=""
            if [ "$score" -ge 80 ]; then
                quality_indicator="⭐ EXCELLENT"
            elif [ "$score" -ge 65 ]; then
                quality_indicator="✓ GOOD"
            elif [ "$score" -ge 45 ]; then
                quality_indicator="~ FAIR"
            else
                quality_indicator="✗ POOR"
            fi

            # Best file indicator
            local best_indicator=""
            if [ "$filepath" = "$best_file" ]; then
                best_indicator="🎯 RECOMMENDED"
            fi

            echo "[$file_index] $filepath" >> "$group_file"
            echo "      Quality Score: $score/100 $quality_indicator $best_indicator" >> "$group_file"
            echo "      Size: $size_human | Date: $file_date | Format: ${file_ext^^}" >> "$group_file"

            if [ "$dimensions" != "unknown" ]; then
                echo "      Resolution: $dimensions" >> "$group_file"
            fi

            if [ "$jpeg_quality" != "N/A" ]; then
                echo "      JPEG Quality: ${jpeg_quality}%" >> "$group_file"
            fi

            local dir_path=$(dirname "$filepath")
            echo "      Directory: $dir_path" >> "$group_file"

            # Folder context explanation
            if [ "$folder_bonus" -gt 0 ]; then
                echo "      Folder: ✓ Meaningful location (+$folder_bonus points)" >> "$group_file"
            elif [ "$folder_bonus" -lt 0 ]; then
                echo "      Folder: ⚠ Backup/temp location ($folder_bonus points)" >> "$group_file"
            fi

            echo "" >> "$group_file"

            ((file_index++))
            ((group_count++))
            group_space=$((group_space + file_size))
        done < "${temp_group}_sorted"

        # Group summary
        local removable_count=$((group_count - 1))
        local removable_space=$((group_space - $(echo "$group_data" | head -1 | cut -d'|' -f8 2>/dev/null || echo "$file_size")))
        local space_human=$(numfmt --to=iec "$removable_space" 2>/dev/null || echo "${removable_space}B")

        echo "=== GROUP SUMMARY ===" >> "$group_file"
        echo "Total files in group: $group_count" >> "$group_file"
        echo "Recommended: Keep file [1] (highest quality)" >> "$group_file"
        echo "Can remove: $removable_count files" >> "$group_file"
        echo "Space savings: $space_human" >> "$group_file"
        echo "" >> "$group_file"
        echo "Best file: $best_file" >> "$group_file"
        echo "Quality score: $best_score/100" >> "$group_file"

        # Update totals
        total_duplicate_files=$((total_duplicate_files + group_count))
        total_space_duplicates=$((total_space_duplicates + removable_space))

        # Cleanup
        rm -f "$temp_group" "${temp_group}_sorted"

        ((duplicate_group++))

        # Progress update
        if (( duplicate_group % 50 == 0 )); then
            log "Processed $duplicate_group groups..."
        fi

    done < "$DUPLICATES_DIR/duplicate_hashes.txt"

    # Generate comprehensive summary report
    generate_summary_report "$total_duplicate_hashes" "$total_duplicate_files" "$total_space_duplicates"
}

# Function to generate summary report
generate_summary_report() {
    local unique_groups="$1"
    local total_files="$2"
    local total_space="$3"

    local summary_report="$DUPLICATES_DIR/reports/duplicate_summary.txt"
    local space_human=$(numfmt --to=iec "$total_space" 2>/dev/null || echo "${total_space}B")

    log "Generating comprehensive duplicate analysis report..."

    cat > "$summary_report" << EOL
=== DUPLICATE ANALYSIS SUMMARY ===
Analysis completed: $(date)

=== OVERVIEW ===
• Total unique duplicate groups: $unique_groups
• Total duplicate files found: $total_files
• Files that can be removed: $((total_files - unique_groups))
• Potential space savings: $space_human

=== QUALITY-BASED RECOMMENDATIONS ===
• Each group ranked by quality score (0-100)
• RAW files automatically prioritized
• High-resolution, low-compression preferred
• Meaningful folder locations favored

=== TOP SPACE-WASTING GROUPS ===
EOL

    # Find groups with largest space savings
    for group_file in "$DUPLICATES_DIR/groups"/group_*.txt; do
        if [ -f "$group_file" ]; then
            local space_line=$(grep "Space savings:" "$group_file" | head -1)
            local group_num=$(basename "$group_file" .txt | sed 's/group_//')
            if [ -n "$space_line" ]; then
                echo "Group $group_num: $space_line"
            fi
        fi
    done | sort -k3 -hr | head -10 >> "$summary_report"

    cat >> "$summary_report" << EOL

=== QUALITY DISTRIBUTION ===
EOL

    # Analyze quality distribution across groups
    local excellent=0 good=0 fair=0 poor=0
    for group_file in "$DUPLICATES_DIR/groups"/group_*.txt; do
        if [ -f "$group_file" ]; then
            local best_score=$(grep "Quality Score:" "$group_file" | head -1 | grep -o '[0-9]\+' | head -1)
            if [ -n "$best_score" ]; then
                if [ "$best_score" -ge 80 ]; then ((excellent++))
                elif [ "$best_score" -ge 65 ]; then ((good++))
                elif [ "$best_score" -ge 45 ]; then ((fair++))
                else ((poor++))
                fi
            fi
        fi
    done

    cat >> "$summary_report" << EOL
• Groups with excellent quality (80+): $excellent
• Groups with good quality (65-79): $good
• Groups with fair quality (45-64): $fair
• Groups with poor quality (<45): $poor

=== NEXT STEPS ===
1. Review duplicate groups: $DUPLICATES_DIR/groups/
2. Run visual verification: ./visual_verify.sh
3. Groups are pre-sorted by quality for easy decision-making
4. Use 'auto' command to accept quality-based recommendations
5. Execute safe removal in Phase 3

=== FILES & LOGS ===
• Summary report: $summary_report
• Duplicate groups: $DUPLICATES_DIR/groups/
• Full log: $LOGFILE
• Quality cache: $QUALITY_DIR/cache/quality_scores.txt

Total groups created: $unique_groups
EOL

    log "Summary report generated: $summary_report"
}

# Main execution
main() {
    log "=== Duplicate Analysis with Quality Intelligence Started ==="

    # Check if manifests exist
    if [ ! -d "$MANIFEST_DIR" ] || [ -z "$(ls -A "$MANIFEST_DIR"/*_manifest.sha256 2>/dev/null)" ]; then
        log "ERROR: No discovery manifests found. Run Phase 1 first."
        exit 1
    fi

    # Check if quality analysis was run (optional but recommended)
    if [ ! -f "$QUALITY_DIR/cache/quality_scores.txt" ]; then
        log "WARNING: No quality analysis found. Run quality_analyzer.sh first for better results."
        log "Proceeding with basic quality estimation..."
    else
        log "Using quality analysis data for intelligent duplicate ranking."
    fi

    # Run duplicate analysis
    create_duplicate_groups

    log "=== Duplicate Analysis Complete ==="
    log "Summary report: $DUPLICATES_DIR/reports/duplicate_summary.txt"
    log "Duplicate groups: $DUPLICATES_DIR/groups/"
    log "Ready for Phase 2 visual verification!"
}

# Run main function
main "$@"