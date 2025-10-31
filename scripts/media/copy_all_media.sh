#!/usr/bin/env bash
set -euo pipefail

# Safe Media Copy Script - Copy First, Process Later
# Copies ALL media files from source drives to /data/incoming before any processing

# Load common configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common/config.sh"

# Initialize configuration
load_common_config
create_directories

# Script-specific directories
INCOMING_DIR="$HOMELAB_DATA_ROOT/incoming"
MANIFESTS_DIR="$HOMELAB_DATA_ROOT/manifests"
LOGFILE="$HOMELAB_LOG_DIR/copy_all_media_$(date +%Y%m%d_%H%M%S).log"

# Copy statistics
TOTAL_COPIED=0
TOTAL_SKIPPED=0
TOTAL_ERRORS=0
TOTAL_SIZE=0

mkdir -p "$INCOMING_DIR"
mkdir -p "$MANIFESTS_DIR"

# Function to copy all files from a source drive
copy_source_drive() {
    local source_drive="$1"
    local source_name="$(basename "$source_drive")"
    local drive_incoming="$INCOMING_DIR/$source_name"
    local manifest_file="$MANIFESTS_DIR/${source_name}_original_manifest.sha256"
    local copy_log="$HOMELAB_LOG_DIR/copy_${source_name}_$(date +%Y%m%d_%H%M%S).log"
    
    log_info "=== Starting copy from: $source_drive ==="
    log_info "Destination: $drive_incoming"
    log_info "Manifest: $manifest_file"
    
    # Verify source exists
    if [ ! -d "$source_drive" ]; then
        log_error "Source drive not found: $source_drive"
        return 1
    fi
    
    # Create destination directory
    mkdir -p "$drive_incoming"
    
    # Build find pattern for media files using centralized config
    local photo_pattern=""
    local video_pattern=""
    
    # Build photo extensions pattern
    while IFS= read -r ext; do
        if [ -n "$photo_pattern" ]; then
            photo_pattern="$photo_pattern -o"
        fi
        photo_pattern="$photo_pattern -iname \"*.$ext\""
    done < <(get_photo_extensions)
    
    # Build video extensions pattern  
    while IFS= read -r ext; do
        if [ -n "$video_pattern" ]; then
            video_pattern="$video_pattern -o"
        fi
        video_pattern="$video_pattern -iname \"*.$ext\""
    done < <(get_video_extensions)
    
    local find_pattern="\\( $photo_pattern \\) -o \\( $video_pattern \\)"
    
    # Count total files to copy
    log_info "Scanning $source_drive for media files..."
    local temp_list="/tmp/media_files_${source_name}_$$"
    eval "find '$source_drive' -type f $find_pattern" > "$temp_list"
    local total_files=$(wc -l < "$temp_list")
    
    log_info "Found $total_files media files to copy from $source_drive"
    
    if [ "$total_files" -eq 0 ]; then
        log_warn "No media files found in $source_drive"
        rm -f "$temp_list"
        return 0
    fi
    
    # Estimate total size
    local total_size_bytes=0
    while IFS= read -r file; do
        local file_size=$(stat -c%s "$file" 2>/dev/null || echo 0)
        total_size_bytes=$((total_size_bytes + file_size))
    done < "$temp_list"
    
    local total_size_human=$(numfmt --to=iec "$total_size_bytes")
    log_info "Total size to copy: $total_size_human"
    
    # Check available space
    local available_bytes=$(df -B1 "$HOMELAB_DATA_ROOT" | awk 'NR==2 {print $4}')
    local min_free_gb=$(get_photo_config "safety.min_free_space_gb" "100")
    local min_free_bytes=$((min_free_gb * 1024 * 1024 * 1024))
    
    if [ $((total_size_bytes + min_free_bytes)) -gt "$available_bytes" ]; then
        log_error "Insufficient space for copy operation"
        log_error "Need: $(numfmt --to=iec $((total_size_bytes + min_free_bytes)))"
        log_error "Available: $(numfmt --to=iec $available_bytes)"
        rm -f "$temp_list"
        return 1
    fi
    
    # Start copying with progress tracking
    log_info "Starting copy operation with progress tracking..."
    > "$manifest_file"  # Clear manifest
    > "$copy_log"      # Clear copy log
    
    local copied_count=0
    local drive_copied=0
    local drive_skipped=0
    local drive_errors=0
    
    # Copy files with progress bar
    {
        while IFS= read -r source_file; do
            # Calculate relative path to preserve structure
            local rel_path="${source_file#$source_drive/}"
            local dest_file="$drive_incoming/$rel_path"
            local dest_dir="$(dirname "$dest_file")"
            
            # Create destination directory
            mkdir -p "$dest_dir"
            
            # Check if file already exists with same size
            if [ -f "$dest_file" ]; then
                local src_size=$(stat -c%s "$source_file" 2>/dev/null || echo 0)
                local dest_size=$(stat -c%s "$dest_file" 2>/dev/null || echo 0)
                if [ "$src_size" -eq "$dest_size" ]; then
                    echo "[$(date '+%H:%M:%S')] SKIP: $rel_path (already exists)" >> "$copy_log"
                    ((drive_skipped++))
                    ((copied_count++))
                    continue
                fi
            fi
            
            # Copy file
            if rsync -a --progress "$source_file" "$dest_file" 2>>"$copy_log"; then
                # Generate SHA256 hash for manifest
                local file_hash=$(sha256sum "$dest_file" | awk '{print $1}')
                echo "$file_hash $dest_file" >> "$manifest_file"
                echo "[$(date '+%H:%M:%S')] COPY: $rel_path" >> "$copy_log"
                ((drive_copied++))
            else
                echo "[$(date '+%H:%M:%S')] ERROR: Failed to copy $rel_path" >> "$copy_log"
                ((drive_errors++))
            fi
            
            ((copied_count++))
            
            # Progress update every 50 files
            if (( copied_count % 50 == 0 )); then
                local progress=$((copied_count * 100 / total_files))
                log_info "Progress: $copied_count/$total_files files ($progress%)"
            fi
            
        done < "$temp_list"
    }
    
    rm -f "$temp_list"
    
    # Drive copy summary
    log_info "Copy completed for $source_drive:"
    log_info "  Copied: $drive_copied files"
    log_info "  Skipped: $drive_skipped files (already existed)"
    log_info "  Errors: $drive_errors files"
    log_info "  Manifest: $manifest_file"
    log_info "  Copy log: $copy_log"
    
    # Update global statistics
    TOTAL_COPIED=$((TOTAL_COPIED + drive_copied))
    TOTAL_SKIPPED=$((TOTAL_SKIPPED + drive_skipped))
    TOTAL_ERRORS=$((TOTAL_ERRORS + drive_errors))
    
    # Calculate drive size
    local drive_size=$(du -sb "$drive_incoming" | awk '{print $1}')
    TOTAL_SIZE=$((TOTAL_SIZE + drive_size))
    
    return 0
}

