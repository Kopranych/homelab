#!/usr/bin/env bash
set -euo pipefail

# Quality Analyzer Script for Photo Deduplication
# Analyzes photo quality metrics for intelligent duplicate selection

MANIFEST_DIR="/home/$USER/manifests"
QUALITY_DIR="/data/quality"
LOGFILE="/data/logs/quality_analysis_$(date +%Y%m%d_%H%M%S).log"

# Create directories
mkdir -p "$QUALITY_DIR"/{reports,cache}
mkdir -p "$(dirname "$LOGFILE")"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"
}

# Function to analyze photo quality
analyze_photo_quality() {
    local file="$1"
    local quality_score=0

    # Skip if file doesn't exist
    if [ ! -f "$file" ]; then
        echo "0|ERROR|File not found"
        return
    fi

    # Get basic file info
    local file_size=$(stat -c%s "$file" 2>/dev/null || echo 0)
    local file_ext=$(echo "${file##*.}" | tr '[:upper:]' '[:lower:]')

    # Base score from file size (larger is usually better)
    local size_score=$((file_size / 100000)) # 1 point per 100KB
    if [ $size_score -gt 30 ]; then size_score=30; fi # Cap at 30 points
    quality_score=$((quality_score + size_score))

    # Get image dimensions and technical details
    local dimensions=""
    local jpeg_quality=""
    local color_depth=""
    local has_exif=""

    if command -v identify >/dev/null 2>&1; then
        # Use ImageMagick to get image info
        local img_info=$(identify -verbose "$file" 2>/dev/null || echo "")
        if [ -n "$img_info" ]; then
            # Extract dimensions
            dimensions=$(echo "$img_info" | grep "Geometry:" | head -1 | awk '{print $2}' | cut -d+ -f1)

            # Extract color depth
            color_depth=$(echo "$img_info" | grep "Depth:" | head -1 | awk '{print $2}')

            # For JPEG files, try to get quality
            if [[ "$file_ext" == "jpg" || "$file_ext" == "jpeg" ]]; then
                if command -v jpeginfo >/dev/null 2>&1; then
                    local jpeg_info=$(jpeginfo -c "$file" 2>/dev/null || echo "")
                    if [[ "$jpeg_info" =~ ([0-9]+)% ]]; then
                        jpeg_quality="${BASH_REMATCH[1]}"
                    fi
                fi

                # Alternative method using ImageMagick
                if [ -z "$jpeg_quality" ]; then
                    jpeg_quality=$(echo "$img_info" | grep -i "quality" | head -1 | grep -o '[0-9]\+' | head -1 || echo "")
                fi
            fi
        fi
    fi

    # Resolution scoring
    if [ -n "$dimensions" ]; then
        local width=$(echo "$dimensions" | cut -dx -f1)
        local height=$(echo "$dimensions" | cut -dx -f2)
        local megapixels=$(( (width * height) / 1000000 ))

        # Resolution bonus: 1-15 points based on megapixels
        local res_bonus=$megapixels
        if [ $res_bonus -gt 15 ]; then res_bonus=15; fi
        quality_score=$((quality_score + res_bonus))
    fi

    # RAW file bonus (highest quality)
    case "$file_ext" in
        cr2|nef|arw|dng|raf|orf|rw2|pef|srw|x3f)
            quality_score=$((quality_score + 20))
            ;;
    esac

    # JPEG quality bonus
    if [ -n "$jpeg_quality" ]; then
        if [ "$jpeg_quality" -ge 95 ]; then
            quality_score=$((quality_score + 10))
        elif [ "$jpeg_quality" -ge 85 ]; then
            quality_score=$((quality_score + 5))
        elif [ "$jpeg_quality" -lt 70 ]; then
            quality_score=$((quality_score - 5))  # Penalty for low quality
        fi
    fi

    # Color depth bonus
    if [ -n "$color_depth" ]; then
        if [ "$color_depth" -ge 24 ]; then
            quality_score=$((quality_score + 3))
        fi
    fi

    # EXIF data completeness check
    if command -v exiftool >/dev/null 2>&1; then
        local exif_count=$(exiftool "$file" 2>/dev/null | wc -l)
        if [ "$exif_count" -gt 20 ]; then
            has_exif="complete"
            quality_score=$((quality_score + 5))
        elif [ "$exif_count" -gt 5 ]; then
            has_exif="partial"
            quality_score=$((quality_score + 2))
        else
            has_exif="minimal"
        fi
    fi

    # Folder context scoring
    local folder_bonus=0
    local dir_path=$(dirname "$file")
    local dir_name=$(basename "$dir_path")

    # Meaningful folder names (bonus points)
    if [[ "$dir_path" =~ (202[0-9]|Summer|Winter|Spring|Fall|Vacation|Trip|Wedding|Birthday|Christmas|Holiday) ]]; then
        folder_bonus=10
    # Backup/copy folders (penalty)
    elif [[ "$dir_path" =~ (Backup|Copy|Old|Archive|Temp) ]]; then
        folder_bonus=-5
    # Random/messy folders (bigger penalty)
    elif [[ "$dir_path" =~ (Random|Misc|Downloads|Desktop|Untitled) ]]; then
        folder_bonus=-10
    fi
    quality_score=$((quality_score + folder_bonus))

    # Ensure score is within bounds
    if [ $quality_score -lt 0 ]; then quality_score=0; fi
    if [ $quality_score -gt 100 ]; then quality_score=100; fi

    # Output format: score|dimensions|jpeg_quality|color_depth|has_exif|folder_bonus|file_size
    echo "${quality_score}|${dimensions:-unknown}|${jpeg_quality:-N/A}|${color_depth:-N/A}|${has_exif:-N/A}|${folder_bonus}|${file_size}"
}

