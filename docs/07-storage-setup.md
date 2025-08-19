# Step 7: Storage Setup - Configure Development and Backup Drives

## 🎯 Goal
Configure the 512GB SSD and 1TB external drive for development, databases, and backups after photo consolidation is complete.

## ⚠️ Prerequisites
- Ubuntu Server installed (Step 2)
- Photos successfully consolidated to `/mnt/photos` (Step 6)
- Old drives ready for reformatting

---

## 📋 Current State Check

First, verify your current setup and identify drives:

```bash
# Check current storage layout
lsblk
df -h

# Expected current state:
# nvme0n1 (1TB) - Already configured with Ubuntu + photos
# sdb (512GB) - Old drive with photos (to be reformatted)
# sdc (1TB) - External drive with photos (to be reformatted)

# Check which drives have your photos
sudo mkdir -p /mnt/check_disk1 /mnt/check_disk2
sudo mount /dev/sdb1 /mnt/check_disk1 2>/dev/null || echo "sdb1 not mountable"
sudo mount /dev/sdc1 /mnt/check_disk2 2>/dev/null || echo "sdc1 not mountable"

# List contents to verify
ls -la /mnt/check_disk1
ls -la /mnt/check_disk2
```

---

## 🔒 SAFETY: Photo Backup Verification

**CRITICAL: Only proceed after verifying photos are safely copied!**

```bash
# Verify photos are in /mnt/photos
ls -la /mnt/photos/
du -sh /mnt/photos/*

# Check photo count comparison
echo "Photos on old disk1:"
find /mnt/check_disk1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.raw" -o -iname "*.cr2" -o -iname "*.nef" \) | wc -l

echo "Photos on old disk2:"
find /mnt/check_disk2 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.raw" -o -iname "*.cr2" -o -iname "*.nef" \) | wc -l

echo "Photos in new location:"
find /mnt/photos -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.raw" -o -iname "*.cr2" -o -iname "*.nef" \) | wc -l

# ONLY CONTINUE IF PHOTO COUNTS MATCH OR YOU'RE SATISFIED WITH BACKUP
```

---

## 🛑 Unmount Old Drives

```bash
# Unmount old drives before repartitioning
sudo umount /mnt/check_disk1 2>/dev/null || echo "disk1 not mounted"
sudo umount /mnt/check_disk2 2>/dev/null || echo "disk2 not mounted"

# Remove temporary mount points
sudo rmdir /mnt/check_disk1 /mnt/check_disk2
```

---

## 🔧 Setup 512GB SSD for Development

### Step 1: Identify the 512GB Drive
```bash
# List all drives with sizes
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT

# Identify your 512GB drive (usually sdb, but verify!)
# We'll assume it's /dev/sdb - REPLACE WITH YOUR ACTUAL DEVICE
DEV_512GB="/dev/sdb"
echo "Working with 512GB drive: $DEV_512GB"
```

### Step 2: Create Partition Table
```bash
# Create new GPT partition table (DESTROYS ALL DATA!)
sudo parted $DEV_512GB mklabel gpt

# Verify partition table created
sudo parted $DEV_512GB print
```

### Step 3: Create Development Partitions
```bash
# Create Docker partition (200GB)
sudo parted $DEV_512GB mkpart docker ext4 1MiB 200GiB

# Create Projects partition (200GB) 
sudo parted $DEV_512GB mkpart projects ext4 200GiB 400GiB

# Create Databases partition (remaining ~112GB)
sudo parted $DEV_512GB mkpart databases ext4 400GiB 100%

# Verify partitions
sudo parted $DEV_512GB print
lsblk $DEV_512GB
```

### Step 4: Format Development Partitions
```bash
# Format Docker partition
sudo mkfs.ext4 -L "docker" ${DEV_512GB}1
echo "Docker partition formatted"

# Format Projects partition  
sudo mkfs.ext4 -L "projects" ${DEV_512GB}2
echo "Projects partition formatted"

# Format Databases partition
sudo mkfs.ext4 -L "databases" ${DEV_512GB}3
echo "Databases partition formatted"

# Verify formatting
sudo blkid ${DEV_512GB}1 ${DEV_512GB}2 ${DEV_512GB}3
```

---

## 🔧 Setup 1TB External Drive for Backups

### Step 1: Identify the 1TB External Drive
```bash
# List drives to identify 1TB external (usually sdc or similar)
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,TRAN

# Look for drive with TRAN=usb
# We'll assume it's /dev/sdc - REPLACE WITH YOUR ACTUAL DEVICE  
DEV_1TB="/dev/sdc"
echo "Working with 1TB external drive: $DEV_1TB"
```

### Step 2: Create Single Backup Partition
```bash
# Create new GPT partition table (DESTROYS ALL DATA!)
sudo parted $DEV_1TB mklabel gpt

# Create single partition for backups (full drive)
sudo parted $DEV_1TB mkpart backup ext4 1MiB 100%

# Verify partition
sudo parted $DEV_1TB print
lsblk $DEV_1TB
```

