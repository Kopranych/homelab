# Homelab Configuration Management

This document explains the centralized configuration system for the homelab project.

## Overview

The homelab uses a hierarchical configuration system that allows for:
- **Centralized configuration** in `config.yml`
- **Environment-specific overrides** (development/production)
- **Local customization** via `config.local.yml`
- **Script integration** via common configuration library

## Configuration Files

### Main Configuration
- **`config.yml`** - Main configuration file with all default settings
- **`config.local.yml`** - Local overrides (not tracked in git)
- **`environments/{dev,prod}/config.yml`** - Environment-specific settings

### Usage Examples
```bash
# View current configuration
./scripts/common/config.sh

# Run in development mode
ENVIRONMENT=development ansible-playbook photo-consolidation.yml

# Override specific settings
ansible-playbook photo-consolidation.yml -e "dry_run=false"
```

## Configuration Structure

The configuration is organized into logical sections:

### Infrastructure
```yaml
infrastructure:
  server:           # Server details (hostname, network, hardware)
  storage:          # Storage configuration (partitions, drives)
```

### Photo Consolidation
```yaml
photo_consolidation:
  process:          # Process control (dry_run, parallel_jobs)
  quality:          # Quality analysis settings
  safety:           # Safety thresholds and checks
  extensions:       # File format definitions
```

### Services
```yaml
services:
  core:             # Core infrastructure (Tailscale, proxy, monitoring)
  photo_management: # Photo services (Immich)
  development:      # Development tools (Java, Python)
```

### Network & Security
```yaml
network:            # Network configuration
backup:             # Backup policies  
logging:            # Logging configuration
```

## Configuration Priority

Settings are loaded in this order (last wins):

1. **Main config** (`config.yml`) - Base configuration
2. **Environment config** (`environments/{env}/config.yml`) - Environment overrides  
3. **Local config** (`config.local.yml`) - Personal customization
4. **Command line** (`-e key=value`) - Runtime overrides

## Getting Started

### 1. Initial Setup
```bash
# Copy the example local config
cp config.local.yml.example config.local.yml

# Edit with your specific settings
nano config.local.yml
```

### 2. Validate Configuration
```bash
# Check configuration is valid
./scripts/common/config.sh

# Show current merged configuration
ENVIRONMENT=production ./scripts/common/config.sh
```

### 3. Customize for Your Setup

Edit `config.local.yml` with your specific:
- Server hostname and IP addresses
- Source drive paths and sizes
- CPU cores and memory
- Tailscale configuration
- Service preferences

## Script Integration

Scripts can use the common configuration library:

```bash
#!/usr/bin/env bash
# Source the common config
source "$(dirname "$0")/common/config.sh"

# Load configuration
load_common_config
create_directories

# Use configuration variables
echo "Data root: $HOMELAB_DATA_ROOT"
echo "Target directory: $PHOTO_TARGET_DIR"
echo "Parallel jobs: $PHOTO_PARALLEL_JOBS"

# Get specific config values
quality_threshold=$(get_photo_config "quality.format_scores.raw_files" "90")
```

## Ansible Integration

Ansible playbooks automatically load configuration:

```yaml
# Configuration is available as variables
- name: Create directories
  file:
    path: "{{ homelab_data_root }}/photos"
    state: directory
    
- name: Use photo consolidation settings  
  debug:
    msg: "Dry run mode: {{ photo_consolidation.process.dry_run }}"
```

## Environment Management

### Development Environment
```bash
# Use development settings
ENVIRONMENT=development ansible-playbook photo-consolidation.yml

# Development features:
# - Always dry_run: true
# - Fewer parallel jobs
# - Debug logging
# - Test data directories
```

### Production Environment  
```bash
# Use production settings (default)
ansible-playbook photo-consolidation.yml

# Production features:
# - Full CPU utilization
# - Comprehensive backups
# - Monitoring enabled
# - Strict safety checks
```

## Security Notes

### Sensitive Information
- **Never commit** `config.local.yml` to git
- Use **Ansible Vault** for passwords/keys in production:
  ```bash
  ansible-vault create secrets.yml
  ansible-vault edit secrets.yml
  ```

### Git Configuration
The `.gitignore` includes:
```
config.local.yml
secrets.yml
environments/*/secrets.yml
```

## Configuration Reference

### Common Photo Consolidation Settings

```yaml
photo_consolidation:
  process:
    dry_run: true                    # Safe testing mode
    preserve_structure: true         # Keep folder structure
    parallel_jobs: 4                 # CPU utilization
    
  safety:
    max_duplicate_percentage: 80     # Alert threshold
    min_free_space_gb: 100          # Space safety buffer
    backup_before_removal: true      # Always backup
    
  quality:
    format_scores:
      raw_files: 90                  # Highest priority
      high_res_jpg: 75               # Large JPEG files
      videos_4k: 85                  # 4K videos
```

### Common Infrastructure Settings

```yaml
infrastructure:
  server:
    hostname: "homelab-server"
    network:
      local_ip: "192.168.1.100"
      tailscale_ip: "100.x.x.x"
      
  storage:
    data_root: "/data"
    source_drives:
      - path: "/media/sdb1"
        label: "old-ssd-1"
        size: "512GB"
```

## Troubleshooting

### Common Issues

**Configuration not loading:**
```bash
# Check file syntax
yq eval . config.yml

# Validate configuration  
./scripts/common/config.sh
```

**Missing yq tool:**
```bash
# Install yq for YAML processing
sudo apt install yq
```

**Permission issues:**
```bash
# Check file permissions
ls -la config*.yml
chmod 644 config*.yml
```

### Debug Configuration
```bash
# Show all configuration sources
HOMELAB_LOG_LEVEL=DEBUG ./scripts/common/config.sh

# Test specific environment
ENVIRONMENT=development HOMELAB_LOG_LEVEL=DEBUG ./scripts/common/config.sh
```

## Migration from Old Scripts

The centralized configuration replaces hardcoded values in scripts:

**Before:**
```bash
MANIFEST_DIR="/home/$USER/manifests"
TARGET_DIR="/data/photos"  
PARALLEL_JOBS=4
```

**After:**
```bash
source "$(dirname "$0")/common/config.sh"
load_common_config
# Now use: $HOMELAB_DATA_ROOT, $PHOTO_TARGET_DIR, $PHOTO_PARALLEL_JOBS
```

This provides consistency across all scripts and playbooks while maintaining flexibility for different environments and personal preferences.