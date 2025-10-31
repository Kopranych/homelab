#!/usr/bin/env bash
# Common Configuration Library for Homelab Scripts
# Provides centralized configuration loading and validation

set -euo pipefail

# Configuration file locations
HOMELAB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MAIN_CONFIG="${HOMELAB_ROOT}/config.yml"
LOCAL_CONFIG="${HOMELAB_ROOT}/config.local.yml"
ENV_CONFIG="${HOMELAB_ROOT}/environments/${ENVIRONMENT:-production}/config.yml"

# Logging configuration
LOG_LEVEL="${HOMELAB_LOG_LEVEL:-INFO}"
LOG_DATE_FORMAT="+%Y-%m-%d %H:%M:%S"

# Function to log messages with levels
log() {
    local level="$1"
    shift
    echo "[$(date "$LOG_DATE_FORMAT")] [$level] $*" >&2
}

log_debug() { [[ "$LOG_LEVEL" =~ (DEBUG) ]] && log "DEBUG" "$@"; }
log_info() { [[ "$LOG_LEVEL" =~ (DEBUG|INFO) ]] && log "INFO" "$@"; }
log_warn() { log "WARN" "$@"; }
log_error() { log "ERROR" "$@"; }

# Function to check if required tools are available
check_required_tools() {
    local missing_tools=()
    
    # Check for yq (YAML processor)
    if ! command -v yq >/dev/null 2>&1; then
        missing_tools+=("yq")
    fi
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Install with: sudo apt install ${missing_tools[*]}"
        return 1
    fi
}

