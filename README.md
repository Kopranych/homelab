# Home Lab Mini PC Server

A simple, safe setup guide for a mini PC home server focused on family photo consolidation and development projects with secure internet access.

## 🎯 Goal
Set up a mini PC at home that you can access from anywhere on the internet to:
- **Safely consolidate family photos** from old Windows drives
- Run Java/Python development projects
- Deploy personal services and applications
- Host web services with secure remote access

## 📋 Complete Setup Process

### Phase 1-4: Basic System Setup
Follow the foundational setup guides:
- [Hardware Setup](docs/01-hardware-setup.md) - Mini PC requirements and setup
- [OS Installation](docs/02-os-installation.md) - Ubuntu Server 22.04 LTS installation  
- [Basic Config + Tailscale](docs/03-basic-config-tailscale.md) - System security and remote access
- [Nextcloud Setup](docs/04-nextcloud-setup.md) - Photo verification web interface

### **Phase 5: Photo Consolidation** 📸
**The main focus**: Safely consolidate photos from old Windows drives using the **copy-first** approach.

This is the **core feature** of this homelab setup - a comprehensive, safe solution for consolidating family photos from multiple old Windows drives.

#### **🔒 Safe Copy-First Approach**
Unlike risky approaches that work directly on original drives, this workflow:
1. **📁 Copies ALL photos/videos** from old drives to `/data/incoming/` (originals never touched)
2. **🔍 Analyzes duplicates** using intelligent quality scoring (RAW > JPEG > compressed)
3. **👁️ Human verification** via Nextcloud web interface for visual confirmation
4. **✨ Removes duplicates** keeping only the best quality versions
5. **🧹 Formats old drives** ready for Phase 6 storage expansion

#### **⚡ Quick Start**
```bash
# Option 1: Python CLI (recommended for manual control)
cd scripts/media && pip3 install -r requirements.txt
screen -S photo-consolidation
python3 consolidate.py workflow                      # Complete workflow
# Or run phases individually: scan, copy, analyze, consolidate

# Option 2: Complete automation via Ansible (recommended for production)
screen -S photo-consolidation
ansible-playbook -i infra/ansible/inventory/homelab infra/ansible/photo-consolidation.yml
```

#### **📖 Complete Guide**
**👉 [05-photo-consolidation.md](docs/05-photo-consolidation.md)**

The comprehensive guide covers:
- **Prerequisites and space planning** 
- **Step-by-step workflow** with detailed explanations
- **Configuration customization** for your specific needs
- **Troubleshooting** common issues
- **Expected results** and success indicators
- **Integration** with the rest of your homelab journey

### Phase 6: Storage Setup
After photo consolidation, the formatted old drives are ready for additional storage configuration and service relocation.

## 🛡️ Safety-First Approach

### **Why This Approach is Safe**
- **🔒 Original drives never modified** - All work done on copies
- **📋 Intelligent duplicate detection** - Quality-based ranking (RAW > JPEG)
- **👁️ Human verification** - Web interface for visual confirmation
- **🔄 Fully reversible** - Can restart any phase safely
- **⚙️ Configuration-driven** - All settings in centralized config files

### **Configuration Management**
All settings controlled by:
- **`config.yml`** - Main configuration
- **`config.local.yml`** - Your personal customization
- **`environments/`** - Development vs production settings

See: [Configuration Guide](CONFIG.md)

## 📁 Repository Structure

```
homelab/
├── README.md                           # This file
├── config.yml                         # Main configuration
├── config.local.yml.example           # Template for personal settings
├── CONFIG.md                          # Configuration guide
├── CLAUDE.md                          # AI assistant guidance
├── docs/
│   ├── 01-hardware-setup.md           # Hardware requirements
│   ├── 02-os-installation.md          # OS installation guide
│   ├── 03-basic-config-tailscale.md   # Basic system setup
│   ├── 06-photo-consolidation.md      # Photo consolidation workflow
│   └── 07-storage-setup.md            # Additional storage setup
├── scripts/
│   ├── common/
│   │   └── config.sh                  # Configuration library
│   ├── media/
│   │   ├── consolidate.py             # Python CLI entry point
│   │   ├── photo_consolidator/        # Python package
│   │   └── tests/                     # Unit tests
│   └── setup/
│       └── setup_nextcloud_verification.sh # Web verification interface
├── infra/ansible/
│   ├── photo-consolidation.yml        # Complete automation
│   ├── inventory/homelab              # Server configuration
│   └── group_vars/all.yml            # Ansible variables
└── environments/
    ├── development/config.yml         # Dev environment settings
    └── production/config.yml          # Production settings
```

## 🚀 Quick Start

### 1. **Initial Setup**
```bash
# Copy and customize your configuration
cp config.local.yml.example config.local.yml
nano config.local.yml  # Add your server details, drive paths, etc.
```

### 2. **Photo Consolidation**
```bash
# Start with the safe copy operation
cd scripts/media && pip3 install -r requirements.txt
python3 consolidate.py workflow
```

### 3. **Web Verification**
- Browse to `http://your-server:8080` after Nextcloud setup
- Review photos and duplicate analysis
- Confirm consolidation decisions

## ⚡ Key Features

### **Intelligent Photo Consolidation**
- **Quality-based ranking**: RAW files > high-resolution JPEG > compressed versions
- **Folder context awareness**: Organized folders preferred over backup locations
- **Configurable scoring**: Customize quality factors for your needs
- **Space optimization**: Significant storage savings through smart deduplication

### **Maximum Safety**
- **Copy-first approach**: Never modifies original drives
- **Human verification**: Visual confirmation before any destructive operations
- **Detailed logging**: Complete audit trail of all operations
- **Rollback capability**: Can restart from any phase

### **Easy Management**
- **Web interface**: Nextcloud for browsing and verification
- **Configuration-driven**: All settings in YAML files
- **Environment-aware**: Different settings for dev/test/production
- **Both scripted and automated**: Choose manual control or full automation

## 🔗 Next Steps

1. **Complete photo consolidation** using the safe workflow
2. **Set up photo management** (Immich, PhotoPrism) on consolidated collection
3. **Configure additional storage** using formatted old drives
4. **Deploy development environment** for Java/Python projects
5. **Add personal services** and applications

## 📚 Documentation

### **Setup Phase Guides**  
- **[01-hardware-setup.md](docs/01-hardware-setup.md)** - Mini PC requirements and setup
- **[02-os-installation.md](docs/02-os-installation.md)** - Ubuntu Server installation
- **[03-basic-config-tailscale.md](docs/03-basic-config-tailscale.md)** - System security and remote access
- **[04-nextcloud-setup.md](docs/04-nextcloud-setup.md)** - Photo verification web interface
- **[05-photo-consolidation.md](docs/05-photo-consolidation.md)** - 📸 Safe photo consolidation workflow
- **[06-storage-setup.md](docs/06-storage-setup.md)** - Additional storage configuration

### **Configuration & Management**
- **[Configuration Management](CONFIG.md)** - ⚙️ Understanding the centralized config system

### **Technical Reference**
- **[CLAUDE.md](CLAUDE.md)** - AI assistant guidance for development and maintenance

---

**Focus**: This homelab setup prioritizes **safe photo consolidation** as the primary use case, with a proven copy-first approach that ensures your family photos are never at risk during the consolidation process.