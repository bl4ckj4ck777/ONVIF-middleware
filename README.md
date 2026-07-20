# ONVIF Middleware

A lightweight proxy server that sits between an NVR (Network Video Recorder) and IP cameras, translating ONVIF protocol calls into native vendor API requests and back. This enables proprietary camera features to work seamlessly over the standardized ONVIF protocol.

## Overview

Many IP cameras support ONVIF, but ONVIF itself is a limited protocol that often doesn't expose advanced vendor-specific features like PTZ presets, two-way audio, motion analytics, or proprietary recording modes. This middleware bridges that gap by:

- **Intercepting ONVIF calls** from the NVR before they reach the camera
- **Translating ONVIF requests** into native API calls specific to each camera vendor (Hikvision, Dahua, Axis, etc.)
- **Forwarding native responses** back to the NVR in proper ONVIF format
- **Handling camera-to-NVR callbacks** (such as two-way audio streams, event notifications) and translating them into valid ONVIF message formats the NVR understands

### Supported Feature Translation

| ONVIF Feature | Native Camera API |
|---|---|
| PTZ Controls | Vendor PTZ commands (absolute/relative positioning, presets) |
| Two-Way Audio | Vendor audio streaming APIs |
| Snapshot/Still Images | Vendor snapshot endpoints |
| Event Subscription | Vendor event/notification APIs |
| Device Management | Vendor device info/configuration APIs |
| Media Streaming | Vendor RTSP/streaming endpoints |

## Architecture

```
┌─────────┐         ONVIF (SOAP/HTTP)         ┌──────────────────┐         Native API         ┌──────────┐
│    NVR  │ ◄────────────────────────────────► │  ONVIF Middleware  ◄──────────────────────────► │  Camera  │
│         │                                    │   (Raspberry Pi)   │                            │          │
└─────────┘                                    └──────────────────┘                            └──────────┘
```

The middleware runs on a lightweight device (such as a Raspberry Pi) on the same network as the cameras. The NVR communicates with the middleware as if it were the camera, and the middleware communicates with the actual camera using its native protocol.

---

## Raspberry Pi Deployment Framework

This section outlines how to build and deploy the ONVIF middleware service on a Raspberry Pi.

### 1. Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| Model | Raspberry Pi 3 Model B+ | Raspberry Pi 4 (4GB+) or Pi 5 |
| Storage | 16GB microSD (Class 10) | 32GB+ microSD (A1 rated) |
| Power | Official Pi 3 power supply | Official Pi 4/5 power supply |
| Cooling | Passive heatsink | Heatsink + fan |

### 2. Operating System Setup

```bash
# Flash Raspberry Pi OS Lite (headless, minimal overhead)
# Download from: https://www.raspberrypi.com/software/operating-systems/

# Enable required interfaces
sudo raspi-config
#   → Interface Options → SSH (enable for remote management)
#   → Interface Options → Camera (if using Pi camera module)
#   → Advanced Options → Expand Filesystem

# Update the system
sudo apt update && sudo apt upgrade -y
```

### 3. Runtime Dependencies

```bash
# Install Python and build tools
sudo apt install -y python3 python3-pip python3-venv

# Install network tools for debugging
sudo apt install -y netcat-traditional iputils-ping curl soapclient

# Optional: Docker support (alternative deployment method, see §6)
# sudo apt install -y docker.io docker-compose
```

### 4. Service Structure

Organize the middleware on the Pi as follows:

```
/opt/onvif-middleware/          # Installation directory
├── bin/
│   └── onvif-middleware        # Main service executable
├── config/
│   ├── middleware.yaml         # Middleware configuration
│   └── cameras/                # Per-camera configuration files
│       ├── camera01.yaml
│       └── camera02.yaml
├── logs/
│   └── middleware.log          # Runtime logs
├── lib/                        # Application code
│   ├── __init__.py
│   ├── server.py               # ONVIF server (listens for NVR requests)
│   ├── translator.py           # ONVIF ↔ Native API translation layer
│   ├── cameras/                # Vendor-specific adapters
│   │   ├── base.py
│   │   ├── hikvision.py
│   │   ├── dahua.py
│   │   ├── axis.py
│   │   └── onvif_native.py
│   └── audio/                  # Two-way audio handling
│       └── audio_bridge.py
└── scripts/
    ├── setup.sh                # Initial setup script
    └── health-check.sh         # Periodic health monitoring
```

### 5. Systemd Service Configuration

Create a systemd service for automatic start and restart:

```ini
# /etc/systemd/system/onvif-middleware.service
[Unit]
Description=ONVIF Middleware Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/onvif-middleware
ExecStart=/opt/onvif-middleware/bin/onvif-middleware --config /opt/onvif-middleware/config/middleware.yaml
Restart=on-failure
RestartSec=5
StandardOutput=append:/opt/onvif-middleware/logs/middleware.log
StandardError=append:/opt/onvif-middleware/logs/middleware.log

# Security hardening
ProtectSystem=full
PrivateTmp=true
NoNewPrivileges=true
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

Enable and manage the service:

```bash
# Enable automatic start on boot
sudo systemctl enable onvif-middleware

