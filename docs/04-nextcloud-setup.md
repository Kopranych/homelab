# Phase 4: Nextcloud Setup - Photo Verification Interface

## 🎯 Goal
Install Nextcloud using Docker to provide a web interface for photo verification during the consolidation process.

## ⚠️ Prerequisites
- Ubuntu Server 22.04 LTS installed (Phase 2) ✅
- Basic configuration and Tailscale setup (Phase 3) ✅
- Docker will be installed as part of this phase
- Remote Ansible access from laptop configured

**Important**: Installing Nextcloud on main NVMe system since old drives contain photos and cannot be used yet.

### (Optional) Enable HTTPS in Tailscale Admin Console

**HTTPS is optional** - Tailscale VPN already encrypts all traffic, so HTTP over Tailscale is secure. However, HTTPS provides:
- Valid certificates for Nextcloud mobile apps (some may require HTTPS)
- Browser security indicators (no "Not Secure" warnings)
- Additional encryption layer

If you want HTTPS support:

1. Go to [Tailscale Admin Console](https://login.tailscale.com/admin)
2. Navigate to **DNS** settings
3. Click **"Enable HTTPS"** button
4. Confirm the action

This enables:
- MagicDNS hostnames (e.g., `homelab.tail1234.ts.net`)
- Automatic HTTPS certificate provisioning
- Support for `tailscale cert` command

**Note**: This is a one-time setup for your entire Tailscale network (tailnet). Once enabled, all devices can request HTTPS certificates.

**If you skip this**: You can still access Nextcloud via `http://homelab.ts.net` or `http://100.x.x.x` (Tailscale IP) - both are secure due to VPN encryption.

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
# Verify Docker is installed
docker --version
docker compose version

# Fix Docker permissions (if needed)
# Check if docker group exists
getent group docker

# If empty, create docker group and add your user
sudo groupadd docker
sudo usermod -aG docker $USER

# Set correct permissions on docker socket
sudo chown root:docker /var/run/docker.sock
sudo chmod 660 /var/run/docker.sock

# Restart Docker service
sudo systemctl restart docker

# Refresh group membership (or logout/login)
newgrp docker

# Test Docker works without sudo
docker ps

# Check available space on /home partition
df -h /home

# Ensure adequate space (need ~10-20GB for Nextcloud)
```

**Storage Strategy:**
- `/data/docker/nextcloud` - All Nextcloud app, database, and Redis data (permanent, 799GB available)
- `/data/nextcloud/files` - Your new photos/documents uploaded via Nextcloud (permanent storage)
- `/data/photo-consolidation` - Old photos verification workflow (read-only, temporary for consolidation process)

---

## 🗑️ Remove Existing Nextcloud (If Installed via Snap)

```bash
# Check if Nextcloud snap is installed
snap list | grep nextcloud

# If found, remove it
sudo snap stop nextcloud
sudo snap remove nextcloud

# Verify port 80 is now free
sudo ss -tlnp | grep -E ':(80|443|8080)'

echo "✅ Old Nextcloud removed"
```

---

## 📁 Create Nextcloud Directory Structure

```bash
# Get Tailscale hostname for configuration
TAILSCALE_HOSTNAME=$(tailscale status --json 2>/dev/null | grep -o '"DNSName":"[^"]*"' | cut -d'"' -f4 | sed 's/\.$//')
if [ -z "$TAILSCALE_HOSTNAME" ]; then
    echo "⚠️  Warning: Could not detect Tailscale hostname. Using fallback."
    TAILSCALE_HOSTNAME="homelab.tailXXXX.ts.net"
fi

echo "Detected Tailscale hostname: $TAILSCALE_HOSTNAME"
echo ""

# Create Nextcloud directories in /data partition (permanent storage)
sudo mkdir -p /data/docker/nextcloud/app
sudo mkdir -p /data/docker/nextcloud/db
sudo mkdir -p /data/docker/nextcloud/redis
# Note: config and data will be created by Nextcloud inside /app directory automatically

# Create Nextcloud user files directory in /data (permanent storage for new photos/files)
sudo mkdir -p /data/nextcloud/files

# Create photo consolidation verification directories in /data (read-only mounts)
sudo mkdir -p /data/photo-consolidation/incoming
sudo mkdir -p /data/photo-consolidation/duplicates
sudo mkdir -p /data/photo-consolidation/final
sudo mkdir -p /data/photo-consolidation/logs

# Set proper ownership - Nextcloud container runs as www-data (UID 33)
sudo chown -R 33:33 /data/docker/nextcloud/app
sudo chown -R 33:33 /data/nextcloud/files
sudo chown -R 33:33 /data/photo-consolidation

# Create docker-compose directory
mkdir -p ~/docker-compose/nextcloud
cd ~/docker-compose/nextcloud

echo "✅ Nextcloud directories created"
echo "ℹ️  All Nextcloud data in /data partition (permanent storage, 799GB available)"
echo "ℹ️  User files in /data/nextcloud/files (permanent storage for new photos)"
echo "ℹ️  Photo consolidation in /data/photo-consolidation (verification only)"
echo "ℹ️  Tailscale HTTPS will be configured: https://$TAILSCALE_HOSTNAME"
```

---

## 🐳 Create Docker Compose Configuration

**Architecture Decision:**
- **Nextcloud**: Dedicated PostgreSQL + Redis (isolated, production-like)
- **Lab apps** (Python/Java): Separate shared PostgreSQL + Redis stack (to be created later)
- **Benefits**: Independent upgrades, easier backups, no conflicts between services

```bash
# Get network configuration
LOCAL_IP=$(hostname -I | awk '{print $1}')
TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "100.x.x.x")

