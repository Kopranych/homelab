# Nextcloud Deployment - Quick Reference

## Prerequisites

### Windows (Recommended: WSL2)

**Option 1: WSL2 (Recommended)**

Windows doesn't support Ansible natively. Use Windows Subsystem for Linux (WSL2):

```powershell
# 1. Install WSL2 (PowerShell as Administrator)
wsl --install

# If already installed, update to WSL2
wsl --set-default-version 2

# 2. Install Ubuntu from Microsoft Store
# Search for "Ubuntu" in Microsoft Store and install

# 3. Launch Ubuntu and set up user account
# (follow prompts for username/password)
```

Then in Ubuntu (WSL):
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Ansible
sudo apt install -y ansible python3-pip

# Verify installation
ansible --version

# Navigate to your project (Windows drives are mounted at /mnt/)
cd /mnt/c/Users/YOUR_USERNAME/PycharmProjects/homelab/infra/ansible

# Install required Ansible collections
ansible-galaxy collection install -r requirements.yml
```

**Option 2: Git Bash + SSH to Linux VM (Alternative)**

If WSL isn't available, use Git Bash to SSH into a Linux VM or server where Ansible is installed.

### macOS

```bash
# Install Ansible via Homebrew
brew install ansible

# Install required collections
cd infra/ansible
ansible-galaxy collection install -r requirements.yml
```

### Linux (Ubuntu/Debian)

```bash
# Install Ansible
sudo apt update
sudo apt install -y ansible python3-pip

# Install required collections
cd infra/ansible
ansible-galaxy collection install -r requirements.yml
```

### Verify Installation

```bash
# Check Ansible version (should be 2.14+)
ansible --version

# Check Python version (should be 3.8+)
python3 --version

# List installed collections
ansible-galaxy collection list
```

## Initial Setup

1. **Configure inventory** - Edit `inventory/homelab` with your server IP:
```ini
[homelab]
homelab-server ansible_host=192.168.1.100 ansible_user=your_username
```

2. **Set up SSH key authentication** (required for passwordless Ansible):
```bash
# Generate SSH key (press ENTER when asked for file location - don't type anything!)
ssh-keygen -t ed25519

# When prompted:
# "Enter file in which to save the key (/home/username/.ssh/id_ed25519):"
# Press ENTER (accept default location)
#
# "Enter passphrase (empty for no passphrase):"
# Press ENTER twice (leave empty for convenience)

# Copy your SSH key to the server (will prompt for server password once)
ssh-copy-id your_username@192.168.1.100

# Test SSH connection (should work without password)
ssh your_username@192.168.1.100
```

**Important**: When generating the SSH key, press **ENTER** to accept the default file location. Do NOT type "yes" or any other filename unless you know what you're doing.

3. **Update passwords** - Edit `group_vars/all.yml`:
```yaml
nextcloud:
  admin:
    password: "change_this_password"
  database:
    password: "change_this_password"
  redis:
    password: "change_this_password"
```

4. **Test Ansible connection**:
```bash
ansible -i inventory/homelab homelab -m ping

# If you get "Permission denied", you may need to use password authentication temporarily:
ansible -i inventory/homelab homelab -m ping --ask-pass
```

## Deployment Commands

### Full Deployment (Recommended)
```bash
# Deploy everything: Docker + Nextcloud + HTTPS
ansible-playbook -i inventory/homelab nextcloud.yml
```

### Step-by-Step Deployment

```bash
# 1. Install Docker only
ansible-playbook -i inventory/homelab install-docker.yml

# 2. Deploy Nextcloud
ansible-playbook -i inventory/homelab deploy-nextcloud.yml
```

### Deployment Options

```bash
# Skip Docker installation (if already installed)
ansible-playbook -i inventory/homelab nextcloud.yml --skip-tags docker

# Deploy without HTTPS
ansible-playbook -i inventory/homelab nextcloud.yml -e "nextcloud_https_enabled=false"

