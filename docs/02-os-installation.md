# Step 2: OS Installation & Initial Setup

## 🎯 Goal
Install Ubuntu Server 22.04 LTS on your mini PC with automatic networking (no static IP needed since we'll use Tailscale).

## 🐧 Why Ubuntu Server 22.04 LTS?
- **Long Term Support**: Updates until 2027
- **Excellent hardware support**: Works great with AMD Ryzen mini PCs
- **Docker friendly**: Native Docker support
- **Large community**: Tons of tutorials and help available
- **Stable**: Perfect for 24/7 home server operation

## 📥 Download Ubuntu Server

**Note**: Do this on your Windows PC/laptop, not the mini PC

### Get the ISO
```bash
# Download via browser (easiest on Windows):
# Go to: https://ubuntu.com/download/server
# Download: ubuntu-22.04.3-live-server-amd64.iso

# Or using PowerShell:
Invoke-WebRequest -Uri "https://releases.ubuntu.com/22.04/ubuntu-22.04.3-live-server-amd64.iso" -OutFile "ubuntu-22.04.3-live-server-amd64.iso"
```

### Create Installation Media

**Use your Windows PC to create the USB installer**

#### Recommended: Rufus (Windows)
1. **Download Rufus**: https://rufus.ie/
2. **Insert USB drive** (8GB+, will be erased)
3. **Open Rufus**:
    - Device: Select your USB drive
    - Boot selection: SELECT the Ubuntu ISO file
    - Partition scheme: GPT
    - Target system: UEFI
4. **Click START** and wait for completion

#### Alternative: Balena Etcher
1. **Download Etcher**: https://www.balena.io/etcher/
2. **Select Ubuntu ISO**
3. **Select USB drive**
4. **Flash** and wait

## 🖥️ Temporary Setup for Installation

**You'll need these items temporarily - we'll remove them after Tailscale setup:**

### Required for Installation
- **USB Keyboard**: Any USB keyboard for setup
- **Monitor/TV**: HDMI monitor or TV with HDMI input
- **HDMI Cable**: To connect mini PC to screen
- **USB Drive**: With Ubuntu Server installer (created above)

### After Tailscale Setup
- **Remove**: Keyboard, monitor, HDMI cable (won't need them anymore)
- **Keep connected**: Ethernet cable, power, UPS
- **Access**: Everything via SSH through Tailscale

## 🖥️ BIOS/UEFI Setup

### Boot Settings
1. **Power on** mini PC with USB drive inserted
2. **Enter BIOS**: Usually F2, F12, or Del during boot
3. **Boot order**: Set USB drive as first boot device
4. **Secure Boot**: Disable if having issues (can re-enable later)
5. **UEFI mode**: Ensure UEFI (not Legacy) mode is selected

### Check Hardware Detection
- Verify 32GB RAM detected
- Confirm all SSDs visible (1TB NVMe)
- Check Ethernet connection

## 🚀 Installation Process

### 1. Boot from USB
- Select "Try or Install Ubuntu Server"
- Choose your language (English recommended for tutorials)

### 2. Initial Setup
- **Language**: English
- **Keyboard**: Your keyboard layout
- **Network**: Use automatic configuration
    - **Ethernet**: Should auto-detect and connect via DHCP ✅
    - **WiFi**: Can configure if needed, also use DHCP ✅
    - **No static IP needed** - Tailscale will handle stable addressing

### 3. Storage Configuration

This is the most important part for your setup!

#### Choose Manual Storage Layout
```
Select: "Custom storage layout"
Not: "Use entire disk" (we need specific partitioning)
```

## 📦 Final Installation Partitioning

#### Partition the 1TB NVMe SSD (Final Layout)
```
Device: /dev/nvme0n1 (1TB NVMe) - Final optimized layout

1. EFI Boot: 1GB, fat32, /boot/efi
2. Boot: 1GB, ext4, /boot
3. Root: 50GB, ext4, / (minimal OS)
4. Home: 20GB, ext4, /home (user configs only)
5. Photos: 911GB, ext4, /data (organized photo storage)
6. Swap: 16GB (adequate for server use)
```

#### Leave Other Drives Untouched During Installation
```
512GB SSD (Internal SATA): Leave as-is (has your photos)
1TB SSD (External USB): Leave as-is (has your photos)

Note: These will be configured later after photo consolidation
```

### 4. User Account Setup
```
Your name: Your Full Name
Your server's name: homelab-server (or your preference)
Pick a username: your-username
Choose a password: Strong password
Confirm your password: Same password
```

**Important**: This user will have sudo privileges

### 5. SSH Setup
```
✅ Install OpenSSH server
✅ Import SSH identity: No (we'll set up keys later)
```

**Note**: During installation, you'll see this option in the Ubuntu installer interface. If you need to install SSH manually later:
```bash
# If SSH wasn't installed during setup, run this after installation:
sudo apt update
sudo apt install openssh-server
sudo systemctl enable ssh
sudo systemctl start ssh
```

### 6. Software Selection

#### Recommended Snaps
```
❌ Docker (we'll install manually for better control)
❌ Other snaps (install what you need later)
```

Keep it minimal - we'll install everything we need manually.

## 📋 Installation Summary

Before confirming installation, verify:
- **1TB NVMe**: Final partitioning (/, /home, /data)
- **Network**: Auto-configured DHCP (Ethernet/WiFi)
- **User account**: Created with sudo access
- **SSH**: Enabled
- **Old drives**: Left untouched (will handle photos after installation)

Click **Done** and **Continue** to start installation.

## ⏱️ Installation Time
- **Duration**: 10-20 minutes depending on drive speed
- **Process**: System will copy files and configure bootloader
- **Reboot**: System will reboot automatically when done

## 🎉 First Boot

### 1. Remove Installation Media
- Remove USB drive when prompted
- System will boot from NVMe SSD

### 2. Login
```bash
# Login with your created username
login: your-username
password: your-password
```

### 3. Verify Installation
```bash
# Check system info
hostnamectl

# Check storage mounts
df -h

# Check RAM
free -h

# Check network
ip addr show
```

### 4. Update System
```bash
# Update package lists
sudo apt update

# Upgrade installed packages
sudo apt upgrade -y

# Reboot if kernel was updated
sudo reboot
```

## 🔍 Verify Storage Setup

After reboot, check your storage layout:

```bash
# Check mounted filesystems - Final Layout
df -h

Expected output:
/dev/nvme0n1p3     50G  ... /            (Root - minimal OS)
/dev/nvme0n1p4     20G  ... /home        (User configs)
/dev/nvme0n1p5    911GB  ... /data  (Photo storage - empty initially)
```

```bash
# Check all block devices
lsblk

Expected structure:
nvme0n1         1TB NVMe (Final optimized layout)
├─nvme0n1p1     1G  EFI
├─nvme0n1p2     1G  Boot
├─nvme0n1p3    50G  Root /
├─nvme0n1p4    20G  Home /home
├─nvme0n1p5   911GB  Photos /data
└─nvme0n1p6    16G  Swap

sdb             512G SSD (Your old drive - untouched)
sdc             1TB External (Your old drive - untouched)
```

## 🌐 Network Verification

### Simple DHCP Check
```bash
# Check your current IP (will change, but that's okay)
ip addr show

# Test internet connectivity
ping google.com

# Note your current local IP for testing local SSH
hostname -I
```

### Test Local SSH (Optional)
```bash
# From another device on your home network (Windows PC, phone on same WiFi):
ssh your-username@192.168.1.XXX  # Replace XXX with actual IP

# This works locally but NOT from internet yet
# Tailscale in Step 3 will enable internet access
```

**Important**: This SSH only works from devices on your home network. Internet access requires Tailscale (Step 3).

## ✅ Installation Complete!

Your Ubuntu Server is now installed with:

- **✅ Ubuntu Server 22.04 LTS** running with final partition layout
- **✅ Automatic DHCP networking** (simple and reliable)
- **✅ SSH enabled** for remote access
- **✅ 911GB dedicated photos partition** ready for consolidation
- **✅ Old drives preserved** with original photos intact

## 🎯 Next Steps

**Keep keyboard/monitor connected** for one more step:

**Next**: Basic System Configuration + Tailscale Setup (Step 3) - this will enable remote access so you can disconnect the keyboard and monitor.