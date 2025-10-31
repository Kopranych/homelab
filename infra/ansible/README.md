# Homelab Ansible Automation

Complete automation for homelab infrastructure deployment and photo consolidation using centralized configuration.

## Available Playbooks

- **Nextcloud Deployment** - Automated Nextcloud deployment with Docker, PostgreSQL, Redis, and Traefik
- **Photo Consolidation** - Safe photo consolidation with duplicate detection and quality analysis

---

# Nextcloud Deployment

Automated deployment of Nextcloud with PostgreSQL, Redis, and Traefik reverse proxy with HTTPS support via Tailscale.

## Prerequisites

### Control Machine Setup

You need Ansible installed on your laptop/workstation to deploy to the homelab server.

**Windows (WSL2 - Recommended)**

Windows doesn't support Ansible natively. Use WSL2 (Windows Subsystem for Linux):

```powershell
# In PowerShell (Administrator)
wsl --install

# Install Ubuntu from Microsoft Store
# Launch Ubuntu and set up user
```

Then in Ubuntu (WSL):
```bash
# Install Ansible
sudo apt update && sudo apt upgrade -y
sudo apt install -y ansible python3-pip

# Navigate to project (Windows drives at /mnt/)
cd /mnt/c/Users/YOUR_USERNAME/PycharmProjects/homelab/infra/ansible

# Install Ansible collections
ansible-galaxy collection install -r requirements.yml
```

**macOS**
```bash
brew install ansible
cd infra/ansible
ansible-galaxy collection install -r requirements.yml
```

**Linux (Ubuntu/Debian)**
```bash
sudo apt install -y ansible python3-pip
cd infra/ansible
ansible-galaxy collection install -r requirements.yml
```

**Verify Installation**
```bash
ansible --version  # Should be 2.14+
ansible-galaxy collection list
```

### Target Server Requirements

- Ubuntu Server 22.04 LTS (recommended)
- SSH access enabled
- Sudo privileges for deployment user
- (Optional) Tailscale installed for HTTPS

## Quick Start

1. **Install Ansible collections**:
   ```bash
   cd infra/ansible
   ansible-galaxy collection install -r requirements.yml
   ```

2. **Configure inventory**:
   ```bash
   # Edit with your server details
   nano inventory/homelab
   ```

3. **Deploy Nextcloud**:
   ```bash
   # Full deployment (Docker + Nextcloud)
   ansible-playbook -i inventory/homelab nextcloud.yml
   ```

## Nextcloud Features

- Automated Docker installation with proper `/data` directory support
- PostgreSQL 15 database (dedicated for Nextcloud)
- Redis 7 cache for performance
- Traefik reverse proxy for HTTPS
- Automatic Tailscale certificate management
- Proper permissions (www-data UID 33)
- Post-installation optimization
- Safe undeployment with data protection

## Nextcloud Usage

**For comprehensive command examples with all options, see [QUICKSTART.md](QUICKSTART.md)**

### Deploy Nextcloud
```bash
# Complete installation
ansible-playbook -i inventory/homelab nextcloud.yml

# Skip Docker if already installed
ansible-playbook -i inventory/homelab nextcloud.yml --skip-tags docker

# Disable HTTPS
ansible-playbook -i inventory/homelab nextcloud.yml -e "nextcloud_https_enabled=false"

# Check mode (dry run - see what would change)
ansible-playbook -i inventory/homelab nextcloud.yml --check --diff

# Verbose output for debugging
ansible-playbook -i inventory/homelab nextcloud.yml -vvv

# Deploy with custom passwords
ansible-playbook -i inventory/homelab nextcloud.yml \
  -e "nextcloud.admin.password=SecurePassword123"
```

### Undeploy Nextcloud
```bash
# Remove containers only (keep data)
ansible-playbook -i inventory/homelab undeploy-nextcloud.yml

# Remove containers and images
ansible-playbook -i inventory/homelab undeploy-nextcloud.yml -e "remove_images=true"

# Remove everything including data (DANGEROUS!)
ansible-playbook -i inventory/homelab undeploy-nextcloud.yml -e "remove_data=true remove_images=true"
```

## Configuration

Edit `group_vars/all.yml` to customize:

```yaml
nextcloud:
  admin:
    password: "your_secure_password"  # Change this!
  database:
    password: "your_db_password"      # Change this!
  redis:
    password: "your_redis_password"   # Change this!
  https:
    enabled: true  # Set to false to disable HTTPS
```

## Troubleshooting

### Docker Permission Errors
```bash
# On target server, after Docker installation
newgrp docker
# Or logout and login again
```

