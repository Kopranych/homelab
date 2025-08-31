# Phase 4: Nextcloud Setup - Photo Verification Interface

## 🎯 Goal
Install Nextcloud using Docker to provide a web interface for photo verification during the consolidation process.

## ⚠️ Prerequisites
- Ubuntu Server 22.04 LTS installed (Phase 2) ✅
- Basic configuration and Tailscale setup (Phase 3) ✅  
- Docker will be installed as part of this phase
- Remote Ansible access from laptop configured

**Important**: Installing Nextcloud on main NVMe system since old drives contain photos and cannot be used yet.

---

## 🐳 Install Docker

```bash
# Update package lists
sudo apt update

# Install prerequisites
sudo apt install -y curl wget apt-transport-https ca-certificates gnupg lsb-release

# Install Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package list
sudo apt update

# Install Docker
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

echo "✅ Docker installed - logout/login required for group membership"
```

## 🔍 Pre-Installation Verification

```bash
# Logout and login, then verify Docker is working
docker --version
docker compose version
docker ps

# Check available space on main system
df -h /data

# Ensure adequate space (need ~10GB for Nextcloud)
```

---

## 📁 Create Nextcloud Directory Structure

```bash
# Create Nextcloud directories on main system
sudo mkdir -p /data/docker/nextcloud/app
sudo mkdir -p /data/docker/nextcloud/db
sudo mkdir -p /data/docker/nextcloud/config
sudo mkdir -p /data/docker/nextcloud/data
sudo mkdir -p /data/docker/nextcloud/logs

# Set proper ownership
sudo chown -R $USER:$USER /data/docker/nextcloud

# Create docker-compose directory
mkdir -p ~/docker-compose/nextcloud
cd ~/docker-compose/nextcloud

echo "✅ Nextcloud directories created"
```

---

## 🐳 Create Docker Compose Configuration

```bash
# Create docker-compose.yml for Nextcloud
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  nextcloud-db:
    image: postgres:15
    container_name: nextcloud-db
    restart: unless-stopped
    volumes:
      - /data/docker/nextcloud/db:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=nextcloud
      - POSTGRES_USER=nextcloud
      - POSTGRES_PASSWORD=nextcloud_db_pass_2024
      - PGDATA=/var/lib/postgresql/data/pgdata
    networks:
      - nextcloud-network

  nextcloud-redis:
    image: redis:7-alpine
    container_name: nextcloud-redis
    restart: unless-stopped
    command: redis-server --requirepass redis_pass_2024
    volumes:
      - /data/docker/nextcloud/redis:/data
    networks:
      - nextcloud-network

  nextcloud-app:
    image: nextcloud:28
    container_name: nextcloud-app
    restart: unless-stopped
    ports:
      - "8080:80"
    depends_on:
      - nextcloud-db
      - nextcloud-redis
    volumes:
      - /data/docker/nextcloud/app:/var/www/html
      - /data/docker/nextcloud/config:/var/www/html/config
      - /data/docker/nextcloud/data:/var/www/html/data
      # Photo verification mounts (read-only for safety)
      - /data/incoming:/var/www/html/data/verification/incoming:ro
      - /data/duplicates:/var/www/html/data/verification/duplicates:ro
      - /data/final:/var/www/html/data/verification/final:ro
      - /data/logs:/var/www/html/data/verification/logs:ro
    environment:
      - POSTGRES_DB=nextcloud
      - POSTGRES_USER=nextcloud
      - POSTGRES_PASSWORD=nextcloud_db_pass_2024
      - POSTGRES_HOST=nextcloud-db
      - REDIS_HOST=nextcloud-redis
      - REDIS_HOST_PASSWORD=redis_pass_2024
      - NEXTCLOUD_ADMIN_PASSWORD=admin_pass_2024
      - NEXTCLOUD_ADMIN_USER=admin
      - NEXTCLOUD_TRUSTED_DOMAINS=localhost 192.168.1.100 homelab-server
      - OVERWRITEHOST=192.168.1.100:8080
      - OVERWRITEPROTOCOL=http
    networks:
      - nextcloud-network

networks:
  nextcloud-network:
    driver: bridge

EOF

echo "✅ Docker Compose configuration created"
```

---

## 🚀 Deploy Nextcloud

```bash
# Navigate to docker-compose directory
cd ~/docker-compose/nextcloud

# Pull images
docker compose pull

# Start Nextcloud stack
docker compose up -d

# Check container status
docker compose ps

# Watch logs for initial setup (optional)
echo "Watching initial setup logs (Ctrl+C to exit)..."
docker compose logs -f nextcloud-app

# Wait for setup to complete (usually 2-3 minutes)
echo "Waiting for Nextcloud to fully initialize..."
sleep 120
```

