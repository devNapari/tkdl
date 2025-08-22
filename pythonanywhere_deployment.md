# PythonAnywhere Deployment Guide

## Overview
This guide provides specific instructions for deploying the TikTok Downloader application on PythonAnywhere, a popular Python hosting platform. PythonAnywhere has some specific requirements and limitations that need to be considered for proper deployment.

## Prerequisites
1. A PythonAnywhere account (free or paid tier)
2. The TikTok Downloader application code
3. Basic familiarity with the PythonAnywhere interface

## PythonAnywhere Specific Considerations

### 1. WSGI Server
PythonAnywhere uses its own WSGI server infrastructure, so you don't need to install Gunicorn or Waitress. However, you'll need to configure your application to work with PythonAnywhere's WSGI system.

### 2. Static Files
PythonAnywhere can serve static files directly, but you'll need to configure this in the web app settings rather than using nginx.

### 3. Scheduled Tasks
For file cleanup and other maintenance tasks, you'll use PythonAnywhere's scheduled tasks feature instead of systemd.

### 4. Storage Limitations
- Free accounts have limited storage (512MB)
- File cleanup is especially important to prevent hitting storage limits
- Downloads directory needs careful management

## Deployment Steps

### 1. Upload Application Code
1. Log in to your PythonAnywhere account
2. Go to the "Files" tab
3. Upload your application files:
   - `tkdl.py` (main application)
   - `requirements.txt`
   - `templates/` directory
   - `static/` directory
   - Any other application files

### 2. Create Virtual Environment
1. Go to the "Consoles" tab
2. Start a new Bash console
3. Create a virtual environment:
```bash
mkvirtualenv tkdl-env --python=/usr/bin/python3.9
```
4. Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
PythonAnywhere allows you to set environment variables in several ways:

#### Option 1: Using a .env file
Create a `.env` file in your project directory:
```bash
# .env file
SECRET_KEY=your-very-secure-random-secret-key-here
FLASK_ENV=production
DOWNLOAD_DIR=/home/yourusername/downloads
LOG_LEVEL=INFO
```

#### Option 2: Using PythonAnywhere's web app configuration
1. Go to the "Web" tab
2. Select your web app
3. In the "Code" section, add environment variables in the "Environment variables" section

### 4. Modify Application for PythonAnywhere
You'll need to make some modifications to work with PythonAnywhere's WSGI system:

#### Create a WSGI file (`tkdl_wsgi.py`):
```python
import sys
import os
from dotenv import load_dotenv

# Add your project directory to the path
path = '/home/yourusername/path/to/your/project'
if path not in sys.path:
    sys.path.append(path)

# Load environment variables
env_path = os.path.join(path, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# Import your Flask application
from tkdl import app as application

if __name__ == '__main__':
    application.run()
```

### 5. Configure Web Application
1. Go to the "Web" tab
2. Click "Add a new web app"
3. Choose "Manual configuration" (not the Flask auto-setup)
4. Select Python version (3.8 or higher)
5. Configure the following settings:

#### WSGI Configuration:
- Set the WSGI file path to `/home/yourusername/path/to/your/project/tkdl_wsgi.py`

#### Static Files:
- URL: `/static/`
- Path: `/home/yourusername/path/to/your/project/static/`

#### Code Section:
- Source code: `/home/yourusername/path/to/your/project/`
- Working directory: `/home/yourusername/path/to/your/project/`

### 6. Configure Security Settings
In the "Security" section of your web app:
1. Enable "Force HTTPS" for better security
2. Configure any additional security headers if needed

### 7. Set Up File Management
Since PythonAnywhere has storage limitations, file management is crucial:

#### Create a cleanup script (`cleanup_downloads.py`):
```python
import os
import time
from datetime import datetime, timedelta

# Configuration
DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', '/home/yourusername/downloads')
MAX_AGE_HOURS = int(os.environ.get('MAX_FILE_AGE_HOURS', 1))  # 1 hour for PythonAnywhere
CLEANUP_INTERVAL = int(os.environ.get('FILE_CLEANUP_INTERVAL', 300))  # 5 minutes

def cleanup_old_files():
    """Clean up files older than MAX_AGE_HOURS"""
    if not os.path.exists(DOWNLOAD_DIR):
        print(f"Download directory {DOWNLOAD_DIR} does not exist")
        return
    
    current_time = datetime.now()
    cleaned_count = 0
    
    for filename in os.listdir(DOWNLOAD_DIR):
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        
        # Skip directories
        if os.path.isdir(filepath):
            continue
        
        try:
            # Get file modification time
            mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            file_age = current_time - mod_time
            
            # Delete files older than max_age
            if file_age > timedelta(hours=MAX_AGE_HOURS):
                os.remove(filepath)
                cleaned_count += 1
                print(f"Cleaned up: {filename}")
        except Exception as e:
            print(f"Error cleaning up {filename}: {str(e)}")
    
    print(f"Cleaned up {cleaned_count} old files")

if __name__ == '__main__':
    cleanup_old_files()
```

