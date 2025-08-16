# Step 2: OS Installation

## 🎯 Goal
Install Ubuntu Server 22.04 LTS on your mini PC with proper storage configuration for your home lab setup.

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

#### Alternative: Windows PowerShell (Advanced)
```powershell
# List available disks
Get-Disk

# Use Windows built-in tool (replace X: with your USB drive letter)
# This is more complex - Rufus is recommended for Windows users
```

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

#### Partition the 1TB NVMe SSD (Flexible Layout for Future Photo Management)
```
Device: /dev/nvme0n1 (1TB NVMe)

Smart partitioning for future flexibility:
1. EFI Boot: 1GB, fat32, /boot/efi
2. Boot: 1GB, ext4, /boot  
3. Root: 100GB, ext4, / (OS + system files)
4. Home: 200GB, ext4, /home (user files, small projects)
5. Docker: 100GB, ext4, /opt/docker (containers)
6. Photos: 400GB, ext4, /mnt/photos (future organized photos)
7. Projects: 150GB, ext4, /mnt/projects (development work)
8. Swap: 32GB (match your RAM)
```

**Why this layout?**
- **Smaller /home**: Just for user configs and small files
- **Dedicated /mnt/photos**: Large space ready for organized photos
- **Dedicated /mnt/projects**: Separate development workspace
- **Flexibility**: Can easily adjust usage without repartitioning

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

Before confirming, verify:
- **1TB NVMe**: Partitioned with /, /home, /mnt/photos, /mnt/projects, /opt/docker
- **Network**: Configured (Ethernet/WiFi)
- **User account**: Created with sudo access
- **SSH**: Enabled
- **Photo drives**: Safely stored (not connected)
- **Flexibility**: Dedicated partitions ready for future reorganization

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
# Check all mounted filesystems
df -h

Expected output:
/dev/nvme0n1p3    100G  ... /            (Root filesystem)
/dev/nvme0n1p4    200G  ... /home        (User configs)
/dev/nvme0n1p5    100G  ... /opt/docker  (Docker data)
/dev/nvme0n1p6    400G  ... /mnt/photos  (Future organized photos)
/dev/nvme0n1p7    150G  ... /mnt/projects (Development projects)
```

```bash
# Check all block devices
lsblk

Expected structure:
nvme0n1         1TB NVMe (well-organized partitions)
├─nvme0n1p1     1G  EFI
├─nvme0n1p2     1G  Boot
├─nvme0n1p3   100G  Root /
├─nvme0n1p4   200G  Home /home  
├─nvme0n1p5   100G  Docker /opt/docker
├─nvme0n1p6   400G  Photos /mnt/photos (ready for Step 6)
├─nvme0n1p7   150G  Projects /mnt/projects
└─nvme0n1p8    32G  Swap

Your photo drives: Safely stored until Step 6
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

### Option 2: WiFi Primary Setup
```bash
# WiFi-first configuration
network:
  version: 2
  renderer: networkd
  wifis:
    wlp2s0:
      dhcp4: false
      addresses:
        - 192.168.1.100/24
      gateway4: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 1.1.1.1
      access-points:
        "YourWiFiNetwork":
          password: "your-wifi-password"
  ethernets:
    enp1s0:
      dhcp4: true  # Ethernet as backup/secondary
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
# Test connectivity (on the mini PC console)
ping google.com

# Check both connections
ip addr show  # See all interfaces and IPs

# Test SSH from your Windows PC
# Use built-in Windows SSH client (Windows 10+):
ssh your-username@192.168.1.100

# Or use PuTTY if you prefer GUI:
# Download from: https://www.putty.org/
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
- ✅ **UPS** (mini PC + router connected)
- ✅ **USB 3.0 Backup Drive** (when ready)

## ✅ Installation Complete!

Your Ubuntu Server is now installed and ready. You have:

- **✅ Ubuntu Server 22.04 LTS** running on Linux mini PC
- **✅ Proper storage layout** for your home lab needs
- **✅ SSH access** enabled for remote management from Windows
- **✅ Network connectivity** configured (Ethernet + WiFi)
- **✅ User account** with sudo privileges
- **✅ Windows photo drives** safely stored for Step 6

## 🔄 Next Steps

Ready for **Step 3: System Configuration** where we'll:
- Set up SSH keys for secure access from Windows
- Install essential tools and Docker on Linux
- Configure basic security (firewall, fail2ban)
- Prepare for NTFS photo drive mounting in Step 6

## 📝 Important Notes for Mixed Environment

### Windows ↔ Linux Compatibility
- **SSH from Windows**: Built-in SSH client or PuTTY
- **File transfers**: We'll set up secure methods in Step 3
- **Photo drives**: NTFS drives will be safely readable on Linux
- **Development**: Your Java/Python projects will work great on Linux

## 🛠️ Troubleshooting

### Boot Issues
- **GRUB not found**: Check UEFI boot order in BIOS
- **Kernel panic**: Try booting from USB again, check RAM seating

### Storage Issues
- **Mount failed**: Check /etc/fstab for correct device names
- **Permission denied**: Verify mount points exist and have correct permissions

### Network Issues
- **No connectivity**: Check cable, verify interface name in netplan
- **DNS not working**: Verify nameservers in netplan configuration

### SSH Issues
- **Connection refused**: Verify SSH service running: `sudo systemctl status ssh`
- **Permission denied**: Check username, password, verify SSH enabled during install

---

**💡 Pro Tip**: Take a snapshot of your VM or create a backup image after successful installation - this gives you a clean baseline to restore if needed!
TODO: Think about arranging partition on 1Tb internal disk (is it necessaey /mnt/projects if I will use separated disk with 512Gb? and for docker and home can be reduced)