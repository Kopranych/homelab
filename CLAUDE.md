# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a homelab infrastructure project for setting up a mini PC home server. The repository contains configuration files, scripts, and documentation for:

- Family photo storage and management with intelligent deduplication
- Development project hosting  
- Personal services deployment
- Secure internet access via Tailscale VPN

## Repository Structure

### Core Directories

- **`/docs/`** - Step-by-step setup guides and documentation
  - Hardware setup, OS installation, network configuration
  - Photo consolidation multi-phase guides
  - Architecture and runbook documentation

- **`/scripts/media/`** - Photo/media processing and deduplication tools
  - `discover_media.sh` - Discovers and catalogs media files with SHA256 hashing
  - `quality_analyzer.sh` - Analyzes photo quality metrics for intelligent duplicate selection
  - `analyze_duplicates.sh` - Creates duplicate groups ranked by quality
  - `visual_verify.sh` - Visual verification tools for duplicate review
  - `safe_remove.sh` - Safe duplicate removal after verification

- **`/infra/`** - Infrastructure as Code
  - `ansible/` - Ansible playbooks, roles, and inventory for system configuration
  - `bootstrap/` - Initial system setup scripts

- **`/apps/`** - Application configurations
  - Service-specific Docker configurations and settings
  - Monitoring, reverse proxy, and core service setups

- **`/configs/`** - System and service configuration files
- **`/environments/`** - Environment-specific configurations (dev/prod)
- **`/secrets/`** - Encrypted secrets and sensitive configurations

## Key Architecture

### Photo Consolidation System
The photo consolidation process uses a multi-phase approach:

1. **Phase 1**: Discovery and manifest creation with SHA256 hashing
2. **Phase 2**: Quality-based duplicate analysis and grouping  
3. **Phase 3**: Safe removal after verification

Scripts use quality scoring based on:
- File format (RAW > high-quality JPEG > compressed formats)
- Resolution and file size
- EXIF metadata completeness
- Folder context (organized vs random locations)

### Infrastructure Management
- Ansible-based configuration management
- Environment separation (dev/prod)
- Tailscale for secure remote access
- Docker-based service deployment

## Common Commands

### Photo Consolidation
```bash
# Discover media files from source drives
./scripts/media/discover_media.sh /media/source1 /media/source2

# Analyze photo quality (run before duplicate analysis)
./scripts/media/quality_analyzer.sh

# Find and rank duplicates by quality
./scripts/media/analyze_duplicates.sh

# Visual verification of duplicates
./scripts/media/visual_verify.sh

# Safe removal of verified duplicates  
./scripts/media/safe_remove.sh
```

### Development Workflow
No traditional build/test commands as this is primarily an infrastructure repository with shell scripts and configuration files.

To validate scripts:
```bash
# Check shell script syntax
bash -n script_name.sh

# Run with dry-run where supported
./script_name.sh --dry-run
```

## Working with Scripts

### Media Processing Scripts
- All scripts use `set -euo pipefail` for safety
- Comprehensive logging with timestamps to `/data/logs/`
- Progress indicators for long-running operations
- Support for `--help` and configuration options
- Use `/data/` as primary working directory on target system

### Key Script Features
- **Parallel processing**: Uses `parallel` and `xargs -P` for performance
- **Progress tracking**: Uses `pv` for visual progress on large operations  
- **Quality intelligence**: Advanced scoring system for media files
- **Safety mechanisms**: Dry-run modes, verification steps, detailed logging

## Environment Context

### Target System
- Mini PC with Ubuntu Server 22.04 LTS
- Optimized partition layout with dedicated `/data` partition
- Multiple source drives for photo consolidation
- Tailscale VPN for secure remote access

### Required Tools
Scripts depend on these system tools:
```bash
sudo apt install -y fdupes rdfind exiftool imagemagick ffmpeg tree pv parallel jq sqlite3
```

## File Paths and Conventions

### Standard Locations
- Scripts: `/home/$USER/scripts/` or project `/scripts/` directory
- Manifests: `/home/$USER/manifests/` 
- Working data: `/data/` with subdirectories (`/data/logs/`, `/data/duplicates/`, etc.)
- Quality analysis: `/data/quality/`

### Naming Conventions
- Scripts use underscores: `discover_media.sh`
- Log files include timestamps: `discovery_20241201_143022.log`
- Manifest files: `source1_manifest.sha256`
- Quality cache: `quality_scores.txt`

## Important Notes

- This is an infrastructure project focused on system setup and media management
- Scripts are designed for Ubuntu Server environment with specific partition layout
- Photo consolidation handles millions of files across complex directory structures
- All operations include comprehensive logging and verification steps
- No traditional CI/CD - changes are deployed manually via Ansible or direct script execution