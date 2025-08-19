# Step 2: OS Installation & Initial Setup

## 🎯 Goal
Install Ubuntu Server 22.04 LTS on your mini PC with final storage configuration for your home lab setup.

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

**You'll need these items temporarily for the initial installation:**

### Required for Installation
- **USB Keyboard**: Any USB keyboard for setup
- **Monitor/TV**: HDMI monitor or TV with HDMI input
- **HDMI Cable**: To connect mini PC to screen
- **USB Drive**: With Ubuntu Server installer (created above)

### After Installation
- **Remove**: Keyboard, monitor, HDMI cable (won't need them anymore)
- **Keep connected**: Ethernet cable, power, UPS
- **Access**: Everything via SSH from your main PC/laptop

## 🖥️ BIOS/UEFI Setup

### Boot Settings
1. **Power on** mini PC with USB drive inserted
2. **Enter BIOS**: Usually F2, F12, or Del during boot
3. **Boot order**: Set USB drive as first boot device
4. **Secure Boot**: Disable if having issues (can re-enable later)
5. **UEFI mode**: Ensure UEFI (not Legacy) mode is selected

### Check Hardware Detection
- Verify 32GB RAM detected
- Confirm all SSDs visible (1TB NVMe + 512GB SATA)
- Check Ethernet connection

## 🚀 Installation Process

### 1. Boot from USB
- Select "Try or Install Ubuntu Server"
- Choose your language (English recommended for tutorials)

### 2. Initial Setup
- **Language**: English
- **Keyboard**: Your keyboard layout
- **Network**: Configure connections
    - **Ethernet**: Should auto-detect and connect
    - **WiFi**: Can configure during installation or later
    - Set static IP if you know your network setup
    - Or use DHCP for now (can change later)

### 3. Storage Configuration

This is the most important part for your setup!

#### Choose Manual Storage Layout
```
Select: "Custom storage layout"
Not: "Use entire disk" (we need specific partitioning)
```

## 🗂️ Single-Phase Storage Strategy

**We'll set up the final configuration immediately, leaving old drives untouched until photo consolidation:**

---

## 📦 Final Installation Partitioning

#### Partition the 1TB NVMe SSD (Final Layout)
```
Device: /dev/nvme0n1 (1TB NVMe) - Final optimized layout

1. EFI Boot: 1GB, fat32, /boot/efi
2. Boot: 1GB, ext4, /boot
3. Root: 50GB, ext4, / (minimal OS)
4. Home: 50GB, ext4, /home (user configs only)
5. Photos: 800GB, ext4, /mnt/photos (organized photo storage)
6. Swap: 16GB (adequate for server use)
```

#### Leave Other Drives Untouched During Installation
```
512GB SSD (Internal SATA): Leave as-is (has your photos)
1TB SSD (External USB): Leave as-is (has your photos)

Note: These will be configured later after photo consolidation
```

---

## 🎯 Next Steps After Installation

### Photo Consolidation (Step 6)
After Ubuntu installation, you'll safely consolidate photos from your old drives:
1. **Mount old drives temporarily** (without formatting)
2. **Copy all photos** to `/mnt/photos` (800GB partition ready)
3. **Organize and deduplicate** photos
4. **Verify backup** before proceeding to storage setup

### Storage Setup (Step 7)
After photo consolidation, configure old drives for development:
- **512GB SSD**: Format for Docker, Projects, Databases
- **1TB External**: Format for backups
- **Auto-mounting**: Configure permanent mount points
- **Performance optimization**: SSD optimizations and directory structure

---

## 📋 Final Storage Layout

### After Complete Setup:
```
1TB NVMe (Primary):
├── EFI Boot: 1GB, /boot/efi
├── Boot: 1GB, /boot
├── Root: 50GB, / (OS)
├── Home: 50GB, /home (configs)
├── Photos: 800GB, /mnt/photos (organized photos)
└── Swap: 16GB

512GB SSD (Development):
├── Docker: 200GB, /opt/docker
├── Projects: 200GB, /mnt/projects
└── Databases: 112GB, /mnt/databases

1TB External (Backups):
└── Backup: 1TB, /mnt/backup
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

### 6. Software Selection

#### Recommended Snaps
```
❌ Docker (we'll install manually for better control)
❌ Other snaps (install what you need later)
```

Keep it minimal - we'll install everything we need manually.

## 📋 Installation Summary

Before confirming installation, verify:
- **1TB NVMe**: Final partitioning (/, /home, /mnt/photos)
- **Network**: Configured (Ethernet/WiFi)
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
/dev/nvme0n1p4     50G  ... /home        (User configs)
/dev/nvme0n1p5    800G  ... /mnt/photos  (Photo storage - empty initially)
```

```bash
# Check all block devices
lsblk

Expected structure:
nvme0n1         1TB NVMe (Final optimized layout)
├─nvme0n1p1     1G  EFI
├─nvme0n1p2     1G  Boot
├─nvme0n1p3    50G  Root /
├─nvme0n1p4    50G  Home /home
├─nvme0n1p5   800G  Photos /mnt/photos
└─nvme0n1p6    16G  Swap

sdb             512G SSD (Your old drive - untouched)
sdc             1TB External (Your old drive - untouched)
```

## 🌐 Network Configuration

### Option 1: Ethernet Primary with WiFi Backup (Recommended)
```bash
# Edit netplan configuration
sudo nano /etc/netplan/00-installer-config.yaml

# Ethernet primary + WiFi backup configuration:
network:
  version: 2
  renderer: networkd
  ethernets:
    enp1s0:  # Your ethernet interface name
      dhcp4: false
      addresses:
        - 192.168.1.100/24  # Choose available IP in your network
      gateway4: 192.168.1.1  # Your router IP
      nameservers:
        addresses:
          - 8.8.8.8
          - 1.1.1.1
  wifis:
    wlp2s0:  # Your WiFi interface name
      dhcp4: true
      access-points:
        "YourWiFiNetwork":
          password: "your-wifi-password"

# Apply changes
sudo netplan apply
```

### Check Interface Names
```bash
# Find your network interface names
ip link show

# Common names:
# Ethernet: enp1s0, eth0, enp0s31f6
# WiFi: wlp2s0, wlan0, wlp0s20f3
```

### Test Network
```bash
# Test connectivity
ping google.com

# Test SSH from your Windows PC
ssh your-username@192.168.1.100
```

## 🎉 Clean Up Physical Setup

### After Successful Installation & SSH Test
**You can now disconnect and store these items:**
- ❌ **USB Keyboard** (not needed anymore)
- ❌ **Monitor/TV** (not needed anymore)
- ❌ **HDMI Cable** (not needed anymore)
- ❌ **Installation USB Drive** (keep for future use)

### Keep Connected
- ✅ **Ethernet Cable** (to router/switch)
- ✅ **Power Cable** (to UPS)
- ✅ **Old drives with photos** (for consolidation)

## ✅ Single-Phase Installation Complete!

Your Ubuntu Server is now installed with the final optimized layout. You have:

- **✅ Ubuntu Server 22.04 LTS** running with final partition layout
- **✅ 800GB dedicated photos partition** ready for consolidation
- **✅ SSH access** for remote management
- **✅ Old drives preserved** with original photos intact

**Next**: Photo consolidation (Step 6) and storage setup (Step 7) for complete configuration.