# Homelab Monitoring Setup Guide

Complete guide for deploying and using the TIG (Telegraf + InfluxDB + Grafana) monitoring stack with Telegram alerting.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Telegram Bot Setup](#telegram-bot-setup)
- [Deployment](#deployment)
- [Accessing Dashboards](#accessing-dashboards)
- [Pre-configured Dashboards](#pre-configured-dashboards)
- [Alert Configuration](#alert-configuration)
- [Custom Metrics](#custom-metrics)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)

## Overview

The monitoring stack provides comprehensive visibility into your homelab infrastructure:

**Components:**
- **Telegraf** - Collects metrics from system, Docker, and custom sources
- **InfluxDB 2.x** - Stores time-series metrics data
- **Grafana** - Visualizes metrics and sends alerts
- **Telegram Bot** - Delivers alerts to your phone

**What's Monitored:**
- System metrics (CPU, RAM, disk, network, temperature)
- Docker containers (resource usage, status, restarts)
- Nextcloud services (PostgreSQL, Redis)
- Photo consolidation workflow (custom metrics)
- Service uptime and health

**Alerts Configured:**
- Disk space < 100GB on `/data`
- Memory usage > 90%
- CPU usage > 85% for 15 minutes
- Container restarts > 3 in 1 hour

## Prerequisites

1. **Docker installed** on your homelab server
2. **Ansible** installed on your laptop/control machine
3. **SSH access** to homelab server
4. **Telegram account** (for alerts)

## Quick Start

### 1. Configure Monitoring Settings

Edit `config.yml` (already configured with defaults):

```yaml
services:
  core:
    monitoring:
      enabled: true

      # Customize alert thresholds if needed
      alerts:
        disk_space_threshold_gb: 100
        memory_threshold_percent: 90
        cpu_threshold_percent: 85
```

### 2. Set Up Telegram Bot (Optional but Recommended)

See [Telegram Bot Setup](#telegram-bot-setup) section below.

### 3. Deploy Monitoring Stack

From your laptop (WSL/Linux):

```bash
cd infra/ansible
ansible-playbook -i inventory/homelab monitoring.yml
```

This takes about 3-5 minutes. The playbook will:
- ✅ Verify Docker is installed
- ✅ Create data directories
- ✅ Deploy InfluxDB, Telegraf, Grafana
- ✅ Configure datasources and dashboards
- ✅ Set up Telegram alerts
- ✅ Start collecting metrics

### 4. Access Grafana

Open your browser:
```
http://<your-server-ip>:3000
```

Default credentials:
- **Username:** admin
- **Password:** changeme_grafana (or your configured password)

**⚠️ Change the default password immediately!**

## Telegram Bot Setup

### Step 1: Create Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow prompts to choose name and username
4. Copy the bot token (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Get Your Chat ID

1. Start a conversation with your new bot (send any message)
2. Run this command in your terminal:

```bash
curl https://api.telegram.org/bot8593737609:AAEI1uN_P76unlFb0ygxLX1ZfIYt6K_wb5w/getUpdates
```

3. Look for `"chat":{"id":123456789}` in the response
4. Copy the chat ID number

### Step 3: Configure in config.local.yml

Create or edit `config.local.yml` in project root:

```yaml
services:
  core:
    monitoring:
      telegram:
        bot_token: "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        chat_id: "123456789"
```

### Step 4: Redeploy to Apply Telegram Configuration

```bash
cd infra/ansible
ansible-playbook -i inventory/homelab monitoring.yml
```

Telegram alerts are now active!

### Testing Telegram Alerts

After deployment, test the alert:

1. Open Grafana: `http://<server-ip>:3000`
2. Go to **Alerting** → **Contact points**
3. Find **telegram-homelab**
4. Click **Test** button
5. You should receive a test message on Telegram!

## Deployment

### Full Deployment

Deploy everything (Docker + Monitoring):

```bash
ansible-playbook -i inventory/homelab monitoring.yml
```

### Skip Docker Installation

If Docker is already installed:

```bash
ansible-playbook -i inventory/homelab monitoring.yml --skip-tags docker
```

### Dry Run (Check Changes)

See what would change without applying:

```bash
ansible-playbook -i inventory/homelab monitoring.yml --check --diff
```

### Deploy Only Monitoring

Skip Docker installation:

```bash
ansible-playbook -i inventory/homelab deploy-monitoring.yml
```

## Accessing Dashboards

### Grafana Web UI

**URL:** `http://<server-ip>:3000`

**Default Credentials:**
- Username: `admin`
- Password: `changeme_grafana`

### InfluxDB Web UI

**URL:** `http://<server-ip>:8086`

**Default Credentials:**
- Username: `admin`
- Password: `changeme_influx`
- Organization: `homelab`
- Bucket: `metrics`

## Pre-configured Dashboards

### 1. System Overview

**Location:** Homelab folder → "Homelab - System Overview"

**Panels:**
- CPU Usage (gauge + graph)
- Memory Usage (gauge + graph)
- Disk Usage for `/data` partition
- System Load (1m average)
- Network Traffic (all interfaces)

**Refresh:** Every 30 seconds

### 2. Docker Containers

**Location:** Homelab folder → "Homelab - Docker Containers"

**Panels:**
- Container CPU Usage (per container)
- Container Memory Usage (per container)
- Container Status Table (name, CPU, memory, status)
- Container Network Traffic

**Refresh:** Every 30 seconds

### Creating Custom Dashboards

1. Log in to Grafana
2. Click **+** → **Dashboard**
3. Add panels with InfluxDB queries
4. Save to **Homelab** folder

**Example Query (CPU usage):**
```flux
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "cpu")
  |> filter(fn: (r) => r["_field"] == "usage_idle")
  |> map(fn: (r) => ({ r with _value: 100.0 - r._value }))
```

## Alert Configuration

### Pre-configured Alerts

All alerts send notifications to Telegram (if configured).

#### 1. Low Disk Space
- **Threshold:** < 100GB free on `/data`
- **Delay:** 5 minutes
- **Severity:** Warning

#### 2. High Memory Usage
- **Threshold:** > 90% for 10 minutes
- **Severity:** Critical

#### 3. High CPU Usage
- **Threshold:** > 85% for 15 minutes
- **Severity:** Warning

#### 4. Container Restarts
- **Threshold:** > 3 restarts in 1 hour
- **Severity:** Warning

### Customizing Alert Thresholds

Edit `config.yml`:

```yaml
services:
  core:
    monitoring:
      alerts:
        disk_space_threshold_gb: 150  # Alert at 150GB instead of 100GB
        memory_threshold_percent: 85  # Alert at 85% instead of 90%
        cpu_threshold_percent: 90
        container_restart_threshold: 5
```

Then redeploy:

```bash
ansible-playbook -i inventory/homelab monitoring.yml
```

### Adding New Alerts in Grafana

1. Go to **Alerting** → **Alert rules**
2. Click **+ New alert rule**
3. Configure:
   - Query (InfluxDB query)
   - Condition (threshold)
   - Evaluation interval
   - Contact point (telegram-homelab)
4. Save

## Custom Metrics

### Photo Consolidation Metrics

A custom Python script collects photo workflow metrics every 5 minutes:

**Location:** `scripts/monitoring/photo_metrics.py`

**Metrics Collected:**
- Photos in incoming/duplicates/final directories
- Directory sizes
- Manifest file counts
- Disk space on `/data`

**View Metrics:**

In Grafana, create a query:

```flux
from(bucket: "metrics")
  |> range(start: -24h)
  |> filter(fn: (r) => r["_measurement"] == "photo_consolidation")
  |> filter(fn: (r) => r["_field"] == "photo_count")
```

### Adding Your Own Metrics

#### Option 1: Exec Plugin (for scripts)

Edit `infra/ansible/templates/telegraf.conf.j2`:

```toml
[[inputs.exec]]
  commands = ["/path/to/your/script.sh"]
  timeout = "10s"
  data_format = "influx"  # Output format
  interval = "1m"
```

Script output format (InfluxDB line protocol):

```bash
#!/bin/bash
echo "my_metric,tag=value field=123"
```

#### Option 2: HTTP Listener (for applications)

Add to Telegraf config:

```toml
[[inputs.http_listener_v2]]
  service_address = ":8186"
  paths = ["/telegraf"]
  data_format = "influx"
```

Then POST metrics from your app:

```bash
curl -X POST http://localhost:8186/telegraf \
  -d 'my_metric,source=app value=42'
```

## Maintenance

### Viewing Logs

**Grafana logs:**
```bash
docker logs monitoring-grafana
```

**InfluxDB logs:**
```bash
docker logs monitoring-influxdb
```

**Telegraf logs:**
```bash
docker logs monitoring-telegraf
```

### Restarting Services

**Restart all:**
```bash
cd ~/docker-compose/monitoring
docker compose restart
```

**Restart specific service:**
```bash
docker restart monitoring-grafana
```

### Updating Stack

Pull latest images and restart:

```bash
cd ~/docker-compose/monitoring
docker compose pull
docker compose up -d
```

### Data Retention

**Current setting:** 30 days (configured in `config.yml`)

**Change retention:**

Edit `config.yml`:

```yaml
services:
  core:
    monitoring:
      influxdb:
        retention: "90d"  # Keep data for 90 days
```

Redeploy to apply.

### Backup

**Backup Grafana dashboards and settings:**
```bash
tar -czf grafana-backup.tar.gz /data/docker/monitoring/grafana
```

**Backup InfluxDB data:**
```bash
tar -czf influxdb-backup.tar.gz /data/docker/monitoring/influxdb
```

### Restore from Backup

```bash
# Stop containers
cd ~/docker-compose/monitoring
docker compose down

# Restore data
tar -xzf grafana-backup.tar.gz -C /
tar -xzf influxdb-backup.tar.gz -C /

# Start containers
docker compose up -d
```

## Troubleshooting

### Grafana Not Accessible

**Check if running:**
```bash
docker ps | grep grafana
```

**Check logs:**
```bash
docker logs monitoring-grafana
```

**Restart:**
```bash
docker restart monitoring-grafana
```

### No Metrics in Dashboards

**Check Telegraf is collecting:**
```bash
docker logs monitoring-telegraf | tail -20
```

**Verify InfluxDB connection:**
```bash
docker exec -it monitoring-telegraf telegraf --test
```

**Check InfluxDB has data:**
```bash
docker exec -it monitoring-influxdb influx query 'from(bucket:"metrics") |> range(start:-1h) |> limit(n:10)'
```

### Telegram Alerts Not Working

**Test bot token:**
```bash
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
```

Should return bot info.

**Test in Grafana:**
1. Go to **Alerting** → **Contact points**
2. Click **telegram-homelab**
3. Click **Test**
4. Check Telegram for message

**Check Grafana logs:**
```bash
docker logs monitoring-grafana | grep -i telegram
```

### High Memory Usage

Monitoring stack uses ~500MB-1GB RAM. If too high:

**Reduce Telegraf collection interval:**

Edit `config.yml`:
```yaml
monitoring:
  telegraf:
    interval: "30s"  # Instead of 10s
```

**Reduce InfluxDB retention:**
```yaml
monitoring:
  influxdb:
    retention: "7d"  # Instead of 30d
```

### Disk Space Issues

**Check data directory sizes:**
```bash
du -sh /data/docker/monitoring/*
```

**Clean old data:**
```bash
# InfluxDB auto-cleans based on retention policy
# Force delete old data:
docker exec -it monitoring-influxdb influx delete \
  --bucket metrics \
  --start 2024-01-01T00:00:00Z \
  --stop 2024-06-01T00:00:00Z
```

## Undeployment

### Remove Containers (Keep Data)

```bash
ansible-playbook -i inventory/homelab undeploy-monitoring.yml
```

This removes containers but preserves all metrics data.

### Remove Everything (INCLUDING DATA)

**⚠️ WARNING: This deletes all historical metrics!**

```bash
ansible-playbook -i inventory/homelab undeploy-monitoring.yml \
  -e "remove_data=true remove_images=true"
```

You'll be prompted to confirm.

## Advanced Configuration

### Monitoring Additional Services

To monitor PostgreSQL, Redis, or other services, edit:

`infra/ansible/templates/telegraf.conf.j2`

Add input plugins:

```toml
[[inputs.postgresql]]
  address = "host=service-name user=postgres password=pass dbname=mydb"

[[inputs.redis]]
  servers = ["tcp://redis-service:6379"]
```

### Custom Dashboard Import

1. Download dashboard JSON from grafana.com
2. Copy to `infra/ansible/files/grafana-dashboards/`
3. Redeploy:

```bash
ansible-playbook -i inventory/homelab deploy-monitoring.yml
```

### Connecting Multiple Servers

To monitor multiple homelab servers:

1. Install Telegraf on each server
2. Configure each to send to central InfluxDB
3. Add server hostname as tag

Edit `telegraf.conf.j2`:

```toml
[global_tags]
  server = "{{ ansible_hostname }}"
```

## Useful Resources

- **Grafana Dashboards:** https://grafana.com/grafana/dashboards/
- **InfluxDB Query Language:** https://docs.influxdata.com/flux/
- **Telegraf Plugins:** https://docs.influxdata.com/telegraf/v1/plugins/
- **Telegram Bot API:** https://core.telegram.org/bots/api

## Next Steps

After deployment:

1. ✅ Change default passwords
2. ✅ Set up Telegram alerts
3. ✅ Explore pre-built dashboards
4. ✅ Test alerts (trigger a test)
5. ✅ Create custom dashboards for your needs
6. ✅ Add custom metrics from photo consolidation

Enjoy your monitoring stack!
