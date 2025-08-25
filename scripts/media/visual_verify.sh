#!/usr/bin/env bash
set -euo pipefail

# Visual Verification Script with Photo Previews
# Interactive verification of duplicate groups with quality recommendations

DUPLICATES_DIR="/data/duplicates"
THUMBNAILS_DIR="$DUPLICATES_DIR/thumbnails"
DECISIONS_FILE="$DUPLICATES_DIR/removal_decisions.txt"
LOGFILE="/data/logs/visual_verification_$(date +%Y%m%d_%H%M%S).log"

# Configuration
SESSION_STATE="$DUPLICATES_DIR/verification_session.txt"
BACKUP_DECISIONS="$DUPLICATES_DIR/removal_decisions_backup.txt"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"
}

# Function to display file information with quality details
show_file_info() {
    local filepath="$1"
    local index="$2"
    local quality_info="$3"

    if [ ! -f "$filepath" ]; then
        echo "[$index] ⚠️  FILE NOT FOUND: $filepath"
        return
    fi

    # Parse quality information
    local score=$(echo "$quality_info" | cut -d'|' -f2)
    local dimensions=$(echo "$quality_info" | cut -d'|' -f3)
    local jpeg_quality=$(echo "$quality_info" | cut -d'|' -f4)
    local color_depth=$(echo "$quality_info" | cut -d'|' -f5)
    local exif_status=$(echo "$quality_info" | cut -d'|' -f6)
    local folder_bonus=$(echo "$quality_info" | cut -d'|' -f7)
    local file_size=$(echo "$quality_info" | cut -d'|' -f8)
    local file_date=$(echo "$quality_info" | cut -d'|' -f9)
    local file_ext=$(echo "$quality_info" | cut -d'|' -f10)

    # Format file size
    local size_human=$(numfmt --to=iec "$file_size" 2>/dev/null || echo "${file_size}B")

    # Quality indicator with emoji
    local quality_indicator=""
    local quality_emoji=""
    if [ "$score" -ge 80 ]; then
        quality_indicator="EXCELLENT"
        quality_emoji="⭐"
    elif [ "$score" -ge 65 ]; then
        quality_indicator="GOOD"
        quality_emoji="✅"
    elif [ "$score" -ge 45 ]; then
        quality_indicator="FAIR"
        quality_emoji="⚠️"
    else
        quality_indicator="POOR"
        quality_emoji="❌"
    fi

    # Display main info
    echo "[$index] $filepath"
    echo "      Quality: $score/100 $quality_emoji $quality_indicator"
    echo "      Size: $size_human | Date: $file_date | Format: ${file_ext^^}"

    # Display technical details if available
    if [ "$dimensions" != "unknown" ] && [ "$dimensions" != "N/A" ]; then
        echo "      Resolution: $dimensions"
    fi

    if [ "$jpeg_quality" != "N/A" ] && [ -n "$jpeg_quality" ]; then
        echo "      JPEG Quality: ${jpeg_quality}%"
    fi

    if [ "$color_depth" != "N/A" ] && [ -n "$color_depth" ]; then
        echo "      Color Depth: ${color_depth}-bit"
    fi

    # Directory context
    local dir_path=$(dirname "$filepath")
    echo "      Directory: $dir_path"

    # Folder context explanation
    if [ "$folder_bonus" -gt 0 ]; then
        echo "      📁 Meaningful location (+$folder_bonus quality points)"
    elif [ "$folder_bonus" -lt 0 ]; then
        echo "      📁 Backup/temp location ($folder_bonus quality points)"
    else
        echo "      📁 Neutral location"
    fi

    # EXIF status
    if [ "$exif_status" = "complete" ]; then
        echo "      📷 Complete metadata preserved"
    elif [ "$exif_status" = "partial" ]; then
        echo "      📷 Partial metadata"
    elif [ "$exif_status" = "minimal" ]; then
        echo "      📷 Minimal metadata (possibly processed)"
    fi
}

# Function to show thumbnail if available
show_thumbnail() {
    local filepath="$1"
    local group_num="$2"
    local file_index="$3"

    local thumb_path="$THUMBNAILS_DIR/groups/group_$(printf "%05d" "$group_num")/file_${file_index}.jpg"

    if [ -f "$thumb_path" ]; then
        # Try different methods to display thumbnail
        if command -v w3m >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
            # Display inline in terminal (if supported)
            echo "      🖼️  Thumbnail preview:"
            w3m -o imgdisplay=1 -dump "$thumb_path" 2>/dev/null || echo "      (thumbnail available but cannot display in terminal)"
        else
            echo "      🖼️  Thumbnail: $thumb_path"
        fi
    else
        echo "      🖼️  No thumbnail available"
    fi
}

