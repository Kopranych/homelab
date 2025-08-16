# Step 1: Hardware Setup

## 🎯 Your Requirements
- **CPU**: AMD Ryzen with 8+ cores / 16+ threads
- **RAM**: 32GB
- **Primary Storage**: 1TB NVMe SSD (OS + applications)
- **Additional Storage**: Your existing 1TB + 512GB SSDs for backups/data
- **Network**: Gigabit Ethernet
- **Form Factor**: Mini PC

## 🖥️ Recommended Mini PC Options

### Option 1: Beelink SER7 (Best Value)
- **CPU**: AMD Ryzen 7 7840HS (8 cores/16 threads)
- **RAM**: Expandable to 64GB DDR5
- **Storage**: M.2 NVMe slot + 2.5" SATA bay
- **Price**: ~$400-500 (barebones)
- **Perfect for**: Your requirements + room to grow

### Option 2: ASUS PN64-E1
- **CPU**: AMD Ryzen 7 PRO 6850U (8 cores/16 threads)
- **RAM**: Up to 64GB DDR5
- **Storage**: Dual M.2 slots + 2.5" SATA
- **Price**: ~$500-600 (barebones)
- **Perfect for**: Professional reliability

### Option 3: Minisforum UM790 Pro
- **CPU**: AMD Ryzen 9 7940HS (8 cores/16 threads)
- **RAM**: Up to 64GB DDR5
- **Storage**: Dual M.2 + 2.5" SATA
- **Price**: ~$600-700 (barebones)
- **Perfect for**: Maximum performance

## 🔧 Hardware Configuration

### What to Buy
1. **Mini PC** (barebones - CPU included, no RAM/storage)
2. **RAM**: 32GB DDR5 kit (2x16GB for dual channel)
3. **Primary Storage**: 1TB NVMe M.2 SSD (Gen4 for best performance)

### What You Already Have
- **512GB SSD** → Database data + Development cache (internal SATA)
- **1TB SSD** → Database backups + Photos backup + Development projects backup (external USB 3.0)

## 🏗️ Assembly Steps

### 1. Prepare Your Workspace
- Clean, static-free surface
- Small Phillips head screwdriver
- Anti-static wrist strap (recommended)

### 2. Install RAM
```
1. Power off and unplug the mini PC
2. Remove bottom cover (usually 4-6 screws)
3. Locate RAM slots (usually accessible)
4. Insert 32GB kit (2x16GB) in dual-channel slots
5. Press down until clips click into place
```

### 3. Install Primary Storage (1TB NVMe)
```
1. Locate M.2 slot (usually marked M.2_1 or similar)
2. Remove mounting screw
3. Insert NVMe SSD at 30-degree angle
4. Press down and secure with screw
```

### 4. Install Secondary Storage

#### Internal Storage Setup
```
SATA Bay: 512GB SSD (Databases + Dev Cache)
1. Connect SATA data cable to motherboard
2. Connect SATA power cable  
3. Mount 512GB SSD in 2.5" SATA bay
4. This will be mounted as /mnt/databases
```

#### External Backup Storage
```
USB 3.0: 1TB SSD (All Backups)
1. Install 1TB SSD in USB 3.0 enclosure
2. Connect to mini PC via USB 3.0
3. Use for all backup needs:
   - Database backups
   - Photos backups (full + incremental)
   - Development projects backups
   - System configuration backups
```

## 🔌 Final Setup

### Physical Placement
- **Location**: Well-ventilated area, away from heat sources
- **Orientation**: Horizontal with vents unobstructed
- **Cables**:
  - Ethernet cable to router/switch
  - Power adapter
  - USB enclosure (if using external storage)

### Initial Power-On Check
```
1. Connect power and Ethernet
2. Connect temporary monitor via HDMI
3. Connect USB keyboard
4. Power on and check BIOS/UEFI
5. Verify all components detected:
   - 32GB RAM
   - 1TB NVMe SSD
   - Additional storage
```

## 📊 Expected Performance

With your configuration:
- **CPU**: 8 cores/16 threads perfect for containers and VMs
- **RAM**: 32GB allows running many services simultaneously
- **Storage**:
  - NVMe for OS/apps (fastest)
  - Internal SSDs for active data (fast)
  - USB 3.0 for backups (sufficient for backup tasks)
- **Power**: ~25-45W under load (very efficient)

**Storage Benefits**:
- **Simplicity**: Everything active on fast NVMe drive
- **Performance**: Databases on dedicated SSD for optimal I/O
- **Safety**: External backup drive can be disconnected/rotated
- **Capacity**: 1TB for active data + 512GB for databases + 1TB for backups

## 🛒 Shopping List Example

| Item | Example Product | Price Range |
|------|-----------------|-------------|
| Mini PC | Beelink SER7 (barebones) | $400-500 |
| RAM | Crucial 32GB DDR5-4800 Kit | $120-150 |
| NVMe SSD | Samsung 980 Pro 1TB | $80-120 |
| **Total** | | **$600-770** |

*Plus your existing SSDs = Complete setup*

## ✅ Next Steps

Once hardware is assembled and boots successfully:
1. Confirm all components detected in BIOS
2. Note down the system's MAC address for network setup
3. Prepare Ubuntu Server installation media
4. Ready for **Step 2: OS Installation**

## 🔍 Troubleshooting

### Common Issues
- **No boot**: Check RAM seating
- **Storage not detected**: Verify NVMe installation
- **Overheating**: Ensure proper ventilation
- **Network issues**: Check Ethernet cable connection

---

**💡 Pro Tip**: The Beelink SER7 is currently the best value for your requirements - powerful Ryzen CPU, excellent expandability, and proven reliability in home lab setups.