# Function to load configuration value
get_config() {
    local key="$1"
    local default="${2:-}"
    local config_files=()
    
    # Build list of config files to check (last one wins)
    [ -f "$MAIN_CONFIG" ] && config_files+=("$MAIN_CONFIG")
    [ -f "$ENV_CONFIG" ] && config_files+=("$ENV_CONFIG") 
    [ -f "$LOCAL_CONFIG" ] && config_files+=("$LOCAL_CONFIG")
    
    if [ ${#config_files[@]} -eq 0 ]; then
        log_error "No configuration files found"
        return 1
    fi
    
    # Try to get value from config files
    for config_file in "${config_files[@]}"; do
        if value=$(yq eval "$key" "$config_file" 2>/dev/null); then
            if [ "$value" != "null" ]; then
                echo "$value"
                return 0
            fi
        fi
    done
    
    # Return default if provided
    if [ -n "$default" ]; then
        echo "$default"
        return 0
    fi
    
    log_error "Configuration key '$key' not found and no default provided"
    return 1
}

# Function to get array configuration values
get_config_array() {
    local key="$1"
    local config_files=()
    
    # Build list of config files
    [ -f "$MAIN_CONFIG" ] && config_files+=("$MAIN_CONFIG")
    [ -f "$ENV_CONFIG" ] && config_files+=("$ENV_CONFIG")
    [ -f "$LOCAL_CONFIG" ] && config_files+=("$LOCAL_CONFIG")
    
    # Get array values
    for config_file in "${config_files[@]}"; do
        if yq eval "$key | length" "$config_file" >/dev/null 2>&1; then
            yq eval "$key[]" "$config_file" 2>/dev/null
            return 0
        fi
    done
    
    log_error "Configuration array '$key' not found"
    return 1
}

# Function to validate configuration
validate_config() {
    log_info "Validating homelab configuration..."
    
    # Check required configuration keys
    local required_keys=(
        ".infrastructure.server.hostname"
        ".infrastructure.storage.data_root"
        ".photo_consolidation.extensions.photos"
        ".photo_consolidation.extensions.videos"
    )
    
    for key in "${required_keys[@]}"; do
        if ! get_config "$key" >/dev/null; then
            log_error "Required configuration missing: $key"
            return 1
        fi
    done
    
    # Check if data directory exists
    local data_root
    data_root=$(get_config ".infrastructure.storage.data_root")
    if [ ! -d "$data_root" ]; then
        log_warn "Data directory does not exist: $data_root"
    fi
    
    log_info "Configuration validation completed"
    return 0
}

# Function to get photo consolidation specific config
get_photo_config() {
    local key="$1"
    local default="${2:-}"
    get_config ".photo_consolidation.$key" "$default"
}

# Function to get infrastructure config  
get_infra_config() {
    local key="$1"
    local default="${2:-}"
    get_config ".infrastructure.$key" "$default"
}

# Function to get service config
get_service_config() {
    local service="$1"
    local key="$2"
    local default="${3:-}"
    get_config ".services.$service.$key" "$default"
}

# Function to load all common variables
load_common_config() {
    log_debug "Loading common configuration..."
    
    # Infrastructure
    export HOMELAB_HOSTNAME=$(get_infra_config "server.hostname" "homelab-server")
    export HOMELAB_DATA_ROOT=$(get_infra_config "storage.data_root" "/data")
    export HOMELAB_CPU_CORES=$(get_infra_config "server.hardware.cpu_cores" "$(nproc)")
    
    # Photo consolidation
    export PHOTO_TARGET_DIR=$(get_photo_config "consolidation.target_directory" "$HOMELAB_DATA_ROOT/photos/consolidated")
    export PHOTO_BACKUP_DIR=$(get_photo_config "consolidation.backup_directory" "$HOMELAB_DATA_ROOT/backup/photos")
    export PHOTO_DRY_RUN=$(get_photo_config "process.dry_run" "true")
    export PHOTO_PARALLEL_JOBS=$(get_photo_config "process.parallel_jobs" "$HOMELAB_CPU_CORES")
    export PHOTO_PRESERVE_STRUCTURE=$(get_photo_config "process.preserve_structure" "true")
    
    # Logging
    export HOMELAB_LOG_DIR=$(get_config ".logging.paths.applications" "$HOMELAB_DATA_ROOT/logs")
    export HOMELAB_LOG_LEVEL=$(get_config ".logging.default_level" "INFO")
    
    # Safety settings
    export PHOTO_MAX_DUPLICATE_PCT=$(get_photo_config "safety.max_duplicate_percentage" "80")
    export PHOTO_MIN_FREE_SPACE_GB=$(get_photo_config "safety.min_free_space_gb" "100")
    export PHOTO_BACKUP_BEFORE_REMOVAL=$(get_photo_config "safety.backup_before_removal" "true")
    
    log_debug "Common configuration loaded"
}

# Function to create required directories
create_directories() {
    log_info "Creating required directories..."
    
    local dirs=(
        "$HOMELAB_DATA_ROOT"
        "$HOMELAB_LOG_DIR"
        "$PHOTO_TARGET_DIR"
        "$PHOTO_BACKUP_DIR"
        "$HOMELAB_DATA_ROOT/manifests"
        "$HOMELAB_DATA_ROOT/duplicates"
        "$HOMELAB_DATA_ROOT/staging"
    )
    
    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            if mkdir -p "$dir" 2>/dev/null; then
                log_debug "Created directory: $dir"
            else
                log_warn "Failed to create directory: $dir"
            fi
        fi
    done
}

# Function to get file extensions as bash array
get_photo_extensions() {
    get_config_array ".photo_consolidation.extensions.photos"
}

get_video_extensions() {
    get_config_array ".photo_consolidation.extensions.videos"
}

# Function to build find command pattern for media files
get_media_find_pattern() {
    local photo_exts video_exts pattern
    
    photo_exts=$(get_photo_extensions | tr '\n' ',' | sed 's/,$//')
    video_exts=$(get_video_extensions | tr '\n' ',' | sed 's/,$//')
    
    # Build pattern: -iname "*.ext1" -o -iname "*.ext2" ...
    pattern=""
    IFS=',' read -ra EXTS <<< "$photo_exts,$video_exts"
    for ext in "${EXTS[@]}"; do
        if [ -n "$pattern" ]; then
            pattern="$pattern -o"
        fi
        pattern="$pattern -iname \"*.$ext\""
    done
    
    echo "\\( $pattern \\)"
}

# Function to show current configuration summary
show_config_summary() {
    echo "=== HOMELAB CONFIGURATION SUMMARY ==="
    echo "Hostname: $(get_infra_config 'server.hostname')"
    echo "Data Root: $(get_infra_config 'storage.data_root')"
    echo "Environment: ${ENVIRONMENT:-production}"
    echo "Log Level: $(get_config '.logging.default_level')"
    echo ""
    echo "Photo Consolidation:"
    echo "  Target: $(get_photo_config 'consolidation.target_directory')"
    echo "  Dry Run: $(get_photo_config 'process.dry_run')"
    echo "  Parallel Jobs: $(get_photo_config 'process.parallel_jobs')"
    echo "  Preserve Structure: $(get_photo_config 'process.preserve_structure')"
    echo ""
    echo "Source Drives:"
    get_config_array ".infrastructure.storage.source_drives[].path" | sed 's/^/  - /'
    echo "=================================="
}

# Initialize if script is sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Script is being run directly - show config
    check_required_tools
    validate_config
    load_common_config
    create_directories
    show_config_summary
else
    # Script is being sourced - just check tools
    check_required_tools
fi