# Safe Photo Consolidation - Ansible Automation

Complete automation for the **copy-first, process-later** photo consolidation approach using centralized configuration.

## Safe Workflow Architecture

**Copy-First Approach:**
- **Phase 1**: Copy all media files from old drives (originals never touched)
- **Phase 2**: Analyze duplicates in copied files only
- **Phase 3**: Human verification via Nextcloud web interface  
- **Phase 4**: Remove duplicates from copied files (originals still safe)
- **Phase 5**: Format original drives for reuse

**Clean Separation:**
- **Ansible**: Orchestration, safety checks, environment management
- **Scripts**: Focused logic using centralized configuration
- **Configuration**: Single source of truth in `../../config.yml`

## Quick Start

1. **Configure your setup**:
   ```bash
   # Copy and customize local configuration (from project root)
   cp config.local.yml.example config.local.yml
   nano config.local.yml
   
   # Edit inventory with your server details
   nano inventory/homelab
   ```

2. **Test connectivity**:
   ```bash
   ansible -i inventory/homelab homelab -m ping
   ```

3. **Run complete safe workflow**:
   ```bash
   # Recommended: Use screen for long-running ansible operations
   screen -S photo-consolidation
   
   # Complete automated safe consolidation
   ansible-playbook -i inventory/homelab photo-consolidation.yml
   
   # Detach: Ctrl+A, then D
   # Reattach: screen -r photo-consolidation
   ```

## What This Achieves

✅ **All unique photos preserved** - SHA256 hash verification ensures no data loss  
✅ **Highest quality versions kept** - Intelligent quality scoring (RAW > high-res JPEG > compressed)  
✅ **Structured organization** - Preserves original folder structure or creates organized layout  
✅ **Storage optimization** - Eliminates duplicates, significant space savings  
✅ **Safe and verifiable** - Multiple safety checks, dry-run mode, detailed logging  
✅ **Photos AND videos** - Processes all common media formats  
✅ **Source drive copying** - Safely copies from source drives to target  
✅ **Read-only operation** - Original drives remain untouched until you decide  

## Process Overview

1. **Prerequisites Check** - Verifies drives, space, tools
2. **Discovery** - Creates SHA256 manifests of all media files
3. **Quality Analysis** - Scores each file for intelligent duplicate selection
4. **Duplicate Detection** - Groups duplicates and ranks by quality
5. **Safe Consolidation** - Copies best version of each file
6. **Verification** - Generates comprehensive report

## Configuration Options

```yaml
# In group_vars/all.yml
dry_run: true                    # Safe testing mode
preserve_structure: true         # Keep folder structure
source_drives: ["/media/sdb1"]   # Your source drives
target_base: "/data"             # Destination location
```

## Safety Features

- **Dry run mode** - Test everything before execution
- **Space verification** - Ensures adequate target space
- **Hash verification** - SHA256 checksums prevent corruption
- **Quality-based selection** - Keeps best version of duplicates
- **Read-only sources** - Original drives never modified
- **Detailed logging** - Complete audit trail
- **Incremental execution** - Can re-run safely if interrupted

## Replacing Current Scripts

This single playbook replaces:
- `discover_media.sh` → Discovery phase
- `quality_analyzer.sh` → Quality analysis phase
- `analyze_duplicates.sh` → Duplicate detection phase  
- `copy_media.sh` → Media copying phase
- `safe_remove.sh` → Smart consolidation phase

## Output Structure

```
/data/
├── logs/           # Detailed execution logs
├── manifests/      # SHA256 hash catalogs
├── duplicates/     # Duplicate analysis results
├── final/          # Consolidated media collection
└── backup/         # Safety backups (if needed)
```

## Troubleshooting

**Connection issues**: Check inventory file and SSH access  
**Permission errors**: Ensure target directories are writable  
**Space errors**: Verify adequate free space on target drive  
**Missing tools**: Playbook installs required packages automatically  

## Extending

Add new phases by including additional tasks:
- Metadata extraction
- Date-based organization  
- Thumbnail generation
- Backup automation