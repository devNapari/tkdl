# Production Deployment Guide

## Overview
This guide provides step-by-step instructions for deploying the TikTok Downloader application in a production environment. It covers server setup, configuration, deployment, and monitoring.

## System Requirements

### Minimum Requirements
- Python 3.8 or higher
- 1 CPU core
- 512MB RAM
- 1GB disk space for application and logs
- Additional disk space for downloaded files

### Recommended Requirements
- Python 3.9 or higher
- 2 CPU cores
- 1GB RAM
- 10GB disk space (including space for downloaded files)
- Redis server for rate limiting (optional but recommended)

## Deployment Options

### 1. Linux Server Deployment (Recommended)

#### Server Setup
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv nginx redis-server -y

# Create application directory
sudo mkdir -p /var/www/tkdl
sudo chown $USER:$USER /var/www/tkdl
```

#### Application Installation
```bash
# Clone or copy application files to server
cd /var/www/tkdl

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install production dependencies
pip install gunicorn redis
```

#### Configuration
Create a `.env` file in the application directory:
```bash
# .env file
SECRET_KEY=your-very-secure-random-secret-key-here
FLASK_ENV=production
DOWNLOAD_DIR=/var/www/tkdl/downloads
LOG_LEVEL=INFO
RATELIMIT_STORAGE_URL=redis://localhost:6379/0
HOST=0.0.0.0
PORT=5000
```

#### WSGI Server Setup
Create a systemd service file for Gunicorn:
```ini
# /etc/systemd/system/tkdl.service
[Unit]
Description=TikTok Downloader Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/tkdl
EnvironmentFile=/var/www/tkdl/.env
ExecStart=/var/www/tkdl/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 wsgi:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable tkdl
sudo systemctl start tkdl
```

#### Nginx Configuration
Create an nginx configuration file:
```nginx
# /etc/nginx/sites-available/tkdl
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # Static files
    location /static/ {
        alias /var/www/tkdl/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Proxy to Flask application
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Health check endpoint (no logging)
    location = /health {
        access_log off;
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
    }
}
```

Enable the site and restart nginx:
```bash
sudo ln -s /etc/nginx/sites-available/tkdl /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 2. Docker Deployment

#### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn redis

# Copy application code
COPY . .

# Create downloads directory
RUN mkdir -p downloads

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "wsgi:app"]
```

#### Docker Compose
```yaml
version: '3.8'

services:
  redis:
    image: redis:alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

  tkdl:
    build: .
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - SECRET_KEY=your-very-secure-random-secret-key-here
      - FLASK_ENV=production
      - RATELIMIT_STORAGE_URL=redis://redis:6379/0
    volumes:
      - downloads:/app/downloads
    depends_on:
      - redis

volumes:
  redis_data:
  downloads:
```

### 3. Cloud Deployment (AWS/Google Cloud/Azure)

#### Using Platform as a Service (PaaS)
For services like Heroku, Google App Engine, or Azure App Service:

1. Create a `Procfile`:
```
web: gunicorn --bind 0.0.0.0:$PORT wsgi:app
```

2. Set environment variables in the platform's configuration

3. Deploy using the platform's deployment method

## Environment Variables

### Required Variables
| Variable | Description | Example |
|----------|-------------|---------|
| SECRET_KEY | Flask secret key | `your-random-secret-key` |
| FLASK_ENV | Environment mode | `production` |

### Optional Variables
| Variable | Description | Default |
|----------|-------------|---------|
| DOWNLOAD_DIR | Directory for downloads | `./downloads` |
| LOG_LEVEL | Logging level | `INFO` |
| RATELIMIT_STORAGE_URL | Rate limit storage | `memory://` |
| HOST | Server host | `0.0.0.0` |
| PORT | Server port | `5000` |

## Security Configuration

### 1. SSL/TLS Setup
Obtain SSL certificate using Let's Encrypt:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 2. Firewall Configuration
```bash
# Allow HTTP and HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow SSH (if needed)
sudo ufw allow ssh

# Enable firewall
sudo ufw enable
```