# Verbose output (for debugging)
ansible-playbook -i inventory/homelab nextcloud.yml -vvv

# Dry run (check mode - see what would change without making changes)
ansible-playbook -i inventory/homelab nextcloud.yml --check

# Show differences (what will be changed)
ansible-playbook -i inventory/homelab nextcloud.yml --check --diff

# Step through tasks one by one (interactive)
ansible-playbook -i inventory/homelab nextcloud.yml --step
```

## Comprehensive Command Examples

### Testing and Validation

```bash
# Test SSH connectivity to server
ansible -i inventory/homelab homelab -m ping

# Test with verbose output
ansible -i inventory/homelab homelab -m ping -vvv

# Check if server is reachable
ansible -i inventory/homelab homelab -m command -a "uptime"

# Gather facts about the server
ansible -i inventory/homelab homelab -m setup

# Check specific fact (e.g., IP address)
ansible -i inventory/homelab homelab -m setup -a "filter=ansible_default_ipv4"

# Syntax check (validate playbook without running)
ansible-playbook -i inventory/homelab nextcloud.yml --syntax-check

# List all tasks that would be executed
ansible-playbook -i inventory/homelab nextcloud.yml --list-tasks

# List all tags available
ansible-playbook -i inventory/homelab nextcloud.yml --list-tags

# List all hosts that would be affected
ansible-playbook -i inventory/homelab nextcloud.yml --list-hosts
```

### Deployment Variations

```bash
# Basic deployment
ansible-playbook -i inventory/homelab nextcloud.yml

# Deploy with custom admin password
# Deploy with custom admin password
ansible-playbook -i inventory/homelab nextcloud.yml \
  -e "nextcloud.admin.password=MySecurePassword123"

# Deploy only Docker (skip Nextcloud)
ansible-playbook -i inventory/homelab nextcloud.yml --tags docker

# Deploy only Nextcloud (skip Docker)
ansible-playbook -i inventory/homelab nextcloud.yml --tags nextcloud

# Skip specific tags
ansible-playbook -i inventory/homelab nextcloud.yml --skip-tags verify

# Deploy with different user
ansible-playbook -i inventory/homelab nextcloud.yml -u different_user

# Deploy with sudo password prompt
ansible-playbook -i inventory/homelab nextcloud.yml --ask-become-pass

# Deploy with SSH password prompt (if no key)
ansible-playbook -i inventory/homelab nextcloud.yml --ask-pass

# Deploy with both passwords
ansible-playbook -i inventory/homelab nextcloud.yml --ask-pass --ask-become-pass

# Deploy with custom SSH key
ansible-playbook -i inventory/homelab nextcloud.yml \
  --private-key ~/.ssh/custom_key

# Deploy with custom SSH port
ansible -i inventory/homelab homelab -m ping -e "ansible_port=2222"
ansible-playbook -i inventory/homelab nextcloud.yml -e "ansible_port=2222"
```

### Debugging and Troubleshooting

```bash
# Verbose output levels
ansible-playbook -i inventory/homelab nextcloud.yml -v      # Basic verbose
ansible-playbook -i inventory/homelab nextcloud.yml -vv     # More verbose
ansible-playbook -i inventory/homelab nextcloud.yml -vvv    # Very verbose (connection debugging)
ansible-playbook -i inventory/homelab nextcloud.yml -vvvv   # SSH debugging

# Check mode (dry run - no changes made)
ansible-playbook -i inventory/homelab nextcloud.yml --check

# Show differences before applying
ansible-playbook -i inventory/homelab nextcloud.yml --diff

# Check mode with diff
ansible-playbook -i inventory/homelab nextcloud.yml --check --diff

# Step through execution (confirm each task)
ansible-playbook -i inventory/homelab nextcloud.yml --step

# Start at specific task
ansible-playbook -i inventory/homelab nextcloud.yml --start-at-task="Deploy Nextcloud"

