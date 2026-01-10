# Certificate Fix - Traefik Not Using Tailscale Certificates

## Issue Summary

**Date Discovered:** 2026-01-10
**Severity:** Medium (HTTPS works but browsers show security warning)

**Symptom:**
- HTTPS works at `https://homelab.nebelung-mercat.ts.net`
- Browser shows "Not Secure" warning requiring "Advanced" click to proceed
- Certificate shows "TRAEFIK DEFAULT CERT" instead of Let's Encrypt

**Root Cause:**
The Traefik container was missing the volume mount for certificates, even though:
- ✅ Tailscale certificates exist in `/var/lib/tailscale/certs/`
- ✅ Certificates were copied to `~/docker-compose/nextcloud/certs/`
- ✅ Traefik configuration references `/certs/` directory
- ❌ But `/certs/` was not mounted into the container

## The Fix

### 1. Verify Certificate Files Exist

```bash
# Check Tailscale certificates
sudo ls -la /var/lib/tailscale/certs/
# Should show: homelab.nebelung-mercat.ts.net.crt and .key

# Check copied certificates
ls -la ~/docker-compose/nextcloud/certs/
# Should show: homelab.nebelung-mercat.ts.net.crt, .key, and dynamic.yml
```

### 2. Add Certificate Volume Mount

Edit `~/docker-compose/nextcloud/docker-compose.yml`:

**Find the Traefik service volumes section:**
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

**Add the certs mount:**
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
  - ./certs:/certs:ro  # Add this line
```

### 3. Apply the Fix

```bash
cd ~/docker-compose/nextcloud
docker compose up -d --force-recreate traefik
```

### 4. Verify the Fix

**Check certificates are in container:**
```bash
docker exec nextcloud-traefik ls -la /certs/
```

Expected output:
```
-rw-r--r-- 1 1000 1000  791 Oct 15 15:20 dynamic.yml
-rw-r--r-- 1 1000 1000 2896 Jan  9 21:51 homelab.nebelung-mercat.ts.net.crt
-rw-r--r-- 1 1000 1000  227 Jan  9 21:51 homelab.nebelung-mercat.ts.net.key
```

**Check certificate being served:**
```bash
openssl s_client -connect homelab.nebelung-mercat.ts.net:443 \
  -servername homelab.nebelung-mercat.ts.net 2>/dev/null | \
  openssl x509 -noout -text | grep -E 'Issuer:|Subject:|Not After'
```

Expected output:
```
Issuer: C = US, O = Let's Encrypt, CN = E7
Not After : Apr  9 20:53:01 2026 GMT
Subject: CN = homelab.nebelung-mercat.ts.net
```

**Before Fix:**
```
Issuer: CN = TRAEFIK DEFAULT CERT  # Self-signed, untrusted
```

**After Fix:**
```
Issuer: C = US, O = Let's Encrypt, CN = E7  # Trusted CA
```

### 5. Test in Browser

Visit: `https://homelab.nebelung-mercat.ts.net/`

✅ Should show green padlock (secure)
❌ Should NOT require "Advanced" click

## Complete Traefik Service Configuration

After the fix, the Traefik service should look like this:

```yaml
traefik:
  image: traefik:v2.10
  container_name: nextcloud-traefik
  restart: unless-stopped
  ports:
    - "80:80"
    - "443:443"
  command:
    # Docker provider
    - "--providers.docker=true"
    - "--providers.docker.exposedbydefault=false"

    # Entry points
    - "--entrypoints.web.address=:80"
    - "--entrypoints.websecure.address=:443"

    # File provider for certificates
    - "--providers.file.directory=/certs"
    - "--providers.file.watch=true"

  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - ./certs:/certs:ro  # ← This line is critical!

  networks:
    - nextcloud-network

  depends_on:
    - nextcloud-app
```

## How Traefik Certificate Loading Works

1. **File Provider** (`--providers.file.directory=/certs`):
   - Traefik watches `/certs/` directory for configuration files

2. **Dynamic Configuration** (`/certs/dynamic.yml`):
   ```yaml
   tls:
     certificates:
       - certFile: /certs/homelab.nebelung-mercat.ts.net.crt
         keyFile: /certs/homelab.nebelung-mercat.ts.net.key
   ```

