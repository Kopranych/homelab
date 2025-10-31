# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a homelab infrastructure project for setting up a mini PC home server. The core focus is **safe photo consolidation** using a copy-first approach, along with supporting infrastructure for development and personal services.

**Primary Goal**: Safely consolidate family photos from multiple old Windows drives into a clean, deduplicated collection while never modifying original drives.

**Key Features**:
- Safe copy-first photo consolidation with intelligent deduplication
- Automated Nextcloud deployment for photo verification
- Centralized configuration management (YAML-based)
- Ansible automation for infrastructure deployment
- Python CLI and legacy bash scripts for photo processing
- Tailscale VPN for secure remote access

## Architecture Overview

### Configuration System
**Centralized YAML configuration** is the foundation of this project:

- **`config.yml`** - Main configuration with all defaults
- **`config.local.yml`** - Local overrides (gitignored, user-specific)
- **`environments/{development,production}/config.yml`** - Environment overrides
- **Priority**: config.yml → environment config → config.local.yml → CLI args

**Key Principle**: All scripts and playbooks reference the centralized config, not hardcoded values.

See `CONFIG.md` for detailed configuration management documentation.

### Photo Consolidation Workflow
**Copy-First Safety Approach** (never modifies original drives):

1. **Scan** - Discover media files on source drives, create SHA256 manifests
2. **Copy** - Copy all media to `/data/incoming/` preserving structure
3. **Analyze** - Find duplicates using hashes, rank by quality scores
4. **Consolidate** - Keep best quality version of each photo, remove duplicates
5. **Verify** - Human review via Nextcloud web interface

**Quality Scoring System**:
- Format priority: RAW files (90) > High-res JPEG (75) > Standard JPEG (60)
- Folder context: Organized (+10) > Neutral (0) > Backup (-10)
- Size bonuses for larger files
- All configurable via `config.yml`

### Ansible Infrastructure
**Two deployment modes**:
1. **From laptop (via WSL/Linux)** - Remote deployment to homelab server
2. **On server directly** - Local execution for manual operations

**Main Playbooks**:
- `nextcloud.yml` - Complete Nextcloud deployment (Docker + app)
- `photo-consolidation.yml` - Automated photo consolidation workflow
- `deploy-nextcloud.yml` - Nextcloud only (assumes Docker installed)
- `undeploy-nextcloud.yml` - Safe removal with data protection

**Configuration**: Playbooks load settings from `../../config.yml` via `group_vars/all.yml`

### Implementation Layers

**Three implementation approaches** (choose based on needs):

1. **Python CLI** (`scripts/media/consolidate.py`) - **Recommended**
   - Modern, robust, better error handling
   - Progress bars and colored output
   - Modular design with photo_consolidator package
   - Commands: `scan`, `copy`, `analyze`, `consolidate`, `workflow`, `status`

2. **Ansible Playbooks** (`infra/ansible/`) - **For automation**
   - Full orchestration from laptop
   - Complete workflow automation
   - Environment management
   - Safety checks and rollback support

3. **Bash Scripts** (`scripts/media/*.sh`) - **Legacy fallback**
   - Simpler but less reliable
   - Still functional for manual operations
   - Being replaced by Python CLI

## Repository Structure

```
homelab/
├── config.yml                      # Main configuration (SINGLE SOURCE OF TRUTH)
├── config.local.yml.example        # Template for user customization
├── CONFIG.md                       # Configuration system documentation
├── README.md                       # User-facing documentation
├── CLAUDE.md                       # This file
│
├── docs/                           # Step-by-step guides
│   ├── 01-hardware-setup.md
│   ├── 02-os-installation.md
│   ├── 03-basic-config-tailscale.md
│   ├── 04-nextcloud-setup.md
│   ├── 05-photo-consolidation.md  # Main consolidation guide
│   └── 07-storage-setup.md
│
├── scripts/
│   ├── common/
│   │   └── config.sh              # Configuration loader for bash scripts
│   ├── media/
│   │   ├── consolidate.py         # Python CLI (RECOMMENDED)
│   │   ├── photo_consolidator/    # Python package
│   │   ├── requirements.txt       # Python dependencies
│   │   ├── copy_all_media.sh      # Legacy bash: copy phase
│   │   ├── analyze_copied_files.sh # Legacy bash: analyze phase
│   │   └── consolidate_copied_files.sh # Legacy bash: consolidate phase
│   └── setup/
│       └── setup_nextcloud_verification.sh
│
├── infra/ansible/
│   ├── README.md                  # Ansible documentation
│   ├── QUICKSTART.md              # Command reference
│   ├── inventory/homelab          # Server inventory
│   ├── group_vars/all.yml         # Loads from main config.yml
│   ├── nextcloud.yml              # Complete Nextcloud deployment
│   ├── photo-consolidation.yml    # Complete photo workflow
│   ├── deploy-nextcloud.yml       # Nextcloud only
│   ├── undeploy-nextcloud.yml     # Safe removal
│   ├── install-docker.yml         # Docker setup
│   └── requirements.yml           # Ansible collections
│
└── environments/
    ├── development/config.yml     # Dev overrides (dry_run: true)
    └── production/config.yml      # Prod overrides (full resources)
```