# Function to open image viewer
open_image_viewer() {
    local filepath="$1"

    if [ ! -f "$filepath" ]; then
        echo "❌ File not found: $filepath"
        return
    fi

    # Try different viewers in order of preference
    if command -v feh >/dev/null 2>&1; then
        feh "$filepath" 2>/dev/null &
        echo "🖼️  Opened in feh (PID: $!)"
    elif command -v sxiv >/dev/null 2>&1; then
        sxiv "$filepath" 2>/dev/null &
        echo "🖼️  Opened in sxiv (PID: $!)"
    elif command -v eog >/dev/null 2>&1; then
        eog "$filepath" 2>/dev/null &
        echo "🖼️  Opened in Eye of GNOME (PID: $!)"
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$filepath" 2>/dev/null &
        echo "🖼️  Opened with default viewer (PID: $!)"
    else
        echo "❌ No image viewer found. Install: sudo apt install feh sxiv"
    fi
}

# Function to compare multiple files side-by-side
compare_files_sidebyside() {
    local files=("$@")

    if [ ${#files[@]} -eq 0 ]; then
        echo "❌ No files to compare"
        return
    fi

    # Check that files exist
    local valid_files=()
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            valid_files+=("$file")
        fi
    done

    if [ ${#valid_files[@]} -eq 0 ]; then
        echo "❌ No valid files to compare"
        return
    fi

    echo "🔍 Comparing ${#valid_files[@]} files side-by-side..."

    # Try different comparison methods
    if command -v feh >/dev/null 2>&1; then
        # Open all files in feh (tabbed view)
        feh "${valid_files[@]}" 2>/dev/null &
        echo "🖼️  Opened ${#valid_files[@]} files in feh for comparison (PID: $!)"
    elif command -v sxiv >/dev/null 2>&1; then
        # Open all files in sxiv
        sxiv "${valid_files[@]}" 2>/dev/null &
        echo "🖼️  Opened ${#valid_files[@]} files in sxiv for comparison (PID: $!)"
    else
        echo "❌ No suitable viewer for side-by-side comparison"
        echo "Install feh or sxiv: sudo apt install feh sxiv"
    fi
}

# Function to show detailed EXIF information
show_detailed_exif() {
    local filepath="$1"

    if [ ! -f "$filepath" ]; then
        echo "❌ File not found: $filepath"
        return
    fi

    if command -v exiftool >/dev/null 2>&1; then
        echo ""
        echo "=== 📷 DETAILED EXIF DATA ==="
        echo "File: $filepath"
        echo ""

        # Show key EXIF data
        local exif_output=$(exiftool "$filepath" 2>/dev/null)

        if [ -n "$exif_output" ]; then
            # Show most important fields first
            echo "$exif_output" | grep -E "(Camera|Make|Model|Date|Time|GPS|Resolution|ISO|Aperture|Shutter|Focal)" | head -20
            echo ""
            echo "--- Full EXIF data (first 30 lines) ---"
            echo "$exif_output" | head -30
        else
            echo "No EXIF data found in file"
        fi

        echo "=== END EXIF DATA ==="
        echo ""
    else
        echo "❌ exiftool not available. Install: sudo apt install exiftool"
    fi
}

# Function to show thumbnail grid for group
show_group_grid() {
    local group_num="$1"

    local grid_file="$THUMBNAILS_DIR/grids/group_$(printf "%05d" "$group_num")_grid.jpg"

    if [ -f "$grid_file" ]; then
        echo "🖼️  Opening thumbnail grid for group $group_num..."
        open_image_viewer "$grid_file"
    else
        echo "❌ No thumbnail grid available for group $group_num"
    fi
}

# Function to verify a duplicate group interactively
verify_group() {
    local group_file="$1"
    local group_num=$(basename "$group_file" .txt | sed 's/group_0*//')

    echo ""
    echo "=================================================="
    echo "🔍 REVIEWING DUPLICATE GROUP $group_num"
    echo "=================================================="

    # Parse group file to extract file information
    local files=()
    local quality_info=()
    local best_recommended=""

    # Read group file and extract information
    local in_file_section=false
    local current_file=""
    local current_quality=""

    while IFS= read -r line; do
        if [[ "$line" =~ ^\[([0-9]+)\]\ (.+)$ ]]; then
            # New file entry
            current_file="${BASH_REMATCH[2]}"
            files+=("$current_file")
            in_file_section=true
        elif [[ "$line" =~ Quality\ Score:\ ([0-9]+)/100.*RECOMMENDED ]]; then
            # This is the recommended file
            best_recommended="$current_file"
            current_quality="50|unknown|N/A|N/A|N/A|0|0|unknown|unknown" # Default
            quality_info+=("$current_quality")
        elif [[ "$line" =~ Quality\ Score:\ ([0-9]+)/100 ]]; then
            # Extract quality score
            local score="${BASH_REMATCH[1]}"
            current_quality="$score|unknown|N/A|N/A|N/A|0|0|unknown|unknown" # Simplified
            quality_info+=("$current_quality")
        elif [[ "$line" =~ Size:\ ([^|]+)\|.*Date:\ ([^|]+)\|.*Format:\ (.+)$ ]]; then
            # Update quality info with size/date/format
            local size_str="${BASH_REMATCH[1]}"
            local date_str="${BASH_REMATCH[2]}"
            local format_str="${BASH_REMATCH[3]}"

            # Convert size back to bytes (rough estimation)
            local size_bytes=1000000  # Default 1MB
            if [[ "$size_str" =~ ([0-9.]+)([KMGT]?)B ]]; then
                local num="${BASH_REMATCH[1]}"
                local unit="${BASH_REMATCH[2]}"
                case "$unit" in
                    K) size_bytes=$(echo "$num * 1024" | bc 2>/dev/null || echo 1024) ;;
                    M) size_bytes=$(echo "$num * 1048576" | bc 2>/dev/null || echo 1048576) ;;
                    G) size_bytes=$(echo "$num * 1073741824" | bc 2>/dev/null || echo 1073741824) ;;
                    *) size_bytes=$(echo "$num" | cut -d. -f1) ;;
                esac
            fi

            # Update last quality entry
            if [ ${#quality_info[@]} -gt 0 ]; then
                local last_idx=$((${#quality_info[@]} - 1))
                local parts=(${quality_info[$last_idx]//|/ })
                quality_info[$last_idx]="${parts[0]}|${parts[1]}|${parts[2]}|${parts[3]}|${parts[4]}|${parts[5]}|$size_bytes|$date_str|$format_str"
            fi
        fi
    done < "$group_file"

    # Show group summary
    echo "📊 Group Summary: ${#files[@]} identical files found"
    if [ -n "$best_recommended" ]; then
        echo "🎯 Recommended: Keep highest quality version"
    fi
    echo ""

    # Display all files with details
    for i in "${!files[@]}"; do
        local file_index=$((i + 1))
        local file_path="${files[$i]}"
        local file_quality="${quality_info[$i]:-50|unknown|N/A|N/A|N/A|0|0|unknown|unknown}"

        # Highlight recommended file
        if [ "$file_path" = "$best_recommended" ]; then
            echo "🎯 RECOMMENDED CHOICE:"
        fi

        show_file_info "$file_path" "$file_index" "$file_quality"

        # Show thumbnail if available
        show_thumbnail "$file_path" "$group_num" "$file_index"

        echo ""
    done

    # Interactive decision loop
    while true; do
        echo "=================================================="
        echo "🎛️  VERIFICATION OPTIONS:"
        echo "  auto         - Accept quality-based recommendation (keep best, remove others)"
        echo "  k [numbers]  - Keep specific files (e.g., 'k 1 3' keeps files 1 and 3)"
        echo "  r [numbers]  - Remove specific files (e.g., 'r 2 4' removes files 2 and 4)"
        echo "  v [number]   - View file in image viewer (e.g., 'v 1' opens file 1)"
        echo "  c [numbers]  - Compare files side-by-side (e.g., 'c 1 2 3')"
        echo "  i [number]   - Show detailed EXIF info (e.g., 'i 1')"
        echo "  g            - Show thumbnail grid for this group"
        echo "  s            - Skip this group (review later)"
        echo "  q            - Quit verification"
        echo "  h            - Show this help"
        echo ""
        read -p "Your decision: " decision

        case "$decision" in
            auto)
                if [ -n "$best_recommended" ]; then
                    # Find index of recommended file
                    local keep_idx=0
                    for i in "${!files[@]}"; do
                        if [ "${files[$i]}" = "$best_recommended" ]; then
                            keep_idx=$((i + 1))
                            break
                        fi
                    done

                    echo "🤖 AUTO: Keeping file $keep_idx (highest quality)"
                    echo "      Removing other $((${#files[@]} - 1)) files"

                    # Mark all others for removal
                    for i in "${!files[@]}"; do
                        local file_idx=$((i + 1))
                        if [ "$file_idx" -ne "$keep_idx" ]; then
                            echo "REMOVE|${files[$i]}" >> "$DECISIONS_FILE"
                        fi
                    done
                    log "Group $group_num: AUTO - kept file $keep_idx, removed $((${#files[@]} - 1)) files"
                else
                    echo "❌ No clear recommendation available. Please make manual decision."
                    continue
                fi
                break
                ;;
            k\ *)
                # Keep specified files, remove others
                local keep_indices=(${decision#k })
                local valid_keeps=()

                # Validate indices
                for idx in "${keep_indices[@]}"; do
                    if [[ "$idx" =~ ^[0-9]+$ ]] && [ "$idx" -ge 1 ] && [ "$idx" -le "${#files[@]}" ]; then
                        valid_keeps+=("$idx")
                    else
                        echo "❌ Invalid file number: $idx"
                    fi
                done

                if [ ${#valid_keeps[@]} -eq 0 ]; then
                    echo "❌ No valid file numbers specified"
                    continue
                fi

                echo "✅ DECISION: Keep files: ${valid_keeps[*]}"
                echo "           Remove files: $(for i in $(seq 1 ${#files[@]}); do [[ ! " ${valid_keeps[*]} " =~ " $i " ]] && echo -n "$i "; done)"

                # Mark files for removal
                local removed_count=0
                for i in $(seq 1 ${#files[@]}); do
                    if [[ ! " ${valid_keeps[*]} " =~ " $i " ]]; then
                        echo "REMOVE|${files[$((i-1))]}" >> "$DECISIONS_FILE"
                        ((removed_count++))
                    fi
                done

                log "Group $group_num: Manual keep - kept ${#valid_keeps[@]} files, removed $removed_count files"
                break
                ;;
            r\ *)
                # Remove specified files
                local remove_indices=(${decision#r })
                local valid_removes=()

                # Validate indices
                for idx in "${remove_indices[@]}"; do
                    if [[ "$idx" =~ ^[0-9]+$ ]] && [ "$idx" -ge 1 ] && [ "$idx" -le "${#files[@]}" ]; then
                        valid_removes+=("$idx")
                    else
                        echo "❌ Invalid file number: $idx"
                    fi
                done

                if [ ${#valid_removes[@]} -eq 0 ]; then
                    echo "❌ No valid file numbers specified"
                    continue
                fi

                # Check that we're not removing all files
                if [ ${#valid_removes[@]} -eq ${#files[@]} ]; then
                    echo "❌ Cannot remove all files in a duplicate group. Keep at least one."
                    continue
                fi

                echo "✅ DECISION: Remove files: ${valid_removes[*]}"
                echo "           Keep files: $(for i in $(seq 1 ${#files[@]}); do [[ ! " ${valid_removes[*]} " =~ " $i " ]] && echo -n "$i "; done)"

                # Mark specified files for removal
                for idx in "${valid_removes[@]}"; do
                    echo "REMOVE|${files[$((idx-1))]}" >> "$DECISIONS_FILE"
                done

                log "Group $group_num: Manual remove - removed ${#valid_removes[@]} files, kept $((${#files[@]} - ${#valid_removes[@]})) files"
                break
                ;;
            v\ *)
                # View file in image viewer
                local view_idx=${decision#v }
                if [[ "$view_idx" =~ ^[0-9]+$ ]] && [ "$view_idx" -ge 1 ] && [ "$view_idx" -le "${#files[@]}" ]; then
                    echo "🖼️  Opening file $view_idx in image viewer..."
                    open_image_viewer "${files[$((view_idx-1))]}"
                else
                    echo "❌ Invalid file number: $view_idx"
                fi
                ;;
            c\ *)
                # Compare files side-by-side
                local compare_indices=(${decision#c })
                local compare_files=()

                for idx in "${compare_indices[@]}"; do
                    if [[ "$idx" =~ ^[0-9]+$ ]] && [ "$idx" -ge 1 ] && [ "$idx" -le "${#files[@]}" ]; then
                        compare_files+=("${files[$((idx-1))]}")
                    else
                        echo "❌ Invalid file number: $idx"
                    fi
                done

                if [ ${#compare_files[@]} -gt 0 ]; then
                    compare_files_sidebyside "${compare_files[@]}"
                else
                    echo "❌ No valid files to compare"
                fi
                ;;
            i\ *)
                # Show detailed info
                local info_idx=${decision#i }
                if [[ "$info_idx" =~ ^[0-9]+$ ]] && [ "$info_idx" -ge 1 ] && [ "$info_idx" -le "${#files[@]}" ]; then
                    show_detailed_exif "${files[$((info_idx-1))]}"
                else
                    echo "❌ Invalid file number: $info_idx"
                fi
                ;;
            g)
                # Show thumbnail grid
                show_group_grid "$group_num"
                ;;
            s)
                echo "⏭️  SKIPPED group $group_num for later review"
                log "Group $group_num: Skipped for later review"
                break
                ;;
            q)
                echo "🚪 Verification session ended by user"
                log "Verification session ended by user at group $group_num"
                return 1  # Signal to quit
                ;;
            h|help)
                # Help already shown above, just continue
                ;;
            "")
                echo "❌ Please enter a decision (or 'h' for help)"
                ;;
            *)
                echo "❌ Invalid option: '$decision'. Type 'h' for help."
                ;;
        esac
    done

    return 0
}

# Function to save session state
save_session_state() {
    local current_group="$1"
    echo "CURRENT_GROUP=$current_group" > "$SESSION_STATE"
    echo "TIMESTAMP=$(date)" >> "$SESSION_STATE"
    echo "DECISIONS_FILE=$DECISIONS_FILE" >> "$SESSION_STATE"
}

# Function to load session state
load_session_state() {
    if [ -f "$SESSION_STATE" ]; then
        source "$SESSION_STATE"
        echo "📂 Previous session found: $TIMESTAMP"
        echo "    Current group: ${CURRENT_GROUP:-1}"
        echo "    Decisions file: ${DECISIONS_FILE:-$DECISIONS_FILE}"
        echo ""
        read -p "Continue from where you left off? (y/n): " continue_session
        if [[ "$continue_session" =~ ^[Yy] ]]; then
            return ${CURRENT_GROUP:-1}
        fi
    fi
    return 1
}

# Function to generate verification summary
generate_verification_summary() {
    local summary_file="$DUPLICATES_DIR/verification_summary.txt"

    log "Generating verification summary..."

    cat > "$summary_file" << EOL
=== VISUAL VERIFICATION SUMMARY ===
Completed: $(date)
Session log: $LOGFILE

=== REMOVAL DECISIONS ===
EOL

    if [ -f "$DECISIONS_FILE" ]; then
        local total_removals=$(grep -c "^REMOVE|" "$DECISIONS_FILE" 2>/dev/null || echo 0)
        echo "Total files marked for removal: $total_removals" >> "$summary_file"
        echo "" >> "$summary_file"

        # Calculate space savings
        local total_space=0
        while IFS='|' read -r action filepath; do
            if [ "$action" = "REMOVE" ] && [ -f "$filepath" ]; then
                local file_size=$(stat -c%s "$filepath" 2>/dev/null || echo 0)
                total_space=$((total_space + file_size))
            fi
        done < "$DECISIONS_FILE"

        local space_human=$(numfmt --to=iec "$total_space" 2>/dev/null || echo "${total_space}B")
        echo "Estimated space to be freed: $space_human" >> "$summary_file"
        echo "" >> "$summary_file"

        # Show sample removals
        echo "Sample files marked for removal:" >> "$summary_file"
        grep "^REMOVE|" "$DECISIONS_FILE" | head -10 | while IFS='|' read -r action filepath; do
            echo "  • $filepath" >> "$summary_file"
        done

        if [ "$total_removals" -gt 10 ]; then
            echo "  ... and $((total_removals - 10)) more files" >> "$summary_file"
        fi
    else
        echo "No removal decisions found" >> "$summary_file"
    fi

    cat >> "$summary_file" << EOL

=== NEXT STEPS ===
1. Review removal decisions: $DECISIONS_FILE
2. Backup decisions file: $BACKUP_DECISIONS (created automatically)
3. Run Phase 3 safe removal script
4. Verify results

=== FILES CREATED ===
• Removal decisions: $DECISIONS_FILE
• Backup decisions: $BACKUP_DECISIONS
• Session state: $SESSION_STATE
• This summary: $summary_file
• Full log: $LOGFILE
EOL

    log "Verification summary created: $summary_file"
}

# Function to backup decisions
backup_decisions() {
    if [ -f "$DECISIONS_FILE" ]; then
        cp "$DECISIONS_FILE" "$BACKUP_DECISIONS"
        log "Decisions backed up to: $BACKUP_DECISIONS"
    fi
}

# Main verification loop
main() {
    log "=== Visual Verification with Photo Previews Started ==="

    # Check if duplicate groups exist
    if [ ! -d "$DUPLICATES_DIR/groups" ] || [ -z "$(ls -A "$DUPLICATES_DIR/groups"/*.txt 2>/dev/null)" ]; then
        log "ERROR: No duplicate groups found. Run analyze_duplicates.sh first."
        exit 1
    fi

    # Check for thumbnail availability
    if [ ! -d "$THUMBNAILS_DIR" ]; then
        log "WARNING: No thumbnails found. Run generate_thumbnails.sh for better visual experience."
    fi

    # Initialize decisions file
    echo "# Visual Verification Removal Decisions - $(date)" > "$DECISIONS_FILE"
    echo "# Format: REMOVE|/path/to/file" >> "$DECISIONS_FILE"
    echo "# Generated by visual_verify.sh" >> "$DECISIONS_FILE"

    # Try to load previous session
    local start_group=1
    if load_session_state; then
        start_group=$?
    fi

    local group_files=("$DUPLICATES_DIR/groups"/group_*.txt)
    local total_groups=${#group_files[@]}
    local current_group_num=1
    local completed_groups=0
    local skipped_groups=0

    echo "=================================================="
    echo "🎯 VISUAL VERIFICATION SESSION"
    echo "=================================================="
    echo "Found $total_groups duplicate groups to review"
    echo "Starting from group: $start_group"
    echo "Decisions will be saved to: $DECISIONS_FILE"
    echo ""
    echo "💡 TIP: Use 'auto' to accept quality-based recommendations quickly"
    echo "💡 TIP: Use 'g' to see thumbnail grids for visual comparison"
    echo "💡 TIP: Use 'c 1 2 3' to compare multiple files side-by-side"
    echo ""

    # Process each group
    for group_file in "${group_files[@]}"; do
        if [ "$current_group_num" -lt "$start_group" ]; then
            ((current_group_num++))
            continue
        fi

        echo "Progress: $current_group_num/$total_groups groups"

        # Save session state
        save_session_state "$current_group_num"

        # Verify the group
        if verify_group "$group_file"; then
            ((completed_groups++))
        else
            # User quit
            break
        fi

        ((current_group_num++))

        # Periodic backup
        if (( current_group_num % 10 == 0 )); then
            backup_decisions
            log "Progress: Completed $completed_groups groups, session saved"
        fi
    done

    # Final backup and summary
    backup_decisions
    generate_verification_summary

    # Cleanup session state if completed
    if [ "$current_group_num" -gt "$total_groups" ]; then
        rm -f "$SESSION_STATE"
        log "Verification session completed successfully"
    fi

    log "=== Visual Verification Complete ==="
    log "Groups processed: $completed_groups/$total_groups"
    log "Decisions saved: $DECISIONS_FILE"
    log "Summary: $DUPLICATES_DIR/verification_summary.txt"

    echo ""
    echo "=================================================="
    echo "✅ VERIFICATION SESSION COMPLETE"
    echo "=================================================="
    echo "Groups reviewed: $completed_groups/$total_groups"

    if [ -f "$DECISIONS_FILE" ]; then
        local total_removals=$(grep -c "^REMOVE|" "$DECISIONS_FILE" 2>/dev/null || echo 0)
        echo "Files marked for removal: $total_removals"
    fi

    echo ""
    echo "📋 Summary report: $DUPLICATES_DIR/verification_summary.txt"
    echo "📁 Removal decisions: $DECISIONS_FILE"
    echo "🔄 Next: Run Phase 3 safe removal script"
    echo ""
}

# Handle script interruption gracefully
trap 'log "Verification interrupted by user"; backup_decisions; exit 130' INT TERM

# Run main function
main "$@"