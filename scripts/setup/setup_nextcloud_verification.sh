#!/usr/bin/env bash
set -euo pipefail

# Nextcloud Setup for Photo Verification
# Sets up Nextcloud with access to /data/incoming for human verification

# Load common configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common/config.sh"

# Initialize configuration
load_common_config
create_directories

# Nextcloud configuration
NEXTCLOUD_DIR="/opt/nextcloud"
NEXTCLOUD_DATA_DIR="/data/nextcloud"
INCOMING_DIR="$HOMELAB_DATA_ROOT/incoming"
VERIFICATION_DIR="$NEXTCLOUD_DATA_DIR/verification"
LOGFILE="$HOMELAB_LOG_DIR/nextcloud_setup_$(date +%Y%m%d_%H%M%S).log"

# Function to create Nextcloud docker-compose configuration
create_nextcloud_compose() {
    local compose_dir="$HOMELAB_DATA_ROOT/../apps/nextcloud"
    local compose_file="$compose_dir/docker-compose.yml"
    
    log_info "Creating Nextcloud Docker Compose configuration..."
    
    mkdir -p "$compose_dir"
    
    cat > "$compose_file" << 'EOL'
version: '3.8'

services:
  nextcloud-db:
    image: postgres:15-alpine
    restart: always
    environment:
      - POSTGRES_DB=nextcloud
      - POSTGRES_USER=nextcloud
      - POSTGRES_PASSWORD=${NEXTCLOUD_DB_PASSWORD:-secure_db_password}
    volumes:
      - nextcloud_db:/var/lib/postgresql/data
    networks:
      - nextcloud-network

  nextcloud-redis:
    image: redis:7-alpine
    restart: always
    networks:
      - nextcloud-network

  nextcloud:
    image: nextcloud:28-apache
    restart: always
    ports:
      - "8080:80"
    environment:
      - POSTGRES_HOST=nextcloud-db
      - POSTGRES_DB=nextcloud
      - POSTGRES_USER=nextcloud
      - POSTGRES_PASSWORD=${NEXTCLOUD_DB_PASSWORD:-secure_db_password}
      - REDIS_HOST=nextcloud-redis
      - NEXTCLOUD_ADMIN_USER=${NEXTCLOUD_ADMIN_USER:-admin}
      - NEXTCLOUD_ADMIN_PASSWORD=${NEXTCLOUD_ADMIN_PASSWORD:-admin_password}
      - NEXTCLOUD_TRUSTED_DOMAINS=${NEXTCLOUD_TRUSTED_DOMAINS:-localhost 127.0.0.1}
    volumes:
      - nextcloud_data:/var/www/html
      - /data/nextcloud:/var/www/html/data
      - /data/incoming:/var/www/html/data/verification/incoming:ro
      - /data/duplicates:/var/www/html/data/verification/duplicates:ro
    depends_on:
      - nextcloud-db
      - nextcloud-redis
    networks:
      - nextcloud-network

volumes:
  nextcloud_db:
  nextcloud_data:

networks:
  nextcloud-network:
    driver: bridge
EOL

    # Create environment file
    cat > "$compose_dir/.env" << EOL
# Nextcloud Environment Configuration
NEXTCLOUD_DB_PASSWORD=secure_nextcloud_db_$(openssl rand -hex 16)
NEXTCLOUD_ADMIN_USER=admin
NEXTCLOUD_ADMIN_PASSWORD=photo_admin_$(openssl rand -hex 8)
NEXTCLOUD_TRUSTED_DOMAINS=localhost,127.0.0.1,$(hostname -I | awk '{print $1}')
EOL

    log_info "Nextcloud configuration created: $compose_file"
    log_info "Environment file: $compose_dir/.env"
    
    return 0
}