# Function to process all files from manifests
process_manifests() {
    log "Starting quality analysis of all discovered files..."

    local quality_report="$QUALITY_DIR/reports/quality_analysis.txt"
    local quality_cache="$QUALITY_DIR/cache/quality_scores.txt"

    # Initialize files
    echo "# Quality Analysis Report - $(date)" > "$quality_report"
    echo "# Format: filepath|quality_score|dimensions|jpeg_quality|color_depth|exif|folder_bonus|file_size" > "$quality_cache"

    # Combine all manifests
    local combined_manifest="$QUALITY_DIR/cache/all_files.txt"
    cat "$MANIFEST_DIR"/*_manifest.sha256 > "$combined_manifest"

    local total_files=$(wc -l < "$combined_manifest")
    local processed=0

    log "Processing $total_files files for quality analysis..."

    # Process files with progress
    while IFS= read -r line; do
        local hash=$(echo "$line" | awk '{print $1}')
        local filepath=$(echo "$line" | awk '{$1=""; print substr($0,2)}')

        if [ -f "$filepath" ]; then
            local quality_info=$(analyze_photo_quality "$filepath")
            echo "$filepath|$quality_info" >> "$quality_cache"

            # Progress indicator
            ((processed++))
            if (( processed % 100 == 0 )); then
                local percent=$((processed * 100 / total_files))
                log "Progress: $processed/$total_files files ($percent%)"
            fi
        fi
    done < "$combined_manifest"

    log "Quality analysis complete: $processed files analyzed"

    # Generate summary report
    generate_quality_report "$quality_cache" "$quality_report"
}

# Function to generate quality summary report
generate_quality_report() {
    local cache_file="$1"
    local report_file="$2"

    log "Generating quality analysis summary report..."

    cat >> "$report_file" << EOL

=== QUALITY ANALYSIS SUMMARY ===
Analysis completed: $(date)
Total files analyzed: $(wc -l < "$cache_file")

=== QUALITY SCORE DISTRIBUTION ===
EOL

    # Quality score distribution
    awk -F'|' '{print $2}' "$cache_file" | grep -E '^[0-9]+$' | sort -n | uniq -c | sort -nr >> "$report_file"

    cat >> "$report_file" << EOL

=== HIGH QUALITY FILES (Score > 80) ===
EOL

    # High quality files
    awk -F'|' '$2 > 80 {print $2 " - " $1}' "$cache_file" | sort -nr | head -20 >> "$report_file"

    cat >> "$report_file" << EOL

=== LOW QUALITY FILES (Score < 30) ===
EOL

    # Low quality files
    awk -F'|' '$2 < 30 && $2 != "ERROR" {print $2 " - " $1}' "$cache_file" | sort -n | head -20 >> "$report_file"

    cat >> "$report_file" << EOL

=== RAW FILES FOUND ===
EOL

    # RAW files (usually highest quality)
    grep -iE '\.(cr2|nef|arw|dng|raf|orf|rw2|pef|srw|x3f)' "$cache_file" | wc -l >> "$report_file"
    echo "RAW files:" >> "$report_file"
    grep -iE '\.(cr2|nef|arw|dng|raf|orf|rw2|pef|srw|x3f)' "$cache_file" | head -10 >> "$report_file"

    log "Quality report generated: $report_file"
}

# Main execution
main() {
    log "=== Photo Quality Analysis Started ==="

    # Check if manifests exist
    if [ ! -d "$MANIFEST_DIR" ] || [ -z "$(ls -A "$MANIFEST_DIR"/*_manifest.sha256 2>/dev/null)" ]; then
        log "ERROR: No discovery manifests found. Run Phase 1 first."
        exit 1
    fi

    # Check required tools
    local missing_tools=()
    for tool in identify exiftool jpeginfo; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools+=("$tool")
        fi
    done

    if [ ${#missing_tools[@]} -gt 0 ]; then
        log "WARNING: Missing tools: ${missing_tools[*]}"
        log "Quality analysis will be limited. Install: sudo apt install imagemagick exiftool jpeginfo"
    fi

    # Run quality analysis
    process_manifests

    log "=== Quality Analysis Complete ==="
    log "Results in: $QUALITY_DIR/reports/quality_analysis.txt"
    log "Cache file: $QUALITY_DIR/cache/quality_scores.txt"
    log "Log file: $LOGFILE"
}

# Run main function
main "$@"