### 3. File Permissions
```bash
# Set proper permissions for application files
cd /var/www/tkdl
sudo chown -R www-data:www-data .
sudo chmod -R 755 .

# Secure the .env file
sudo chmod 600 .env
```

## Monitoring and Logging

### 1. Log Rotation
Create a logrotate configuration:
```bash
# /etc/logrotate.d/tkdl
/var/www/tkdl/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload tkdl
    endscript
}
```

### 2. Health Monitoring
Set up monitoring with tools like:
- Prometheus + Grafana for metrics
- ELK stack for log analysis
- Uptime monitoring services

### 3. Alerting
Configure alerts for:
- Application downtime
- High error rates
- Resource usage (CPU, memory, disk)
- Rate limit violations

## Backup and Recovery

### 1. Application Code Backup
```bash
# Create backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf /backup/tkdl_$DATE.tar.gz /var/www/tkdl
```

### 2. Configuration Backup
Regularly backup:
- `.env` file
- nginx configuration
- systemd service files

### 3. Database Backup (if applicable)
If using a database, implement regular backups.

## Scaling Considerations

### 1. Horizontal Scaling
For high-traffic deployments:
- Use multiple application instances
- Load balance with nginx or cloud load balancer
- Use shared storage for downloaded files

### 2. Vertical Scaling
- Increase server resources (CPU, RAM)
- Optimize application performance
- Use CDN for static assets

## Troubleshooting

### 1. Common Issues
- **Application not starting**: Check logs in `/var/www/tkdl/logs/`
- **Permission errors**: Verify file ownership and permissions
- **Rate limiting issues**: Check Redis connectivity

### 2. Log Locations
- Application logs: `/var/www/tkdl/logs/tkdl.log`
- Nginx access logs: `/var/log/nginx/access.log`
- Nginx error logs: `/var/log/nginx/error.log`
- Systemd logs: `journalctl -u tkdl`

### 3. Debugging Commands
```bash
# Check application status
systemctl status tkdl

# Check application logs
journalctl -u tkdl -f

# Check nginx configuration
nginx -t

# Restart services
systemctl restart tkdl
systemctl restart nginx
```

## Maintenance

### 1. Regular Tasks
- Monitor disk space usage
- Check application logs for errors
- Update dependencies regularly
- Rotate logs

### 2. Update Process
```bash
# Stop application
sudo systemctl stop tkdl

# Pull latest code
cd /var/www/tkdl
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run database migrations (if applicable)
# python migrate.py

# Start application
sudo systemctl start tkdl
```

## Performance Tuning

### 1. Gunicorn Configuration
Adjust Gunicorn settings based on server resources:
```bash
# For a 2-core server
--workers 2 --worker-class sync --worker-connections 1000

# For a 4-core server
--workers 4 --worker-class gevent --worker-connections 1000
```

### 2. Nginx Optimization
```nginx
# Enable gzip compression
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain application/json application/javascript text/css;

# Connection pooling
upstream tkdl_backend {
    server 127.0.0.1:5000;
    keepalive 32;
}
```

## Testing Deployment

### 1. Pre-deployment Checklist
- [ ] All dependencies installed
- [ ] Environment variables configured
- [ ] SSL certificate installed (if applicable)
- [ ] Firewall rules configured
- [ ] Backup procedures documented

### 2. Post-deployment Testing
- [ ] Application accessible via web browser
- [ ] Health check endpoint returns 200
- [ ] Download functionality works
- [ ] Rate limiting is functioning
- [ ] Logs are being written
- [ ] Monitoring is receiving data

## Rollback Procedure

In case of deployment issues:
1. Stop current application: `sudo systemctl stop tkdl`
2. Restore previous code backup
3. Restore previous configuration files
4. Start application: `sudo systemctl start tkdl`
5. Verify functionality

## Contact and Support

For issues with deployment, contact:
- System administrator: admin@your-domain.com
- Development team: dev@your-domain.com

## Version Information
Application Version: 1.0.0
Last Updated: 2025-08-22