### Step 3: Format Backup Partition
```bash
# Format backup partition
sudo mkfs.ext4 -L "backup" ${DEV_1TB}1
echo "Backup partition formatted"

# Verify formatting
sudo blkid ${DEV_1TB}1
```

---

## 📁 Create Mount Points

```bash
# Create mount point directories
sudo mkdir -p /opt/docker
sudo mkdir -p /mnt/projects  
sudo mkdir -p /mnt/databases
sudo mkdir -p /mnt/backup

# Set proper permissions
sudo chown $USER:$USER /mnt/projects
sudo chmod 755 /opt/docker /mnt/projects /mnt/databases /mnt/backup

echo "Mount points created"
```

---

## 🔗 Configure Automatic Mounting

### Step 1: Get UUIDs for Reliable Mounting
```bash
# Get UUIDs for all new partitions
echo "=== UUIDs for /etc/fstab ==="
sudo blkid ${DEV_512GB}1 | grep -o 'UUID="[^"]*"' | sed 's/UUID=//g'
sudo blkid ${DEV_512GB}2 | grep -o 'UUID="[^"]*"' | sed 's/UUID=//g'  
sudo blkid ${DEV_512GB}3 | grep -o 'UUID="[^"]*"' | sed 's/UUID=//g'
sudo blkid ${DEV_1TB}1 | grep -o 'UUID="[^"]*"' | sed 's/UUID=//g'

# Store UUIDs in variables for easier use
UUID_DOCKER=$(sudo blkid ${DEV_512GB}1 -s UUID -o value)
UUID_PROJECTS=$(sudo blkid ${DEV_512GB}2 -s UUID -o value)
UUID_DATABASES=$(sudo blkid ${DEV_512GB}3 -s UUID -o value)
UUID_BACKUP=$(sudo blkid ${DEV_1TB}1 -s UUID -o value)

echo "Docker UUID: $UUID_DOCKER"
echo "Projects UUID: $UUID_PROJECTS" 
echo "Databases UUID: $UUID_DATABASES"
echo "Backup UUID: $UUID_BACKUP"
```

### Step 2: Backup Current fstab
```bash
# Backup current fstab
sudo cp /etc/fstab /etc/fstab.backup.$(date +%Y%m%d_%H%M%S)
echo "fstab backed up"
```

### Step 3: Add Mount Entries to fstab
```bash
# Add entries to fstab for automatic mounting
echo "" | sudo tee -a /etc/fstab
echo "# Development and Backup drives" | sudo tee -a /etc/fstab
echo "UUID=$UUID_DOCKER /opt/docker ext4 defaults,noatime 0 2" | sudo tee -a /etc/fstab
echo "UUID=$UUID_PROJECTS /mnt/projects ext4 defaults,noatime 0 2" | sudo tee -a /etc/fstab
echo "UUID=$UUID_DATABASES /mnt/databases ext4 defaults,noatime 0 2" | sudo tee -a /etc/fstab
echo "UUID=$UUID_BACKUP /mnt/backup ext4 defaults,noatime,nofail 0 2" | sudo tee -a /etc/fstab

echo "fstab entries added"
```

### Step 4: Test Mount Configuration
```bash
# Test mount configuration without rebooting
sudo mount -a

# Check if all mounts successful
df -h | grep -E "(docker|projects|databases|backup)"

# Expected output should show all four new mounts
```

---

## 🔍 Verify Final Storage Layout

```bash
# Check complete storage layout
echo "=== Complete Storage Layout ==="
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,LABEL

# Check mounted filesystems with usage
echo "=== Mounted Filesystems ==="
df -h

# Check fstab entries
echo "=== fstab entries ==="  
cat /etc/fstab
```

Expected final layout:
```
nvme0n1 (1TB NVMe):
├─nvme0n1p1    1G  /boot/efi
├─nvme0n1p2    1G  /boot  
├─nvme0n1p3   50G  / 
├─nvme0n1p4   50G  /home
├─nvme0n1p5  800G  /mnt/photos
└─nvme0n1p6   16G  [SWAP]

sdb (512GB SSD):
├─sdb1        200G  /opt/docker
├─sdb2        200G  /mnt/projects
└─sdb3        112G  /mnt/databases

sdc (1TB External):
└─sdc1       1000G  /mnt/backup
```

---

## 🔧 Set Up Directory Structure

