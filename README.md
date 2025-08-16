# Home Lab Mini PC Server

A simple guide to set up a mini PC home server for family photos, development projects, and personal services with internet access.

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

### 3. Basic System Configuration
- Set static IP address on your local network
- Update system packages
- Configure basic security (firewall, SSH keys)

### 4. Internet Access Setup
- **Tailscale VPN**: Set up Tailscale for secure remote access
- No port forwarding needed on your router
- Works from anywhere with encrypted connections
- Easy device management through Tailscale admin panel

### 5. Install Docker
- Install Docker and Docker Compose
- Set up basic container management

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
- `02-os-installation.md`
- `03-system-config.md`
- `04-internet-access.md`
- `05-docker-setup.md`
- `06-core-services.md`
- `07-applications.md`

## 🔗 Quick Links
- [Hardware Requirements](docs/01-hardware-setup.md)
- [OS Installation Guide](docs/02-os-installation.md)
- [Tailscale Setup Guide](docs/04-tailscale-setup.md)

---

Start with step 1-3 to get a basic working server, then choose your internet access method in step 4.