# Step 3: Basic System Configuration + Tailscale Setup

## 🎯 Goal
Configure your Ubuntu server for secure remote access via Tailscale, then transition to headless operation (no keyboard/monitor needed).

## 📋 Prerequisites
- **Ubuntu Server installed** (Step 2 complete)
- **Keyboard/monitor still connected** (we'll disconnect them at the end)
- **Internet connection working** (Ethernet or WiFi)
- **Tailscale account created** (free at https://tailscale.com)

## 🚀 System Updates First

### Update System Packages
```bash
# Update package lists
sudo apt update

# Upgrade all packages
sudo apt upgrade -y

# Install essential tools
sudo apt install -y curl wget htop tree unzip

# Reboot if kernel was updated
sudo reboot
```

**Wait for reboot, then log back in**

## 🔐 Install & Configure Tailscale

### 1. Install Tailscale
```bash
# Download and run Tailscale installer
curl -fsSL https://tailscale.com/install.sh | sh

# This installs Tailscale but doesn't connect it yet
```

### 2. Connect to Your Tailscale Account
```bash
# Start Tailscale and connect to your account
sudo tailscale up

# This will output a URL like:
# To authenticate, visit: https://login.tailscale.com/a/...
```

### 3. Authenticate (Two Options)

#### Option A: Use the URL (Easier)
1. **Copy the URL** from the terminal
2. **Open it on your Windows PC** browser
3. **Log in to your Tailscale account**
4. **Approve the device** connection

#### Option B: Use Auth Key (If URL doesn't work)
1. **On your Windows PC**: Go to https://login.tailscale.com/admin/settings/keys
2. **Generate an auth key** (one-time use)
3. **Back on server**: `sudo tailscale up --authkey=YOUR_KEY_HERE`

### 4. Verify Tailscale Connection
```bash
# Check Tailscale status
sudo tailscale status

# Get your Tailscale IP address
tailscale ip -4

# Example output: 100.64.15.42 (this is your stable remote IP!)
```

## 🔥 Configure UFW Firewall

### Enable Basic Firewall
```bash
# Allow SSH (port 22)
sudo ufw allow ssh

# Allow Tailscale interface
sudo ufw allow in on tailscale0

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status verbose
```

## 🌐 Test Remote SSH Access

### From Your Windows PC

#### Option 1: Install Tailscale on Windows (Recommended)
1. **Download Tailscale** from https://tailscale.com/download/windows
2. **Install and login** with your account
3. **Test SSH connection**:
```bash
# Replace with your server's Tailscale IP
ssh your-username@100.64.15.42
```

#### Option 2: Use Tailscale Web SSH (Backup)
1. **Go to**: https://login.tailscale.com/admin/machines
2. **Find your server** in the device list
3. **Click SSH** button to access via browser

### Verify Remote Access Works
```bash
# Test commands via SSH to make sure everything works
whoami
hostname
df -h
tailscale status
```

## 🔑 Set Up SSH Keys (Optional but Recommended)

### Generate SSH Keys on Windows PC
```powershell
# In PowerShell on your Windows PC
ssh-keygen -t ed25519 -C "your-email@example.com"

# This creates keys in: C:\Users\YourName\.ssh\
```

### Copy Public Key to Server
```bash
# From your Windows PC, copy public key to server
scp C:\Users\YourName\.ssh\id_ed25519.pub your-username@100.64.15.42:~/

# On the server, add the key
mkdir -p ~/.ssh
cat ~/id_ed25519.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
rm ~/id_ed25519.pub

# Test passwordless login
exit
ssh your-username@100.64.15.42  # Should not ask for password
```

## 📱 Install Tailscale on Your Phone (Bonus)

### Mobile Access
1. **Download Tailscale app** (iOS/Android)
2. **Login with your account**
3. **SSH from your phone** using apps like:
    - **Termius** (iOS/Android)
    - **JuiceSSH** (Android)
    - **Blink** (iOS)

## 🎉 Transition to Headless Operation

### Final Tests Before Disconnecting
```bash
# 1. Verify SSH works from all your devices
# 2. Test basic server commands remotely
# 3. Confirm Tailscale IP is stable

# Check your Tailscale IP one more time
tailscale ip -4
# Remember this IP: 100.64.15.42 (example)
```

### Clean Up Physical Setup
**Now you can disconnect and store these items:**
- ❌ **USB Keyboard** (not needed anymore)
- ❌ **Monitor/TV** (not needed anymore)
- ❌ **HDMI Cable** (not needed anymore)

### Keep Connected
- ✅ **Ethernet Cable** (primary internet)
- ✅ **Power Cable** (to UPS)
- ✅ **Old drives with photos** (for later consolidation)

## 🔍 Verify Headless Operation

### From Your Windows PC
```bash
# SSH to your server using Tailscale IP
ssh your-username@100.64.15.42

# Run some commands to verify everything works
htop          # Check system resources (press 'q' to quit)
df -h         # Check disk space
sudo systemctl status tailscaled  # Verify Tailscale is running
```

## 📋 Tailscale Management

### Useful Commands
```bash
# Check connection status
sudo tailscale status

# See your IPs
tailscale ip

# Logout from Tailscale (if needed)
sudo tailscale logout

# Reconnect to Tailscale
sudo tailscale up
```

### Web Dashboard
- **URL**: https://login.tailscale.com/admin/machines
- **Features**:
    - See all connected devices
    - Monitor connection status
    - Configure access controls
    - Generate SSH commands

## 🌟 What You've Accomplished

### ✅ Secure Remote Access
- **Tailscale VPN** connecting your server to your account
- **Encrypted connections** from anywhere on the internet
- **No port forwarding** needed on your router
- **Stable IP address** (100.64.x.x) that never changes

### ✅ Headless Server Operation
- **No keyboard/monitor** needed anymore
- **SSH access** from Windows PC, phone, laptop
- **Firewall configured** for security
- **System updated** and ready for Docker

### ✅ Multi-Device Access
- **Windows PC**: Tailscale client + SSH
- **Phone**: Tailscale app + SSH client
- **Laptop**: Install Tailscale anywhere for access

## 🎯 Next Steps

Your server is now fully accessible remotely! Next steps:

1. **Docker Installation** (Step 4) - Install Docker for containerized services
2. **Photo Consolidation** (Step 5) - Safely move photos to the `/data` partition
3. **Core Services** (Step 6) - Web interfaces and monitoring

## 🆘 Troubleshooting

### Tailscale Not Connecting
```bash
# Check Tailscale logs
sudo journalctl -u tailscaled -f

# Restart Tailscale service
sudo systemctl restart tailscaled
sudo tailscale up
```

### SSH Not Working
```bash
# Check SSH service
sudo systemctl status ssh

# Check firewall
sudo ufw status

# Verify Tailscale IP
tailscale ip -4
```

### Can't Access from Windows
1. **Install Tailscale on Windows PC**
2. **Login with same account**
3. **Wait 30 seconds** for network sync
4. **Try SSH again**

**Your server is now fully configured for remote access! 🎉**