## Common Commands

### Photo Consolidation (Python CLI - Recommended)

```bash
# On mini PC: Install dependencies
cd scripts/media
pip3 install -r requirements.txt

# Complete workflow (all phases)
python3 consolidate.py workflow

# Individual phases
python3 consolidate.py scan         # Phase 1: Scan source drives
python3 consolidate.py copy         # Phase 2: Copy files
python3 consolidate.py analyze      # Phase 3: Analyze duplicates
python3 consolidate.py consolidate  # Phase 4: Final consolidation

# Check status
python3 consolidate.py status

# Options
python3 consolidate.py --help
python3 consolidate.py --config /path/to/config.yml
python3 consolidate.py --log-level DEBUG
python3 consolidate.py copy --dry-run    # Override config
```

### Ansible Deployment (From Laptop)

```bash
# Prerequisites: WSL2 on Windows, or Linux/macOS
cd infra/ansible

# Install Ansible collections (first time only)
ansible-galaxy collection install -r requirements.yml

# Test connectivity
ansible -i inventory/homelab homelab -m ping

# Deploy Nextcloud (complete)
ansible-playbook -i inventory/homelab nextcloud.yml

# Deploy Nextcloud without HTTPS
ansible-playbook -i inventory/homelab nextcloud.yml -e "nextcloud_https_enabled=false"

# Check what would change (dry run)
ansible-playbook -i inventory/homelab nextcloud.yml --check --diff

# Deploy only Docker
ansible-playbook -i inventory/homelab install-docker.yml

# Complete photo consolidation workflow
ansible-playbook -i inventory/homelab photo-consolidation.yml

# Undeploy Nextcloud (keep data)
ansible-playbook -i inventory/homelab undeploy-nextcloud.yml

# Undeploy everything including data (DANGEROUS)
ansible-playbook -i inventory/homelab undeploy-nextcloud.yml \
  -e "remove_data=true remove_images=true"
```

### Configuration Management

```bash
# Copy and customize configuration
cp config.local.yml.example config.local.yml
nano config.local.yml

# Validate configuration
./scripts/common/config.sh

# Test with different environment
ENVIRONMENT=development ansible-playbook ...
ENVIRONMENT=production ansible-playbook ...
```

### Legacy Bash Scripts

```bash
# Individual phases (legacy approach)
./scripts/media/copy_all_media.sh
./scripts/media/analyze_copied_files.sh
./scripts/media/consolidate_copied_files.sh

# All support dry-run mode via config.yml
```

## Development Workflow

### Working with Configuration

**When modifying configuration**:
1. Edit `config.yml` for defaults that apply to all users
2. Edit `config.local.yml` for personal/machine-specific settings
3. Edit `environments/*/config.yml` for environment-specific overrides
4. Never commit `config.local.yml` (gitignored)

**When adding new configuration options**:
1. Add to `config.yml` with sensible defaults
2. Update `CONFIG.md` documentation
3. Update affected scripts/playbooks to use new config
4. Test in both development and production environments

### Working with Ansible Playbooks

**File locations**:
- Inventory: `infra/ansible/inventory/homelab`
- Variables: `infra/ansible/group_vars/all.yml` (loads from main config)
- Playbooks: `infra/ansible/*.yml`

**Best practices**:
- Always use `--check --diff` first for safety
- Use tags for selective execution: `--tags docker`, `--skip-tags verify`
- Reference main config.yml: `"{{ (lookup('file', homelab_config_file) | from_yaml).path.to.setting }}"`
- Test in development environment first

### Working with Python Scripts

**Structure**:
- CLI entry point: `scripts/media/consolidate.py`
- Core logic: `scripts/media/photo_consolidator/` package
- Configuration: Loads from `config.yml` via Config class