### Nextcloud Data Directory Error
The playbook handles permissions automatically. If you see "Cannot create or write into data directory":
```bash
sudo chown -R 33:33 /data/docker/nextcloud/data
docker compose restart nextcloud-app
```

### HTTPS Certificate Issues
```bash
# Check Tailscale status
tailscale status

# Verify HTTPS is enabled in Tailscale Admin Console
# https://login.tailscale.com/admin/dns

# Check certificates in Traefik
docker exec nextcloud-traefik ls -la /certs/
```

See full documentation in `docs/04-nextcloud-setup.md`

---

# Safe Photo Consolidation

Complete automation for the **copy-first, process-later** photo consolidation approach using centralized configuration.

## Safe Workflow Architecture

**Copy-First Approach:**
- **Phase 1**: Copy all media files from old drives (originals never touched)
- **Phase 2**: Analyze duplicates in copied files only
- **Phase 3**: Human verification via Nextcloud web interface  
- **Phase 4**: Remove duplicates from copied files (originals still safe)
- **Phase 5**: Format original drives for reuse

**Clean Separation:**
- **Ansible**: Orchestration, safety checks, environment management
- **Scripts**: Focused logic using centralized configuration
- **Configuration**: Single source of truth in `../../config.yml`

## Quick Start

1. **Configure your setup**:
   ```bash
   # Copy and customize local configuration (from project root)
   cp config.local.yml.example config.local.yml
   nano config.local.yml
   
   # Edit inventory with your server details
   nano inventory/homelab
   ```

2. **Test connectivity**:
   ```bash
   ansible -i inventory/homelab homelab -m ping
   ```

3. **Run complete safe workflow**:
   ```bash
   # Recommended: Use screen for long-running ansible operations
   screen -S photo-consolidation
   
   # Complete automated safe consolidation
   ansible-playbook -i inventory/homelab photo-consolidation.yml
   
   # Detach: Ctrl+A, then D
   # Reattach: screen -r photo-consolidation
   ```

## What This Achieves

✅ **All unique photos preserved** - SHA256 hash verification ensures no data loss  
✅ **Highest quality versions kept** - Intelligent quality scoring (RAW > high-res JPEG > compressed)  
✅ **Structured organization** - Preserves original folder structure or creates organized layout  
✅ **Storage optimization** - Eliminates duplicates, significant space savings  
✅ **Safe and verifiable** - Multiple safety checks, dry-run mode, detailed logging  
✅ **Photos AND videos** - Processes all common media formats  
✅ **Source drive copying** - Safely copies from source drives to target  
✅ **Read-only operation** - Original drives remain untouched until you decide  

## Process Overview

1. **Prerequisites Check** - Verifies drives, space, tools
2. **Discovery** - Creates SHA256 manifests of all media files
3. **Quality Analysis** - Scores each file for intelligent duplicate selection
4. **Duplicate Detection** - Groups duplicates and ranks by quality
5. **Safe Consolidation** - Copies best version of each file
6. **Verification** - Generates comprehensive report

## Configuration Options

```yaml
# In group_vars/all.yml
dry_run: true                    # Safe testing mode
preserve_structure: true         # Keep folder structure
source_drives: ["/media/sdb1"]   # Your source drives
target_base: "/data"             # Destination location
```

## Safety Features

- **Dry run mode** - Test everything before execution
- **Space verification** - Ensures adequate target space
- **Hash verification** - SHA256 checksums prevent corruption
- **Quality-based selection** - Keeps best version of duplicates
- **Read-only sources** - Original drives never modified
- **Detailed logging** - Complete audit trail
- **Incremental execution** - Can re-run safely if interrupted

## Replacing Current Scripts

This single playbook replaces:
- `discover_media.sh` → Discovery phase
- `quality_analyzer.sh` → Quality analysis phase
- `analyze_duplicates.sh` → Duplicate detection phase  
- `copy_media.sh` → Media copying phase
- `safe_remove.sh` → Smart consolidation phase

## Output Structure

```
/data/
├── logs/           # Detailed execution logs
├── manifests/      # SHA256 hash catalogs
├── duplicates/     # Duplicate analysis results
├── final/          # Consolidated media collection
└── backup/         # Safety backups (if needed)
```

## Troubleshooting

**Connection issues**: Check inventory file and SSH access  
**Permission errors**: Ensure target directories are writable  
**Space errors**: Verify adequate free space on target drive  
**Missing tools**: Playbook installs required packages automatically  

## Extending

Add new phases by including additional tasks:
- Metadata extraction
- Date-based organization  
- Thumbnail generation
- Backup automation