# Create docker-compose.yml for Nextcloud
cat > docker-compose.yml << 'EOF'
services:
  postgres-nextcloud:
    image: postgres:15-alpine
    container_name: postgres-nextcloud
    restart: unless-stopped
    volumes:
      - /data/docker/nextcloud/db:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=nextcloud
      - POSTGRES_USER=nextcloud
      - POSTGRES_PASSWORD=nextcloud_db_pass_2024
      - PGDATA=/var/lib/postgresql/data/pgdata
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nextcloud"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - nextcloud-network

  redis-nextcloud:
    image: redis:7-alpine
    container_name: redis-nextcloud
    restart: unless-stopped
    command: redis-server --requirepass redis_pass_2024
    volumes:
      - /data/docker/nextcloud/redis:/data
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    networks:
      - nextcloud-network

  nextcloud-app:
    image: nextcloud:28-apache
    container_name: nextcloud-app
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      postgres-nextcloud:
        condition: service_healthy
      redis-nextcloud:
        condition: service_healthy
    volumes:
      - /data/docker/nextcloud/app:/var/www/html
      - /data/docker/nextcloud/config:/var/www/html/config
      - /data/docker/nextcloud/data:/var/www/html/data
    environment:
      - POSTGRES_DB=nextcloud
      - POSTGRES_USER=nextcloud
      - POSTGRES_PASSWORD=nextcloud_db_pass_2024
      - POSTGRES_HOST=postgres-nextcloud
      - REDIS_HOST=redis-nextcloud
      - REDIS_HOST_PASSWORD=redis_pass_2024
      - NEXTCLOUD_ADMIN_PASSWORD=admin_pass_2024
      - NEXTCLOUD_ADMIN_USER=admin
      - NEXTCLOUD_TRUSTED_DOMAINS=localhost 192.168.8.107 homelab homelab.nebelung-mercat.ts.net 100.65.45.18
    networks:
      - nextcloud-network

networks:
  nextcloud-network:
    driver: bridge

EOF

echo "✅ Docker Compose configuration created"
echo "ℹ️  All Nextcloud data in /data partition (permanent storage)"
echo "ℹ️  Tailscale access: http://$TAILSCALE_HOSTNAME (or https:// if you enable it)"
echo "ℹ️  Local network access: http://$LOCAL_IP"
echo "ℹ️  Dedicated postgres-nextcloud and redis-nextcloud containers"
echo "ℹ️  Lab apps will use separate shared PostgreSQL/Redis stack"
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

## 🔐 (Optional) Enable Tailscale HTTPS Certificates

**This step is optional.** Skip this if you're comfortable accessing Nextcloud via HTTP over Tailscale VPN (which is already encrypted).

**Prerequisites**: Make sure you've enabled HTTPS in your Tailscale Admin Console (see Prerequisites section above).

If you want HTTPS support, request certificates for your server:

```bash
# Get your Tailscale hostname
TAILSCALE_HOSTNAME=$(tailscale status --json 2>/dev/null | grep -o '"DNSName":"[^"]*"' | cut -d'"' -f4 | sed 's/\.$//')
echo "Your Tailscale hostname: $TAILSCALE_HOSTNAME"

# Request HTTPS certificate from Tailscale
sudo tailscale cert $TAILSCALE_HOSTNAME

# This will create certificates at:
# /var/lib/tailscale/certs/$TAILSCALE_HOSTNAME.crt
# /var/lib/tailscale/certs/$TAILSCALE_HOSTNAME.key

# Verify certificates were created
echo "Verifying certificates..."
sudo ls -la /var/lib/tailscale/certs/

if [ -f "/var/lib/tailscale/certs/$TAILSCALE_HOSTNAME.crt" ]; then
    echo "✅ Tailscale HTTPS certificates obtained successfully"
    echo "ℹ️  Nextcloud will be accessible via https://$TAILSCALE_HOSTNAME"
else
    echo "❌ Certificate generation failed. Check:"
    echo "   1. HTTPS is enabled in Tailscale Admin Console"
    echo "   2. Your device is connected to Tailscale"
    echo "   3. MagicDNS is working: ping $TAILSCALE_HOSTNAME"
fi
```

**How It Works:**
- Tailscale uses Let's Encrypt to generate valid HTTPS certificates
- Certificates are automatically renewed by Tailscale
- Apache in the Nextcloud container will use these certificates when accessed via HTTPS
- HTTP access (local network) continues to work normally

**Note**: The Nextcloud container will automatically use HTTPS when accessed via the Tailscale hostname on port 443.

---

## 🔧 Post-Installation Configuration

```bash
# Check if Nextcloud is responding
curl -I http://localhost

# Wait for installation to complete (check logs if needed)
docker compose logs nextcloud-app | grep "successfully installed"

# Run occ commands for database optimization
docker compose exec -u www-data nextcloud-app php occ db:add-missing-indices
docker compose exec -u www-data nextcloud-app php occ db:convert-filecache-bigint

# Scan files to register mounted directories
docker compose exec -u www-data nextcloud-app php occ files:scan --all

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
# Get server access URLs
SERVER_IP=$(hostname -I | awk '{print $1}')
TAILSCALE_HOSTNAME=$(tailscale status --json 2>/dev/null | grep -o '"DNSName":"[^"]*"' | cut -d'"' -f4 | sed 's/\.$//')

echo "==========================================="
echo "Nextcloud Access URLs:"
echo "==========================================="
echo ""
echo "🌍 Remote Access (Tailscale - Recommended):"
echo "   http://$TAILSCALE_HOSTNAME (or https:// if you enabled HTTPS certificates)"
echo "   ✅ Works from anywhere with Tailscale"
echo "   ✅ Encrypted via Tailscale VPN tunnel"
echo "   ✅ No port forwarding needed"
echo ""
echo "🏠 Local Network Access:"
echo "   http://$SERVER_IP"
echo "   ⚠️  Only works on home network"
echo "   ⚠️  No encryption (HTTP only)"
echo ""
echo "💻 Localhost (on server):"
echo "   http://localhost"
echo ""
echo "==========================================="
echo "Default credentials:"
echo "  Username: admin"
echo "  Password: admin_pass_2024"
echo ""
echo "⚠️  IMPORTANT: Change the default password after first login!"
echo "==========================================="
```

### Test Web Access
```bash
# Test local access
echo "Testing local access..."
LOCAL_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost)
if [ "$LOCAL_STATUS" = "200" ]; then
    echo "✅ Local access working (HTTP $LOCAL_STATUS)"
else
    echo "❌ Local access failed (HTTP $LOCAL_STATUS)"
fi

# Test Tailscale HTTPS access
echo ""
echo "Testing Tailscale HTTPS access..."
TAILSCALE_STATUS=$(curl -s -k -o /dev/null -w "%{http_code}" https://$TAILSCALE_HOSTNAME)
if [ "$TAILSCALE_STATUS" = "200" ] || [ "$TAILSCALE_STATUS" = "302" ]; then
    echo "✅ Tailscale HTTPS access working (HTTP $TAILSCALE_STATUS)"
    echo "   Access your Nextcloud at: https://$TAILSCALE_HOSTNAME"
else
    echo "⚠️  Tailscale HTTPS may need configuration (HTTP $TAILSCALE_STATUS)"
fi
```

---

## 📱 Connect Nextcloud Mobile App