# Function to setup verification directory structure
setup_verification_structure() {
    log_info "Setting up verification directory structure..."
    
    # Create Nextcloud data directory structure
    mkdir -p "$NEXTCLOUD_DATA_DIR"/{verification,users}
    
    # Create verification subdirectories
    mkdir -p "$VERIFICATION_DIR"/{incoming,duplicates,reports,consolidated}
    
    # Set proper permissions
    chown -R www-data:www-data "$NEXTCLOUD_DATA_DIR" 2>/dev/null || true
    
    # Create symbolic links for easy access (if not using volume mounts)
    if [ ! -L "$VERIFICATION_DIR/incoming" ]; then
        ln -sf "$INCOMING_DIR" "$VERIFICATION_DIR/incoming_link"
    fi
    
    if [ ! -L "$VERIFICATION_DIR/duplicates" ]; then  
        ln -sf "$HOMELAB_DATA_ROOT/duplicates" "$VERIFICATION_DIR/duplicates_link"
    fi
    
    log_info "Verification structure created in: $VERIFICATION_DIR"
    
    return 0
}

# Function to create verification guide
create_verification_guide() {
    local guide_file="$VERIFICATION_DIR/VERIFICATION_GUIDE.md"
    
    log_info "Creating photo verification guide..."
    
    cat > "$guide_file" << EOL
# Photo Verification Guide

Welcome to the photo consolidation verification interface!

## What You're Seeing

### 📁 Incoming Folder
- **Location**: \`incoming/\`
- **Contents**: All photos and videos copied from your old drives
- **Status**: These are COPIES - your original drives are safe
- **Structure**: Organized by source drive (drive1/, drive2/, etc.)

### 🔍 Duplicates Folder  
- **Location**: \`duplicates/\`
- **Contents**: Analysis results showing duplicate groups
- **Files**: 
  - \`reports/copied_files_analysis.txt\` - Summary of duplicate analysis
  - \`groups/group_XXXXX.txt\` - Individual duplicate group details

## How to Verify

### 1. Review Duplicate Analysis
1. Open \`duplicates/reports/copied_files_analysis.txt\`
2. Check the summary statistics
3. Note the space savings potential

### 2. Spot-Check Duplicate Groups
1. Open some files in \`duplicates/groups/\`
2. Each group shows files ranked by quality
3. The first file (marked "KEEP") will be preserved
4. Other files (marked "REMOVE") will be deleted

### 3. Visual Verification
1. Browse through \`incoming/\` folders
2. Look at photos to confirm they copied correctly
3. Check that folder structure makes sense
4. Verify important photos are present

### 4. Quality Check Examples
Look for these patterns in duplicate groups:
- ✅ RAW files ranked higher than JPEG
- ✅ Large/high-resolution files ranked higher
- ✅ Files in organized folders (2023/, Photos/) ranked higher
- ✅ Files from backup/old folders ranked lower

## What Happens Next

### After Your Verification
1. ✅ **Approve**: Run final consolidation to remove duplicates
2. 🔄 **Adjust**: Modify quality scoring if needed
3. ❌ **Abort**: Return to original drives if issues found

### Safety Features
- 🔒 **Original drives untouched**: Your source drives are completely safe
- 💾 **Working on copies**: All operations work on copied files only
- 🔙 **Rollback possible**: Can start over anytime
- 📋 **Detailed logs**: Every operation is logged

## Quick Verification Checklist

- [ ] Summary report looks reasonable
- [ ] Important family photos are present
- [ ] Duplicate groups make sense (RAW > JPEG, etc.)
- [ ] Folder structure is preserved
- [ ] No obvious missing photos/videos
- [ ] Quality rankings look correct

## Need Help?

- **Duplicate groups**: Each group shows why files were ranked
- **Missing photos**: Check other source drive folders
- **Quality questions**: Review quality scoring in config
- **Technical issues**: Check logs in \`/data/logs/\`

## Final Decision

When satisfied with verification:
✅ **Ready to consolidate**: Duplicates will be removed, best versions kept
🔒 **Original drives can be formatted**: After final consolidation success

---
*Generated by Homelab Photo Consolidation System*
*$(date)*
EOL

    log_info "Verification guide created: $guide_file"
    
    return 0
}

# Function to start Nextcloud
start_nextcloud() {
    local compose_dir="$HOMELAB_DATA_ROOT/../apps/nextcloud"
    
    if [ ! -f "$compose_dir/docker-compose.yml" ]; then
        log_error "Nextcloud compose file not found. Run setup first."
        return 1
    fi
    
    log_info "Starting Nextcloud services..."
    
    cd "$compose_dir"
    
    # Pull latest images
    docker-compose pull
    
    # Start services
    docker-compose up -d
    
    log_info "Nextcloud starting up..."
    log_info "This may take a few minutes for initial setup..."
    
    # Wait for Nextcloud to be ready
    local timeout=300  # 5 minutes
    local count=0
    
    while [ $count -lt $timeout ]; do
        if curl -s http://localhost:8080 > /dev/null 2>&1; then
            log_info "Nextcloud is ready!"
            break
        fi
        
        ((count += 10))
        log_info "Waiting for Nextcloud... ($count/${timeout}s)"
        sleep 10
    done
    
    if [ $count -ge $timeout ]; then
        log_warn "Nextcloud startup timeout. Check status manually."
    fi
    
    return 0
}

# Function to display access information
show_access_info() {
    local compose_dir="$HOMELAB_DATA_ROOT/../apps/nextcloud"
    local env_file="$compose_dir/.env"
    
    if [ ! -f "$env_file" ]; then
        log_error "Environment file not found: $env_file"
        return 1
    fi
    
    # Source environment variables
    set -a
    source "$env_file"
    set +a
    
    local server_ip=$(hostname -I | awk '{print $1}')
    
    cat << EOL

====================================================
🌐 NEXTCLOUD VERIFICATION ACCESS
====================================================

🔗 Access URLs:
   Local: http://localhost:8080
   Network: http://$server_ip:8080

🔐 Admin Login:
   Username: $NEXTCLOUD_ADMIN_USER
   Password: $NEXTCLOUD_ADMIN_PASSWORD

📁 Verification Folders (in Nextcloud):
   • Files > verification > incoming (your copied photos)
   • Files > verification > duplicates (analysis results)

📋 Verification Guide:
   • Files > verification > VERIFICATION_GUIDE.md

====================================================
🔍 VERIFICATION STEPS:
====================================================

1. Login to Nextcloud with above credentials
2. Navigate to Files > verification
3. Read VERIFICATION_GUIDE.md for detailed instructions
4. Review incoming/ folder - your copied photos  
5. Check duplicates/reports/ for analysis summary
6. Spot-check some duplicate groups for accuracy
7. When satisfied, return to command line for final consolidation

====================================================
⚠️  SAFETY REMINDERS:
====================================================

🔒 Your original drives are UNTOUCHED and safe
📁 You're reviewing COPIES in /data/incoming
✅ Safe to disconnect original drives anytime
🔄 Can restart process if any issues found

====================================================

Next: After verification, run consolidation script to finalize!

EOL

    return 0
}

# Main execution
main() {
    log_info "=== Nextcloud Verification Setup Started ==="
    
    # Check if Docker is available
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker not found. Please install Docker first."
        return 1
    fi
    
    if ! command -v docker-compose >/dev/null 2>&1; then
        log_error "Docker Compose not found. Please install Docker Compose first."
        return 1
    fi
    
    # Check if incoming directory exists
    if [ ! -d "$INCOMING_DIR" ]; then
        log_error "Incoming directory not found: $INCOMING_DIR"
        log_error "Please run copy_all_media.sh first."
        return 1
    fi
    
    # Setup process
    create_nextcloud_compose
    setup_verification_structure
    create_verification_guide
    start_nextcloud
    
    # Display access information
    show_access_info
    
    log_info "=== Nextcloud Verification Setup Complete ==="
    log_info "Nextcloud is ready for photo verification!"
    
    return 0
}

# Handle interruption
trap 'log_error "Nextcloud setup interrupted"; exit 130' INT TERM

# Run main function
main "$@"