# Limit to specific hosts (if multiple in inventory)
ansible-playbook -i inventory/homelab nextcloud.yml --limit homelab-server

# Run specific tasks by tags
ansible-playbook -i inventory/homelab nextcloud.yml --tags "docker,nextcloud"
```

### Advanced Options

```bash
# Run with multiple extra variables
ansible-playbook -i inventory/homelab nextcloud.yml \
  -e "nextcloud_https_enabled=true" \
  -e "nextcloud.admin.user=myadmin" \
  -e "nextcloud.admin.password=SecurePass123"

# Load variables from file
ansible-playbook -i inventory/homelab nextcloud.yml \
  -e "@custom_vars.yml"

# Parallel execution (forks - useful for multiple servers)
ansible-playbook -i inventory/homelab nextcloud.yml --forks 10

# Set connection timeout
ansible-playbook -i inventory/homelab nextcloud.yml \
  -e "ansible_timeout=60"

# Force handlers to run (even if task didn't change)
ansible-playbook -i inventory/homelab nextcloud.yml --force-handlers

# Don't gather facts (faster, if facts not needed)
ansible-playbook -i inventory/homelab nextcloud.yml \
  -e "gather_facts=false"
```

### Undeployment Variations

```bash
# Basic undeployment (containers only)
ansible-playbook -i inventory/homelab undeploy-nextcloud.yml

# Remove containers and images
ansible-playbook -i inventory/homelab undeploy-nextcloud.yml \
  -e "remove_images=true"

# Remove everything including data (DANGEROUS)
ansible-playbook -i inventory/homelab undeploy-nextcloud.yml \
  -e "remove_data=true" \
  -e "remove_images=true"

# Remove Docker completely
ansible-playbook -i inventory/homelab undeploy-nextcloud.yml \
  -e "remove_docker=true"

# Nuclear option - remove EVERYTHING
ansible-playbook -i inventory/homelab undeploy-nextcloud.yml \
  -e "remove_data=true" \
  -e "remove_images=true" \
  -e "remove_docker=true"

# Force undeployment without confirmation prompts
ansible-playbook -i inventory/homelab undeploy-nextcloud.yml \
  -e "force=true" \
  -e "remove_data=true"

# Check what would be removed (dry run)
ansible-playbook -i inventory/homelab undeploy-nextcloud.yml \
  --check --diff \
  -e "remove_data=true"
```

### Specific Component Operations

```bash
# Install only Docker
ansible-playbook -i inventory/homelab install-docker.yml

# Install Docker with verbose output
ansible-playbook -i inventory/homelab install-docker.yml -vvv

# Check Docker installation (dry run)
ansible-playbook -i inventory/homelab install-docker.yml --check

# Deploy only Nextcloud (assumes Docker already installed)
ansible-playbook -i inventory/homelab deploy-nextcloud.yml

# Deploy Nextcloud without HTTPS
ansible-playbook -i inventory/homelab deploy-nextcloud.yml \
  -e "nextcloud_https_enabled=false"

# Redeploy (useful after config changes)
ansible-playbook -i inventory/homelab deploy-nextcloud.yml --tags nextcloud
```

### Production Examples

```bash
# Production deployment with all options
ansible-playbook -i inventory/homelab nextcloud.yml \
  -e "nextcloud.admin.password=$(openssl rand -base64 32)" \
  -e "nextcloud.database.password=$(openssl rand -base64 32)" \
  -e "nextcloud.redis.password=$(openssl rand -base64 32)" \
  --diff

# Deployment with external vars file
ansible-playbook -i inventory/homelab nextcloud.yml \
  -e "@production_vars.yml" \
  --diff

# Safe deployment (check first, then deploy)
ansible-playbook -i inventory/homelab nextcloud.yml --check --diff
# Review output, then:
ansible-playbook -i inventory/homelab nextcloud.yml

# Deployment with logging
ansible-playbook -i inventory/homelab nextcloud.yml \
  | tee deployment_$(date +%Y%m%d_%H%M%S).log
