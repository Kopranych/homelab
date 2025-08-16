# Step 1: Hardware Setup

## 🎯 Your Requirements
- **CPU**: AMD Ryzen with 8+ cores / 16+ threads
- **RAM**: 32GB
- **Primary Storage**: 1TB NVMe SSD (OS + applications)
- **Additional Storage**: Your existing 1TB + 512GB SSDs for backups/data
- **Network**: Gigabit Ethernet + WiFi 6 (dual connectivity options)
- **Form Factor**: Mini PC
- **Power Protection**: UPS for mini PC + WiFi router

## 🖥️ Recommended Mini PC Options

### Option 1: Beelink SER7 (Best Value)
- **CPU**: AMD Ryzen 7 7840HS (8 cores/16 threads)
- **RAM**: Expandable to 64GB DDR5
- **Storage**: M.2 NVMe slot + 2.5" SATA bay
- **Network**: Gigabit Ethernet + WiFi 6E + Bluetooth
- **Price**: ~$400-500 (barebones)
- **Perfect for**: Your requirements + room to grow

### Option 2: ASUS PN64-E1
- **CPU**: AMD Ryzen 7 PRO 6850U (8 cores/16 threads)
- **RAM**: Up to 64GB DDR5
- **Storage**: Dual M.2 slots + 2.5" SATA
- **Network**: Gigabit Ethernet + WiFi 6 + Bluetooth
- **Price**: ~$500-600 (barebones)
- **Perfect for**: Professional reliability

### Option 3: Minisforum UM790 Pro
- **CPU**: AMD Ryzen 9 7940HS (8 cores/16 threads)
- **RAM**: Up to 64GB DDR5
- **Storage**: Dual M.2 + 2.5" SATA
- **Network**: Gigabit Ethernet + WiFi 6E + Bluetooth
- **Price**: ~$600-700 (barebones)
- **Perfect for**: Maximum performance

## 🔧 Hardware Configuration

### What to Buy
1. **Mini PC** (barebones - CPU included, no RAM/storage)
2. **RAM**: 32GB DDR5 kit (2x16GB for dual channel)
3. **Primary Storage**: 1TB NVMe M.2 SSD (Gen4 for best performance)
4. **UPS**: 600-900VA UPS for mini PC + WiFi router protection

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

## 🔋 UPS (Uninterruptible Power Supply) Setup

### Why You Need UPS
- **Continue working** during power outages (15-30 minutes runtime)
- **Graceful shutdown** prevents data corruption
- **Protect equipment** from power surges and voltage fluctuations
- **Network connectivity** - router stays online during outages

### Recommended UPS Options

#### Budget Option: APC Back-UPS 600VA
- **Model**: BE600M1 or similar
- **Power**: 600VA/330W
- **Runtime**: ~15 minutes for mini PC + router
- **Price**: $70-90
- **Perfect for**: Basic protection and graceful shutdown

#### Better Option: CyberPower CP900AVR
- **Model**: 900VA/540W with AVR
- **Runtime**: ~20-30 minutes for mini PC + router
- **Features**: Automatic Voltage Regulation, LCD display
- **Price**: $100-130
- **Perfect for**: Longer runtime + voltage protection

#### Premium Option: APC Smart-UPS 750VA
- **Model**: SMC750I or similar
- **Runtime**: ~30-45 minutes
- **Features**: Network management, smart battery monitoring
- **Price**: $200-250
- **Perfect for**: Professional setup with remote monitoring

### Power Calculation
```
Mini PC: ~45W max load
WiFi Router: ~15W
Total Load: ~60W
UPS Efficiency: ~85%
Required UPS: 60W ÷ 0.85 = ~71W minimum

Recommendation: 600VA+ UPS for comfortable headroom
```

## 🔌 Final Setup

### Temporary Installation Hardware
**Needed only during OS installation:**
- **USB Keyboard**: For installation setup
- **Monitor/TV**: With HDMI input for display
- **HDMI Cable**: To connect mini PC to screen
- **USB Drive**: 8GB+ for Ubuntu installer (prepare on main PC)

**After installation, these can be disconnected - access via SSH only**

### UPS Connection
- **UPS Battery Outlets**: Mini PC + WiFi router
- **UPS Surge-Only Outlets**: Monitor (temporary), USB enclosure, other peripherals
- **USB Connection**: UPS to mini PC for shutdown communication

### Physical Placement
- **Location**: Well-ventilated area, away from heat sources
- **Orientation**: Horizontal with vents unobstructed
- **Cables**:
  - Ethernet cable to router/switch (primary connection)
  - WiFi antennas positioned for good signal (backup/mobile connection)
  - Power adapter
  - USB enclosure (if using external storage)

## 🌐 Network Connectivity Options

### Option 1: Ethernet Primary + WiFi Backup (Recommended)
**Benefits:**
- **Ethernet**: Fastest, most reliable connection (1 Gbps)
- **WiFi**: Automatic failover if Ethernet cable unplugged
- **Redundancy**: Two network paths for maximum uptime

### Option 2: WiFi Primary + Ethernet Available
**Benefits:**
- **Flexibility**: No cable required for daily operation
- **Ethernet**: Available for high-bandwidth tasks (backups, large transfers)
- **Clean setup**: Fewer cables in your setup area

### Option 3: Dual Active Connections
**Advanced Setup:**
- **Load balancing**: Distribute traffic across both connections
- **Bonding**: Combine bandwidth (requires router support)
- **Separate networks**: Ethernet for LAN, WiFi for guest/IoT network

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
| UPS | CyberPower CP900AVR | $100-130 |
| **Total** | | **$700-900** |

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