---

## 🔧 Post-Installation Configuration

```bash
# Check if Nextcloud is responding
curl -I http://localhost:8080

# Create verification folder structure inside Nextcloud
docker compose exec nextcloud-app su -s /bin/bash www-data -c "
mkdir -p /var/www/html/data/admin/files/verification
mkdir -p /var/www/html/data/admin/files/verification/incoming
mkdir -p /var/www/html/data/admin/files/verification/duplicates
mkdir -p /var/www/html/data/admin/files/verification/final
mkdir -p /var/www/html/data/admin/files/verification/logs
"

# Set proper permissions
docker compose exec nextcloud-app chown -R www-data:www-data /var/www/html/data

# Run occ commands for optimization
docker compose exec -u www-data nextcloud-app php occ db:add-missing-indices
docker compose exec -u www-data nextcloud-app php occ db:convert-filecache-bigint

echo "✅ Nextcloud post-installation configuration completed"
```

---

## 📋 Create Verification Guide

```bash
# Create verification guide that will be accessible via Nextcloud
cat > /data/VERIFICATION_GUIDE.md << 'EOF'
# Photo Consolidation Verification Guide

## 🎯 Purpose
This Nextcloud interface allows you to visually verify your photos before and after consolidation.

## 📁 Folder Structure

### `verification/incoming/`
- Contains all photos copied from your old drives
- Organized by source drive (sdb1/, sdc1/, etc.)
- **READ-ONLY** - These are your working copies

### `verification/duplicates/`
- Contains analysis reports showing duplicate groups
- Each group shows files ranked by quality
- Review these to understand which files will be kept/removed

### `verification/final/`
- Will contain your final consolidated collection
- Only appears after Phase 6 (Photo Consolidation) completes
- This is your clean, deduplicated photo library

### `verification/logs/`
- Contains detailed logs of the consolidation process
- Shows file counts, sizes, and operation summaries

## ✅ Verification Checklist

Before approving consolidation:
- [ ] Browse `incoming/` folders to confirm important photos are present
- [ ] Check folder organization makes sense for your needs
- [ ] Review duplicate analysis reports
- [ ] Verify RAW files are ranked higher than JPEG versions
- [ ] Confirm organized folders preferred over backup locations
- [ ] Check that file counts seem reasonable

## 🚨 Safety Reminders
- Original drives are NEVER modified during this process
- All work is performed on copies in `/data/incoming/`
- You can restart the process safely at any time
- This interface is for verification only - no modifications possible

## 📞 Need Help?
Check the logs in `verification/logs/` for detailed information about each phase.
EOF

echo "✅ Verification guide created"
```

---

## 🌐 Access and Test Nextcloud

```bash
# Get server IP for access
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "Nextcloud is accessible at:"
echo "  Local: http://localhost:8080"
echo "  Network: http://$SERVER_IP:8080"
echo "  Tailscale: http://$(tailscale ip -4):8080"
echo ""
echo "Default credentials:"
echo "  Username: admin"
echo "  Password: admin_pass_2024"
echo ""
echo "⚠️  Change the default password after first login!"
```

### Test Web Access
```bash
# Test web access
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080

# Expected output: 200 (success)
# If you get 200, Nextcloud is working properly
```

---

## 🔒 Security Configuration

```bash
# Create script to change default passwords
cat > ~/change-nextcloud-passwords.sh << 'EOF'
#!/bin/bash
echo "🔒 Changing Nextcloud default passwords..."

# Generate secure passwords
ADMIN_PASS=$(openssl rand -base64 32)
DB_PASS=$(openssl rand -base64 32)
REDIS_PASS=$(openssl rand -base64 32)

echo "Generated secure passwords:"
echo "Admin password: $ADMIN_PASS"
echo "Database password: $DB_PASS" 
echo "Redis password: $REDIS_PASS"

echo ""
echo "⚠️  SAVE THESE PASSWORDS SECURELY!"
echo "   Update docker-compose.yml with new passwords"
echo "   Restart containers after updating"
echo ""
EOF

chmod +x ~/change-nextcloud-passwords.sh

echo "✅ Password change script created at ~/change-nextcloud-passwords.sh"
echo "   Run this script after initial setup to secure your installation"
```

---

## 📊 Monitor Nextcloud