# Start the service
sudo systemctl start onvif-middleware

# Check status
sudo systemctl status onvif-middleware

# View live logs
sudo journalctl -u onvif-middleware -f

# Restart after configuration changes
sudo systemctl restart onvif-middleware
```

### 6. Docker Deployment (Alternative)

For containerized deployment on the Raspberry Pi:

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["python", "bin/onvif-middleware", "--config", "/app/config/middleware.yaml"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  onvif-middleware:
    build: .
    container_name: onvif-middleware
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
    environment:
      - LOG_LEVEL=info
      - TZ=America/New_York
    networks:
      - onvif-network

networks:
  onvif-network:
    driver: bridge
```

```bash
# Build and start
docker compose up -d

# Monitor
docker compose logs -f onvif-middleware
```

### 7. Network Configuration

The middleware must be reachable by both the NVR and the cameras. Configure networking appropriately:

```bash
# Set a static IP (optional but recommended for the Pi)
sudo nano /etc/dhcpcd.conf

# Add:
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1

# Ensure firewall allows ONVIF traffic (typically port 80/443 or custom)
sudo ufw allow 8080/tcp
sudo ufw enable
```

**NVR Configuration:** In the NVR's camera setup, add the camera using the Raspberry Pi's IP address and the middleware's listening port instead of the camera's actual IP.

### 8. Configuration Example

```yaml
# config/middleware.yaml

server:
  host: "0.0.0.0"
  port: 8080
  ssl: false
  timeout: 30

cameras:
  camera01:
    ip: "192.168.1.20"
    port: 80
    vendor: hikvision
    username: "admin"
    password_env: "HIKVISION_CAM_01_PASS"
    onvif_port: 8080          # Port the middleware listens on for this camera
    native_port: 80            # Camera's native API port
    features:
      ptz: true
      audio: true
      snapshots: true

  camera02:
    ip: "192.168.1.21"
    port: 80
    vendor: dahua
    username: "admin"
    password_env: "DAHUA_CAM_02_PASS"
    onvif_port: 8081
    native_port: 8000
    features:
      ptz: true
      audio: false
      snapshots: true
```

### 9. Monitoring and Maintenance

```bash
# Health check script (run periodically via cron)
#!/bin/bash
# scripts/health-check.sh

MIDDLEWARE_URL="http://localhost:8080/onvif/device"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$MIDDLEWARE_URL")

if [ "$RESPONSE" != "200" ]; then
    echo "$(date): Middleware unhealthy (HTTP $RESPONSE) - restarting" >> /opt/onvif-middleware/logs/health.log
    sudo systemctl restart onvif-middleware
fi

# Add to crontab (check every 5 minutes)
# crontab -e
# */5 * * * * /opt/onvif-middleware/scripts/health-check.sh
```

### 10. Resource Management

The Raspberry Pi has limited resources. Keep the middleware lightweight:

| Metric | Target | Monitoring Command |
|---|---|---|
| CPU Usage | < 30% (idle) | `top` or `htop` |
| Memory Usage | < 500MB | `free -m` |
| Disk I/O | Minimal | `iostat` |
| Log Size | < 100MB | `du -sh /opt/onvif-middleware/logs/` |

Configure log rotation:

```bash
# /etc/logrotate.d/onvif-middleware
/opt/onvif-middleware/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    size 50M
    copytruncate
}
```

### 11. Power and Reliability Considerations

```bash
# Enable watchdog for automatic recovery
sudo apt install -y watchdog
sudo systemctl enable watchdog
sudo systemctl start watchdog

# Configure /etc/watchdog.conf
# max-load-1 = 24
# watchdog-device = /dev/watchdog

# Use a UPS HAT for clean shutdowns (optional but recommended)
# Examples: Pi-UPS HAT, Waveshare UPS
```

---

## Development

### Adding a New Camera Vendor

1. Create a new adapter in `lib/cameras/<vendor>.py`
2. Extend the base camera class implementing:
   - `get_device_info()` — Map vendor device info to ONVIF DeviceInfo
   - `ptz_control()` — Translate ONVZ PTZ commands to vendor PTZ API
   - `get_stream_uri()` — Return vendor-specific RTSP stream URL
   - `subscribe_events()` — Handle ONVIF event subscriptions via vendor API
3. Register the vendor in the middleware's camera factory

### Testing

```bash
# Use onvif device manager tools for testing
# https://www.onvif.org/profiles/tools/

# Simulate NVR requests
curl -X POST http://localhost:8080/onvif/device -d @test_requests/get_device_info.xml

# Verify camera connectivity
python -c "from lib.cameras import factory; factory.create('hikvision', {...})"
```

---

## License

[Add your license here]