**Adding new features**:
1. Update `photo_consolidator/` modules
2. Add CLI commands in `consolidate.py`
3. Update configuration if needed
4. Test with `--dry-run` first

**Testing**:
```bash
# Validate Python syntax
python3 -m py_compile consolidate.py

# Test with dry-run
python3 consolidate.py workflow --log-level DEBUG

# Test configuration loading
python3 -c "from photo_consolidator import Config; c = Config(); print(c.config)"
```

### Working with Bash Scripts

**Integration with centralized config**:
```bash
#!/usr/bin/env bash
source "$(dirname "$0")/../common/config.sh"
load_common_config

# Now use variables from config.yml
echo "Data root: $HOMELAB_DATA_ROOT"
echo "Parallel jobs: $PHOTO_PARALLEL_JOBS"
```

**Validation**:
```bash
# Check syntax
bash -n script_name.sh

# Test with shellcheck (if available)
shellcheck script_name.sh
```

## Target Environment

### Mini PC Server
- **OS**: Ubuntu Server 22.04 LTS
- **Partition Layout**:
  - `/` (50GB root)
  - `/home` (20GB)
  - `/data` (911GB) - Primary working directory
  - swap (16GB)
- **Network**: Local LAN + Tailscale VPN
- **Services**: Docker, Nextcloud, photo consolidation tools

### Control Machine (Laptop)
- **OS**: Windows (WSL2), Linux, or macOS
- **Requirements**: Ansible 2.14+, Python 3.8+, SSH access to server
- **Network**: Must reach server via SSH (LAN or Tailscale)

### Required Tools on Server

**System packages**:
```bash
sudo apt install -y exiftool imagemagick ffmpeg tree pv parallel jq yq
```

**Python packages** (for Python CLI):
```bash
pip3 install -r scripts/media/requirements.txt
```

**Docker** (installed via Ansible):
```bash
ansible-playbook -i inventory/homelab install-docker.yml
```

## File Paths and Conventions

### Standard Locations on Server
- **Data root**: `/data/`
- **Docker compose**: `~/docker-compose/nextcloud/`
- **Logs**: `/data/logs/`
- **Manifests**: `/data/manifests/`
- **Incoming photos**: `/data/incoming/`
- **Duplicates analysis**: `/data/duplicates/`
- **Final collection**: `/data/final/`
- **Nextcloud data**: `/data/docker/nextcloud/`

### Naming Conventions
- **Scripts**: `snake_case.sh` or `snake_case.py`
- **Config files**: `kebab-case.yml` or `snake_case.yml`
- **Log files**: `process_YYYYMMDD_HHMMSS.log`
- **Manifests**: `drive_manifest.sha256` or `drive_manifest.json`

### Important Paths
- **Configuration**: `config.yml` (project root)
- **Ansible playbooks**: `infra/ansible/`
- **Python CLI**: `scripts/media/consolidate.py`
- **Documentation**: `docs/` (guides) and `*.md` files (reference)

## Important Notes

### Configuration System
- **Single source of truth**: All settings in `config.yml`
- **Hierarchical loading**: Main → Environment → Local → CLI
- **Never hardcode**: Always reference config, never hardcode paths/settings
- See `CONFIG.md` for comprehensive configuration documentation

### Photo Consolidation
- **Copy-first approach**: Originals never modified during entire process
- **Quality-based**: Intelligent scoring keeps best versions
- **SHA256 verification**: All file integrity verified with hashes
- **Human verification**: Nextcloud web interface for visual review
- **Fully reversible**: Can restart any phase safely

### Ansible Deployment
- **Remote execution**: Run from laptop, deploy to server
- **Idempotent**: Safe to re-run playbooks
- **Check mode**: Always test with `--check --diff` first
- **Centralized config**: Playbooks load from main `config.yml`

### Safety Mechanisms
- **Dry-run by default**: Set `dry_run: false` in config for live operations
- **Space verification**: Checks adequate free space before operations
- **Detailed logging**: Complete audit trail in `/data/logs/`
- **Original backup**: Source drives remain untouched throughout

### Development Environment
- **Use development environment**: `ENVIRONMENT=development` for testing
- **Dry-run mode**: Always enabled in development environment
- **Reduced resources**: Lower parallel jobs in dev environment
- **Production safeguards**: Extra safety checks and backups in production

### Git Practices
- **Gitignored**: `config.local.yml`, `secrets.yml`, environment secrets
- **Committed**: `config.yml`, `config.local.yml.example`, playbooks, scripts
- **Branch**: Development work on feature branches, PR to main
- **Current branch**: `ansible-automation` (active development)