# Homelab Ansible - Changelog

## [2026-01-10] - Certificate Volume Mount Fix

### Fixed
- **Missing certificate volume mount in Traefik** - The Nextcloud docker-compose template was missing the volume mount for Tailscale certificates, causing Traefik to fall back to self-signed certificates.
- **Playbook docker cp commands failing** - Removed obsolete `docker cp` commands that tried to copy certificates into the container, which failed because the volume is mounted read-only.

### Changed
- Updated `templates/docker-compose.nextcloud.yml.j2` (lines 149-153):
  - Added conditional certificate volume mount: `{{ nextcloud.certs_dir }}:/certs:ro`
  - Mount is only added when `certificates_available` is true
  - Prevents "Not Secure" warnings in browsers

- Updated `deploy-nextcloud.yml` (lines 292-315):
  - Removed "Copy certificates into Traefik container" block (was using `docker cp`)
  - Replaced with simple verification task
  - Certificates are now automatically mounted via volume

### Files Modified
- `infra/ansible/templates/docker-compose.nextcloud.yml.j2`
- `infra/ansible/deploy-nextcloud.yml`

### Impact
- ✅ Future Nextcloud deployments will automatically mount certificates
- ✅ HTTPS will work with trusted Let's Encrypt certificates immediately
- ✅ No manual docker-compose.yml editing required after deployment

### Testing
To verify the fix works on new deployments:
```bash
cd ~/homelab/infra/ansible
ansible-playbook -i inventory/homelab deploy-nextcloud.yml
```

Then check:
```bash
# Certificates should be in container
docker exec nextcloud-traefik ls -la /certs/

# Certificate should be from Let's Encrypt
openssl s_client -connect homelab.nebelung-mercat.ts.net:443 \
  -servername homelab.nebelung-mercat.ts.net 2>/dev/null | \
  openssl x509 -noout -issuer
# Should show: Issuer: C = US, O = Let's Encrypt
```

### Documentation Added
- `CERTIFICATE_FIX.md` - Complete troubleshooting guide for certificate issues
- This changelog entry

### Related Issues
- Issue discovered during offshore job alerts deployment
- Root cause: template bug from initial Nextcloud setup
- No changes needed to offshore deployment itself

---

## Template for Future Changes

### [YYYY-MM-DD] - Brief Description

#### Added
- New features or files

#### Changed
- Modifications to existing functionality

#### Fixed
- Bug fixes

#### Removed
- Deprecated features or files

#### Security
- Security-related changes