### iPhone/iPad Setup
1. **Install Tailscale** from the App Store
   - Log in to your Tailscale account
   - Turn on Tailscale VPN

2. **Install Nextcloud app** from the App Store

3. **Connect to Nextcloud:**
   - Open Nextcloud app
   - Tap "Log in"
   - Server URL: `https://YOUR-TAILSCALE-HOSTNAME.ts.net` (get from server: `tailscale status`)
   - Username: `admin`
   - Password: `admin_pass_2024`
   - Grant permissions when prompted

4. **✅ Benefits:**
   - Works at home AND remotely
   - Automatic HTTPS encryption
   - No configuration changes needed when traveling

### Android Setup
1. **Install Tailscale** from Google Play Store
   - Log in to your Tailscale account
   - Turn on Tailscale VPN

2. **Install Nextcloud app** from Google Play Store

3. **Connect to Nextcloud:**
   - Follow same steps as iPhone above
   - Server URL: `https://YOUR-TAILSCALE-HOSTNAME.ts.net`

### Auto-Upload Photos (Optional)
```bash
# In Nextcloud mobile app:
# 1. Go to Settings → Auto upload
# 2. Enable "Instant upload"
# 3. Choose folder: /Photos or create new folder
# 4. Enable "Upload via WiFi only" to save mobile data (or allow cellular if desired)
```

### Get Your Tailscale Hostname
Run this on your server to get the URL for mobile apps:
```bash
tailscale status --json | grep -o '"DNSName":"[^"]*"' | cut -d'"' -f4 | sed 's/\.$//'
# Example output: homelab.tail1234.ts.net
# Use: https://homelab.tail1234.ts.net
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
echo "   - Database: PostgreSQL 15"
echo "   - Cache: Redis 7"
echo "   - Admin User: admin"
echo ""
echo "✅ Docker Containers:"
docker compose ps

echo ""
echo "✅ Storage Locations (all in /data partition - permanent):"
echo "   - App Data: /data/docker/nextcloud/app"
echo "   - Database: /data/docker/nextcloud/db"
echo "   - User Data: /data/docker/nextcloud/data"
echo "   - Configuration: /data/docker/nextcloud/config"
echo "   - Redis: /data/docker/nextcloud/redis"
echo ""
echo "✅ User Files (read-write, permanent):"
echo "   - Nextcloud Files: /data/nextcloud/files → admin/files"
echo ""
echo "✅ Photo Consolidation Mounts (read-only for verification):"
echo "   - Incoming: /data/photo-consolidation/incoming"
echo "   - Duplicates: /data/photo-consolidation/duplicates"
echo "   - Final: /data/photo-consolidation/final"
echo "   - Logs: /data/photo-consolidation/logs"
echo ""
echo "✅ Remote Access:"
echo "   - Tailscale HTTPS: https://\$(tailscale status --json | grep -o '\"DNSName\":\"[^\"]*\"' | cut -d'\"' -f4 | sed 's/\.\$//')"
echo "   - Local Network: http://\$(hostname -I | awk '{print \$1}')"
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
echo "   - Nextcloud accessible via Tailscale HTTPS (secure remote access)"
echo "   - All photo mounts are read-only for safety"
echo "   - Tailscale provides zero-trust network security"
echo ""
```

---

## 🔗 Next Steps

After completing this phase:

1. **Deploy Nextcloud**: Follow the deployment steps above
2. **Test Access**:
   - Local: `http://your-server-ip`
   - Remote: `http://your-tailscale-hostname.ts.net` or `http://100.x.x.x`
3. **(Optional) Enable HTTPS**:
   - Enable HTTPS in Tailscale Admin Console (see Prerequisites)
   - Run `sudo tailscale cert $TAILSCALE_HOSTNAME`
   - Access via: `https://your-tailscale-hostname.ts.net`
4. **Security**: Run `~/change-nextcloud-passwords.sh` and update docker-compose.yml
5. **Phase 5**: Start photo consolidation process using Ansible from laptop
6. **Verification**: Use Nextcloud interface to review each consolidation phase

**Important Notes:**
- Nextcloud runs on ports 80/443 for HTTP/HTTPS access
- Tailscale provides automatic HTTPS with valid certificates
- All photo directories mounted as read-only for safety
- Interface will populate as photo consolidation phases complete
- All data stored in /data partition (799GB available)

---

**Phase 4 Complete!** ✅ 
Nextcloud is ready to provide web-based verification interface for photo consolidation.