3. **Certificate Files** must be accessible inside container:
   - Host: `~/docker-compose/nextcloud/certs/homelab.nebelung-mercat.ts.net.crt`
   - Container: `/certs/homelab.nebelung-mercat.ts.net.crt`
   - This requires the volume mount!

## Troubleshooting

### Certificate Still Shows as Self-Signed

1. **Check Traefik logs:**
   ```bash
   docker logs nextcloud-traefik 2>&1 | grep -i 'certificate\|tls\|error'
   ```

2. **Look for errors like:**
   ```
   Error while creating certificate store: failed to load X509 key pair
   Unable to append certificate to store
   Cannot start the provider *file.Provider: error adding file watcher: no such file or directory
   ```

3. **Common causes:**
   - `/certs/` volume not mounted
   - Certificate files have wrong permissions
   - Certificate and key don't match
   - dynamic.yml has incorrect paths

### Certificate Files Don't Exist

**If certificates are missing from `/var/lib/tailscale/certs/`:**

```bash
# Request new certificates
sudo tailscale cert homelab.nebelung-mercat.ts.net

# Copy to nextcloud directory
sudo cp /var/lib/tailscale/certs/homelab.nebelung-mercat.ts.net.* \
  ~/docker-compose/nextcloud/certs/

# Fix permissions
sudo chown $(whoami):$(whoami) ~/docker-compose/nextcloud/certs/*
```

### Certificates Expired

Tailscale certificates from Let's Encrypt expire after 90 days.

**Check expiration:**
```bash
openssl x509 -in ~/docker-compose/nextcloud/certs/homelab.nebelung-mercat.ts.net.crt \
  -noout -enddate
```

**Renew if expired:**
```bash
sudo tailscale cert homelab.nebelung-mercat.ts.net
# Then copy to certs/ directory as shown above
```

## Prevention - ✅ FIXED

### Ansible Template and Playbook Updated

**Status:** ✅ Fixed on 2026-01-10

The Nextcloud deployment has been fully updated to properly handle certificates:

#### 1. Docker Compose Template Fixed

**File:** `infra/ansible/templates/docker-compose.nextcloud.yml.j2` (lines 149-153)

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
{% if certificates_available | default(false) %}
  - {{ nextcloud.certs_dir }}:/certs:ro
{% endif %}
```

**What this does:**
- ✅ Mounts certificate directory into Traefik container
- ✅ Certificates available at `/certs/` inside container
- ℹ️  Conditional: only added when certificates exist

#### 2. Playbook Fixed

**File:** `infra/ansible/deploy-nextcloud.yml` (lines 292-315)

**Changes:**
- ✅ Removed obsolete `docker cp` commands (they fail with read-only volumes)
- ✅ Certificates now mounted automatically via docker-compose volume
- ✅ Added verification task to check certificates are present

**What this means:**
- ✅ Future deployments via Ansible will automatically mount certificates
- ✅ No manual editing of docker-compose.yml required
- ✅ Certificates will work immediately after deployment
- ✅ No `docker cp` errors during deployment

**To apply this fix to existing deployment:**
```bash
cd ~/homelab/infra/ansible
ansible-playbook -i inventory/homelab deploy-nextcloud.yml
```

This will regenerate the docker-compose.yml with the certificate volume mount included and use the fixed playbook.

## Related Issues

- This fix is unrelated to the offshore deployment
- Offshore app works fine with or without proper certificates
- This is a general Nextcloud/Traefik HTTPS configuration issue

## Documentation Updated

- ✅ This fix documented in `CERTIFICATE_FIX.md`
- ✅ Offshore deployment docs note this is not required for their app
- ℹ️  Consider adding certificate volume mount to Ansible template

## Verification Checklist

After applying the fix:

- [ ] `docker exec nextcloud-traefik ls /certs/` shows 3 files
- [ ] `docker logs nextcloud-traefik` shows no certificate errors
- [ ] `openssl s_client` shows "Issuer: Let's Encrypt"
- [ ] Browser shows green padlock at `https://homelab.nebelung-mercat.ts.net/`
- [ ] No "Not Secure" warning in browser
- [ ] Both Nextcloud and Offshore apps accessible via HTTPS

---

**Status:** ✅ Fixed on 2026-01-10
**Applied To:** Traefik container in Nextcloud stack
**Impact:** All services using Traefik now have proper HTTPS certificates