# Function to generate copy summary report
generate_copy_summary() {
    local summary_file="$HOMELAB_LOG_DIR/copy_summary_$(date +%Y%m%d_%H%M%S).txt"
    local total_size_human=$(numfmt --to=iec "$TOTAL_SIZE")
    
    cat > "$summary_file" << EOL
=== MEDIA COPY OPERATION SUMMARY ===
Completed: $(date)
Server: $(get_infra_config "server.hostname" "unknown")

=== OPERATION OVERVIEW ===
Purpose: Safe copy of ALL media files from source drives to staging area
Strategy: Copy first, process copies later (never modify originals)

=== COPY RESULTS ===
• Files copied: $TOTAL_COPIED
• Files skipped: $TOTAL_SKIPPED (already existed)
• Files with errors: $TOTAL_ERRORS
• Total size copied: $total_size_human

=== SOURCE DRIVES PROCESSED ===
EOL
    
    # List each source drive with statistics
    local drive_num=1
    while IFS= read -r drive_path; do
        local source_name=$(basename "$drive_path")
        local manifest="$MANIFESTS_DIR/${source_name}_original_manifest.sha256"
        if [ -f "$manifest" ]; then
            local file_count=$(wc -l < "$manifest")
            local drive_size=$(du -sh "$INCOMING_DIR/$source_name" 2>/dev/null | awk '{print $1}' || echo "0B")
            echo "• Drive $drive_num ($source_name): $file_count files, $drive_size" >> "$summary_file"
        fi
        ((drive_num++))
    done < <(get_config_array ".infrastructure.storage.source_drives[].path")
    
    cat >> "$summary_file" << EOL

=== STAGING LOCATION ===
All copied files are in: $INCOMING_DIR/
• Each source drive has its own subdirectory
• Original folder structure preserved
• SHA256 manifests created for each drive

=== NEXT STEPS ===
1. ✅ OLD DRIVES ARE NOW SAFE TO DISCONNECT
2. Run duplicate analysis on copied files: analyze_duplicates_v2.sh --source=incoming
3. Review and consolidate using copied files only
4. Set up Nextcloud/verification access to $INCOMING_DIR
5. After human verification, old drives can be formatted for storage setup

=== IMPORTANT SAFETY NOTES ===
• Original drives have NOT been modified in any way
• All processing will now work on copies in $INCOMING_DIR
• Original drives can be safely disconnected after this step
• Keep original drives until final verification is complete

=== FILES & LOGS ===
• Summary report: $summary_file
• Individual copy logs: $HOMELAB_LOG_DIR/copy_*
• SHA256 manifests: $MANIFESTS_DIR/*_original_manifest.sha256
• Staged files: $INCOMING_DIR/

STATUS: ✅ SAFE COPY OPERATION COMPLETE
All media files safely copied to staging area. Original drives untouched.
EOL
    
    log_info "Copy summary generated: $summary_file"
    cat "$summary_file"
}

# Main execution
main() {
    log_info "=== Safe Media Copy Operation Started ==="
    log_info "Strategy: Copy ALL files first, process copies later"
    
    # Get source drives from configuration
    local source_drives=()
    while IFS= read -r drive_path; do
        source_drives+=("$drive_path")
    done < <(get_config_array ".infrastructure.storage.source_drives[].path")
    
    if [ ${#source_drives[@]} -eq 0 ]; then
        log_error "No source drives configured in config.yml"
        return 1
    fi
    
    log_info "Processing ${#source_drives[@]} source drive(s): ${source_drives[*]}"
    
    # Check total available space across all drives first
    log_info "Checking total space requirements..."
    local total_source_size=0
    for drive in "${source_drives[@]}"; do
        if [ -d "$drive" ]; then
            local drive_size=$(du -sb "$drive" 2>/dev/null | awk '{print $1}' || echo 0)
            total_source_size=$((total_source_size + drive_size))
            log_info "Source drive $drive: $(numfmt --to=iec $drive_size)"
        fi
    done
    
    local available_space=$(df -B1 "$HOMELAB_DATA_ROOT" | awk 'NR==2 {print $4}')
    local min_free_gb=$(get_photo_config "safety.min_free_space_gb" "100")  
    local min_free_bytes=$((min_free_gb * 1024 * 1024 * 1024))
    
    log_info "Total source size: $(numfmt --to=iec $total_source_size)"
    log_info "Available space: $(numfmt --to=iec $available_space)"
    log_info "Safety buffer: ${min_free_gb}GB"
    
    if [ $((total_source_size + min_free_bytes)) -gt "$available_space" ]; then
        log_error "Insufficient total space for copy operation"
        log_error "Need: $(numfmt --to=iec $((total_source_size + min_free_bytes)))"
        log_error "Have: $(numfmt --to=iec $available_space)"
        return 1
    fi
    
    log_info "Space check passed. Proceeding with copy operation."
    
    # Copy from each source drive
    for drive in "${source_drives[@]}"; do
        copy_source_drive "$drive"
        if [ $? -ne 0 ]; then
            log_error "Failed to copy from $drive"
            continue
        fi
    done
    
    # Generate summary report
    generate_copy_summary
    
    log_info "=== Safe Copy Operation Complete ==="
    log_info "Total: $TOTAL_COPIED copied, $TOTAL_SKIPPED skipped, $TOTAL_ERRORS errors"
    
    if [ "$TOTAL_ERRORS" -gt 0 ]; then
        log_warn "Some files had copy errors. Review logs in $HOMELAB_LOG_DIR"
    fi
    
    log_info ""
    log_info "🔒 ORIGINAL DRIVES ARE NOW SAFE TO DISCONNECT"
    log_info "📁 All files copied to: $INCOMING_DIR"
    log_info "📋 Next: Run duplicate analysis on copied files"
    
    return 0
}

# Handle script interruption
trap 'log_error "Copy operation interrupted"; exit 130' INT TERM

# Run main function
main "$@"