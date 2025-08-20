# Home Lab Mini PC Server

A simple guide to set up a mini PC home server for family photos, development projects, and personal services with secure internet access.

## 🎯 Goal
Set up a mini PC at home that you can access from anywhere on the internet to:
- Store and manage family photos
- Run your Java/Python projects
- Deploy Telegram bots
- Host web services

## 📋 Top Level Steps

### 1. Hardware Setup
- Get a mini PC (8GB+ RAM, 256GB+ storage)
- Connect to your home network via Ethernet
- Set up in a well-ventilated location

### 2. Install Operating System
- Install Ubuntu Server 22.04 LTS
- Create user account with sudo privileges
- Enable SSH access
- Use automatic DHCP networking (no static IP needed)

### 3. Basic System Configuration + Tailscale
- Update system packages
- **Install Tailscale VPN** for secure remote access
- Configure basic security (firewall, SSH keys)
- Test remote SSH access via Tailscale
- **Remove keyboard/monitor** (headless operation)

### 4. Docker Setup
- Install Docker and Docker Compose
- Set up basic container management

### 5. Photo Storage Setup
- Consolidate photos from old drives
- Organize and deduplicate photos
- Configure additional storage drives

### 6. Deploy Core Services
- Reverse proxy (Traefik or Nginx)
- SSL certificates for HTTPS
- Basic monitoring

### 7. Add Your Applications
- Photo management system
- Development environment
- Your first services

## 🚀 Next Steps

Each of these top-level steps will have its own detailed guide:
- `01-hardware-setup.md`
- `02-os-installation.md` *(simplified networking)*
- `03-basic-config-tailscale.md` *(combines system config + Tailscale)*
- `04-docker-setup.md`
- `05-photo-storage.md`
- `06-core-services.md`
- `07-applications.md`

## 🔗 Quick Links
- [Hardware Requirements](docs/01-hardware-setup.md)
- [OS Installation Guide](docs/02-os-installation.md)
- [Basic Config + Tailscale Setup](docs/03-basic-config-tailscale.md)

## ⚡ Quick Start
1. **Prep**: Create free Tailscale account at [tailscale.com](https://tailscale.com)
2. **Install**: Ubuntu Server with automatic networking
3. **Configure**: System updates + Tailscale (5 minutes)
4. **Go headless**: SSH via Tailscale, disconnect monitor/keyboard

---

Start with steps 1-3 to get a fully accessible server, then continue with your specific needs.