```bash
# Create monitoring script
cat > ~/check-nextcloud.sh << 'EOF'
#!/bin/bash
echo "=== Nextcloud Status ==="
echo ""

echo "📊 Container Status:"
cd ~/docker-compose/nextcloud && docker compose ps

echo ""
echo "💾 Storage Usage:"
df -h /data/docker/nextcloud

echo ""
echo "🌐 Web Access Test:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Nextcloud is accessible (HTTP $HTTP_CODE)"
else
    echo "❌ Nextcloud not responding (HTTP $HTTP_CODE)"
fi

echo ""
echo "📁 Verification Folders:"
if [ -d "/data/incoming" ]; then
    echo "✅ /data/incoming exists"
else
    echo "⚠️  /data/incoming not found (normal before photo copy)"
fi

if [ -d "/data/duplicates" ]; then
    echo "✅ /data/duplicates exists"  
else
    echo "⚠️  /data/duplicates not found (normal before analysis)"
fi

if [ -d "/data/final" ]; then
    echo "✅ /data/final exists"
else
    echo "⚠️  /data/final not found (normal before consolidation)"
fi
EOF

chmod +x ~/check-nextcloud.sh

echo "✅ Monitoring script created at ~/check-nextcloud.sh"
```

---

## 🧪 Test Verification Interface

```bash
# Create test directories to verify mounting works
mkdir -p /data/incoming/test
mkdir -p /data/duplicates/test
mkdir -p /data/final/test
mkdir -p /data/logs

# Create test files
echo "Test file from incoming" > /data/incoming/test/test.txt
echo "Test file from duplicates" > /data/duplicates/test/test.txt
echo "Test file from final" > /data/final/test/test.txt
echo "Test log entry" > /data/logs/test.log

# Restart Nextcloud to recognize mounts
cd ~/docker-compose/nextcloud
docker compose restart nextcloud-app

# Wait for restart
sleep 30

# Test file access
docker compose exec nextcloud-app ls -la /var/www/html/data/verification/

echo "✅ Test files created - check web interface to verify folder access"
```

---

## 📋 Installation Summary

```bash
# Final verification
echo "=== NEXTCLOUD INSTALLATION SUMMARY ==="
echo ""
echo "✅ Nextcloud Services:"
echo "   - Web Interface: http://$(hostname -I | awk '{print $1}'):8080"
echo "   - Database: MariaDB 10.11"
echo "   - Cache: Redis 7"
echo "   - Admin User: admin"
echo ""
echo "✅ Docker Containers:"
docker compose ps

echo ""
echo "✅ Storage Locations:"
echo "   - App Data: /data/docker/nextcloud/app"
echo "   - Database: /data/docker/nextcloud/db"
echo "   - User Data: /data/docker/nextcloud/data"
echo "   - Configuration: /data/docker/nextcloud/config"
echo ""
echo "✅ Verification Mounts (read-only):"
echo "   - Photos: /data/incoming → verification/incoming"
echo "   - Analysis: /data/duplicates → verification/duplicates"  
echo "   - Results: /data/final → verification/final"
echo "   - Logs: /data/logs → verification/logs"
echo ""
echo "✅ Management Scripts:"
echo "   - Status Check: ~/check-nextcloud.sh"
echo "   - Password Change: ~/change-nextcloud-passwords.sh"
echo "   - Docker Compose: ~/docker-compose/nextcloud/"
echo ""
echo "🎯 READY FOR:"
echo "   - Photo consolidation verification"
echo "   - Visual confirmation of duplicate analysis"
echo "   - Final result review"
echo ""
echo "⚠️  SECURITY REMINDERS:"
echo "   - Change default passwords using ~/change-nextcloud-passwords.sh"
echo "   - Nextcloud is only accessible on local network"
echo "   - All photo mounts are read-only for safety"
echo ""
```

---

## 🔗 Next Steps

After completing this phase:

1. **Security**: Run `~/change-nextcloud-passwords.sh` and update docker-compose.yml
2. **Access Test**: Open http://your-server-ip:8080 and log in
3. **Phase 5**: Start photo consolidation process using Ansible from laptop
4. **Verification**: Use Nextcloud interface to review each consolidation phase

**Important Notes:**
- Nextcloud runs on port 8080 (avoid conflicts with other services)
- All photo directories mounted as read-only for safety
- Interface will populate as photo consolidation phases complete
- Can be relocated to dedicated storage in Phase 6

---

**Phase 4 Complete!** ✅ 
Nextcloud is ready to provide web-based verification interface for photo consolidation.