```bash
# Create organized directory structure
echo "Creating directory structures..."

# Docker directory structure
sudo mkdir -p /opt/docker/containers
sudo mkdir -p /opt/docker/volumes
sudo mkdir -p /opt/docker/compose-projects

# Projects directory structure
mkdir -p /mnt/projects/java
mkdir -p /mnt/projects/python
mkdir -p /mnt/projects/web
mkdir -p /mnt/projects/scripts
mkdir -p /mnt/projects/learning

# Database directory structure  
sudo mkdir -p /mnt/databases/postgresql
sudo mkdir -p /mnt/databases/mysql
sudo mkdir -p /mnt/databases/mongodb
sudo mkdir -p /mnt/databases/redis

# Backup directory structure
mkdir -p /mnt/backup/system
mkdir -p /mnt/backup/databases
mkdir -p /mnt/backup/projects
mkdir -p /mnt/backup/photos
mkdir -p /mnt/backup/docker-volumes

# Set proper ownership
sudo chown -R $USER:$USER /mnt/projects
sudo chown -R $USER:$USER /mnt/backup
sudo chown -R root:root /opt/docker
sudo chown -R $USER:$USER /mnt/databases

echo "Directory structures created"
```

---

## ⚡ Performance Optimization

```bash
# Add performance optimizations for development drives
echo "Applying performance optimizations..."

# Add scheduler optimizations for SSD
echo 'ACTION=="add|change", KERNEL=="sdb", ATTR{queue/scheduler}="mq-deadline"' | sudo tee /etc/udev/rules.d/60-ssd-scheduler.rules

# Enable TRIM for SSD
sudo systemctl enable fstrim.timer

# Check current I/O scheduler
cat /sys/block/sdb/queue/scheduler
cat /sys/block/sdc/queue/scheduler

echo "Performance optimizations applied"
```

---

## 🧪 Test Storage Setup

```bash
# Test write/read on each partition
echo "Testing storage setup..."

# Test Docker partition
echo "test" | sudo tee /opt/docker/test.txt > /dev/null
sudo rm /opt/docker/test.txt
echo "✅ Docker partition working"

# Test Projects partition
echo "test" > /mnt/projects/test.txt
rm /mnt/projects/test.txt  
echo "✅ Projects partition working"

# Test Databases partition
echo "test" | sudo tee /mnt/databases/test.txt > /dev/null
sudo rm /mnt/databases/test.txt
echo "✅ Databases partition working"

# Test Backup partition (if external drive connected)
if mountpoint -q /mnt/backup; then
    echo "test" > /mnt/backup/test.txt
    rm /mnt/backup/test.txt
    echo "✅ Backup partition working"
else
    echo "⚠️  Backup partition not mounted (external drive disconnected?)"
fi

echo "Storage setup testing complete!"
```

---

## 🎉 Final Verification

```bash
# Final summary
echo "=== FINAL STORAGE SETUP SUMMARY ==="
echo ""
echo "✅ 512GB SSD configured for development:"
echo "   - /opt/docker (200GB) - Docker containers and images"  
echo "   - /mnt/projects (200GB) - Java/Python development"
echo "   - /mnt/databases (112GB) - Database storage"
echo ""
echo "✅ 1TB External configured for backups:"
echo "   - /mnt/backup (1TB) - System and data backups"
echo ""
echo "✅ 1TB NVMe already configured:"
echo "   - / (50GB) - Ubuntu system"
echo "   - /home (50GB) - User configurations" 
echo "   - /mnt/photos (800GB) - Organized photo storage"
echo ""
echo "🔧 Ready for:"
echo "   - Docker installation and containers"
echo "   - Java/Python development environments"
echo "   - Database servers (PostgreSQL, MySQL, etc.)"
echo "   - Automated backup scripts"
echo ""

# Show final disk usage
df -h | grep -E "(nvme|sdb|sdc|docker|projects|databases|backup|photos)"
```

---

## ⚠️ Important Notes

### External Drive Handling
```bash
# The 1TB backup drive uses 'nofail' option in fstab
# This means system will boot even if external drive is disconnected
# To manually mount when reconnected:
sudo mount /mnt/backup

# To safely unmount before disconnecting:
sudo umount /mnt/backup
```

### Backup Recommendations
```bash
# Create a simple backup verification script
cat > ~/check_backups.sh << 'EOF'
#!/bin/bash
echo "=== Backup Drive Status ==="
if mountpoint -q /mnt/backup; then
    echo "✅ Backup drive mounted"
    df -h /mnt/backup
else
    echo "❌ Backup drive not mounted"
    echo "To mount: sudo mount /mnt/backup"
fi
EOF

chmod +x ~/check_backups.sh
echo "Created backup check script: ~/check_backups.sh"
```

---

## 🎯 Next Steps After Storage Setup

1. **Install Docker** (Step 8) with data directory on `/opt/docker`
2. **Set up development environments** for Java/Python in `/mnt/projects`
3. **Install databases** with data storage on `/mnt/databases` 
4. **Configure backup scripts** to use `/mnt/backup`
5. **Set up photo management tools** for `/mnt/photos`

Your storage setup is now complete and optimized for your home lab server!