### 8. Set Up Scheduled Tasks
1. Go to the "Tasks" tab
2. Add a scheduled task to run the cleanup script:
```
*/5 * * * * /home/yourusername/.virtualenvs/tkdl-env/bin/python /home/yourusername/path/to/your/project/cleanup_downloads.py
```
This runs the cleanup script every 5 minutes.

### 9. Configure Logging
Modify your application to use PythonAnywhere-friendly logging:

```python
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Set up logging for PythonAnywhere"""
    # Create logs directory if it doesn't exist
    logs_dir = '/home/yourusername/logs'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Configure logging
    log_file = os.path.join(logs_dir, 'tkdl.log')
    handler = RotatingFileHandler(log_file, maxBytes=1024*1024*15, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    handler.setFormatter(formatter)
    
    logger = logging.getLogger(__name__)
    logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))
    logger.addHandler(handler)
    
    # Reduce verbosity of third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    return logger
```

## PythonAnywhere Specific Optimizations

### 1. Storage Management
- Set aggressive file cleanup (5-minute intervals, 1-hour max age)
- Monitor storage usage regularly
- Consider limiting download size

### 2. Performance Considerations
- PythonAnywhere free tier has limited resources
- Avoid heavy processing in web requests
- Use caching where possible

### 3. Bandwidth Limitations
- Free accounts have bandwidth limits
- Implement rate limiting to prevent exceeding limits
- Monitor usage in the dashboard

## Environment Variables for PythonAnywhere

### Required Variables:
```
SECRET_KEY=your-very-secure-random-secret-key-here
FLASK_ENV=production
DOWNLOAD_DIR=/home/yourusername/downloads
LOG_LEVEL=INFO
MAX_FILE_AGE_HOURS=1
FILE_CLEANUP_INTERVAL=300
```

### Optional Variables:
```
MAX_FILE_SIZE=52428800  # 50MB limit for free tier
```

## Troubleshooting Common Issues

### 1. Import Errors
- Ensure your project directory is in `sys.path`
- Verify virtual environment is activated
- Check that all dependencies are installed

### 2. Permission Errors
- Make sure all files have appropriate read permissions
- Check directory permissions for downloads folder
- Verify the web app is running as the correct user

### 3. Static File Issues
- Ensure static files path is correctly configured
- Check file permissions on static assets
- Verify URL mapping in web app settings

### 4. Storage Limit Issues
- Check current storage usage in dashboard
- Run cleanup script manually to free space
- Consider upgrading to paid account for more storage

## Monitoring and Maintenance

### 1. Log Monitoring
- Regularly check application logs in `/home/yourusername/logs/`
- Monitor PythonAnywhere's error logs
- Set up email alerts for critical errors

### 2. Storage Monitoring
- Check storage usage in PythonAnywhere dashboard
- Monitor download directory size
- Adjust cleanup schedule as needed

### 3. Performance Monitoring
- Use PythonAnywhere's built-in monitoring
- Monitor response times
- Check for timeout errors

## Scaling Considerations

### Free Tier Limitations:
- Limited storage (512MB)
- Limited bandwidth
- Limited CPU time
- No custom domain (unless upgraded)

### Paid Tier Benefits:
- More storage (1GB+ depending on tier)
- More bandwidth
- More CPU time
- Custom domain support
- Multiple web apps

## Security Considerations for PythonAnywhere

### 1. File Security
- Set appropriate permissions on all files
- Protect sensitive configuration files
- Regularly audit file access

### 2. Network Security
- Use HTTPS (enforced by PythonAnywhere)
- Limit access to sensitive endpoints
- Monitor for suspicious activity

### 3. Application Security
- Keep dependencies updated
- Implement proper input validation
- Use secure secret keys

## Backup and Recovery

### 1. Code Backup
- Use version control (Git) for your code
- Regularly push changes to remote repository
- Keep configuration files in version control (without secrets)

### 2. Data Backup
- PythonAnywhere provides some backup options
- For important data, implement your own backup solution
- Regularly download critical files

## Cost Considerations

### Free Tier:
- Suitable for low-traffic applications
- Storage and bandwidth limitations
- No custom domain

### Paid Tiers:
- Starting at $5/month for beginner tier
- More storage and bandwidth
- Custom domain support
- Better performance

## Alternative Approaches

### 1. Hybrid Approach
- Host the web application on PythonAnywhere
- Use external storage (e.g., AWS S3) for downloads
- Use external databases if needed

### 2. CDN Integration
- Use a CDN for static assets
- Reduce bandwidth usage on PythonAnywhere
- Improve global performance

## Conclusion

Deploying on PythonAnywhere requires some specific adaptations compared to a traditional server deployment, but it's a viable option for hosting your TikTok Downloader application. The key considerations are:

1. Proper configuration of the WSGI system
2. Aggressive file cleanup due to storage limitations
3. Careful management of dependencies and environment variables
4. Regular monitoring of storage and bandwidth usage
5. Implementation of scheduled tasks for maintenance

With these considerations in mind, your application should run successfully on PythonAnywhere.