```

### Using with Different Inventory Files

```bash
# Development server
ansible-playbook -i inventory/dev nextcloud.yml

# Production server
ansible-playbook -i inventory/prod nextcloud.yml

# Staging server
ansible-playbook -i inventory/staging nextcloud.yml

# Multiple servers at once
ansible-playbook -i inventory/all_servers nextcloud.yml
```

## Access Nextcloud

After deployment:
- **HTTPS**: `https://your-tailscale-hostname.ts.net`
- **HTTP**: `http://server-ip`
- **Localhost**: `http://localhost` (on server)

Default credentials:
- Username: `admin`
- Password: `admin_pass_2024` (change immediately!)

## Management

### View Logs
```bash
# SSH to server
ssh your_username@server-ip

# View logs
cd ~/docker-compose/nextcloud
docker compose logs -f

# View specific service
docker compose logs -f nextcloud-app
docker compose logs -f traefik
```

### Restart Services
```bash
cd ~/docker-compose/nextcloud
docker compose restart              # All services
docker compose restart nextcloud-app  # Specific service
```

### Stop/Start
```bash
docker compose stop    # Stop all
docker compose start   # Start all
docker compose up -d   # Start in background
```

## Undeployment

```bash
# Remove containers only (keep data)
ansible-playbook -i inventory/homelab undeploy-nextcloud.yml

# Remove containers + images
ansible-playbook -i inventory/homelab undeploy-nextcloud.yml -e "remove_images=true"

# DANGEROUS: Remove everything including data
ansible-playbook -i inventory/homelab undeploy-nextcloud.yml \
  -e "remove_data=true remove_images=true"

# Remove Docker completely
ansible-playbook -i inventory/homelab undeploy-nextcloud.yml -e "remove_docker=true"
```

## Common Issues

### "Docker permission denied"
```bash
# On server, after Docker installation:
newgrp docker
# OR logout and login again
```

### "Cannot create or write into data directory"
```bash
# On server:
sudo chown -R 33:33 /data/docker/nextcloud/data
sudo chmod 770 /data/docker/nextcloud/data
cd ~/docker-compose/nextcloud
docker compose restart nextcloud-app
```

### HTTPS not working
```bash
# Check Tailscale status
tailscale status

# Check certificates
sudo ls -la /var/lib/tailscale/certs/

# Check Traefik container
docker exec nextcloud-traefik ls -la /certs/

# View Traefik logs
docker compose logs traefik | grep -i cert
```

### Containers won't start
```bash
# Check container status
docker compose ps

# View all logs
docker compose logs

# Restart everything
docker compose down
docker compose up -d
```

## File Locations

On the server:
- **Docker Compose**: `~/docker-compose/nextcloud/docker-compose.yml`
- **Certificates**: `~/docker-compose/nextcloud/certs/`
- **Data**: `/data/docker/nextcloud/`
- **User Files**: `/data/nextcloud/files/`
- **Photos**: `/data/photo-consolidation/`

## Security Checklist

- [ ] Change Nextcloud admin password
- [ ] Change database password in `group_vars/all.yml`
- [ ] Change Redis password in `group_vars/all.yml`
- [ ] Enable HTTPS via Tailscale
- [ ] Configure Tailscale ACLs
- [ ] Set up regular backups
- [ ] Update trusted domains if needed

## Next Steps After Deployment

1. **Access Nextcloud** in browser
2. **Complete initial setup** if prompted
3. **Change default password** in settings
4. **Install mobile apps**:
   - Install Tailscale on phone
   - Install Nextcloud app
   - Connect using `https://your-tailscale-hostname.ts.net`
5. **Configure photo auto-upload** (optional)

## Help

- **Full documentation**: `docs/04-nextcloud-setup.md`
- **Ansible README**: `infra/ansible/README.md`
- **View playbook variables**: `cat group_vars/all.yml`
- **Check container logs**: `docker compose logs -f`
