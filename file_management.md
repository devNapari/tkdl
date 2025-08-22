# File Management and Cleanup Implementation

## Purpose
Proper file management and cleanup are essential for production applications to:
- Prevent disk space exhaustion
- Ensure security of downloaded files
- Maintain application performance
- Provide a clean user experience

## Current Issues
The application currently has minimal file management, which could lead to:
- Unbounded disk space usage
- Accumulation of old files
- Security risks from unmanaged files
- Performance degradation over time

## File Management Implementation

### 1. Download Directory Management

#### Secure Directory Setup:
```python
import os
import tempfile
from pathlib import Path

def setup_download_directory():
    """Set up and validate download directory"""
    download_dir = os.environ.get('DOWNLOAD_DIR') or os.path.join(os.path.dirname(__file__), 'downloads')
    
    # Create directory if it doesn't exist
    Path(download_dir).mkdir(parents=True, exist_ok=True)
    
    # Check permissions
    if not os.access(download_dir, os.W_OK):
        raise PermissionError(f"Download directory {download_dir} is not writable")
    
    # Set secure permissions (755 for directory)
    os.chmod(download_dir, 0o755)
    
    return download_dir
```

#### File Naming and Organization:
```python
import uuid
from datetime import datetime

def generate_safe_filename(original_filename, prefix="tkdl_"):
    """Generate a safe filename with timestamp and UUID"""
    # Get file extension
    _, ext = os.path.splitext(original_filename)
    ext = ext.lower()
    
    # Generate safe filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    safe_filename = f"{prefix}{timestamp}_{unique_id}{ext}"
    
    # Ensure filename is safe
    safe_filename = secure_filename(safe_filename)
    
    return safe_filename
```

### 2. File Cleanup Implementation

#### Automatic Cleanup with Threading:
```python
import threading
import time
from datetime import datetime, timedelta

class FileCleanupManager:
    def __init__(self, download_dir, cleanup_interval=300, max_age_hours=1):
        self.download_dir = download_dir
        self.cleanup_interval = cleanup_interval  # 300 seconds = 5 minutes
        self.max_age = timedelta(hours=max_age_hours)  # 1 hour max age
        self.running = False
        self.thread = None
    
    def start_cleanup_service(self):
        """Start the automatic cleanup service"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.thread.start()
        logger.info("File cleanup service started")
    
    def stop_cleanup_service(self):
        """Stop the automatic cleanup service"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("File cleanup service stopped")
    
    def _cleanup_loop(self):
        """Main cleanup loop"""
        while self.running:
            try:
                self.cleanup_old_files()
                time.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Error in cleanup loop: {str(e)}")
    
    def cleanup_old_files(self):
        """Clean up files older than max_age"""
        if not os.path.exists(self.download_dir):
            return
        
        current_time = datetime.now()
        cleaned_count = 0
        
        for filename in os.listdir(self.download_dir):
            filepath = os.path.join(self.download_dir, filename)
            
            # Skip directories
            if os.path.isdir(filepath):
                continue
            
            # Get file modification time
            try:
                mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                file_age = current_time - mod_time
                
                # Delete files older than max_age
                if file_age > self.max_age:
                    os.remove(filepath)
                    cleaned_count += 1
                    logger.info(f"Cleaned up old file: {filename}")
            except Exception as e:
                logger.error(f"Error cleaning up file {filename}: {str(e)}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old files")
```

#### Manual Cleanup Endpoint:
```python
@app.route('/admin/cleanup', methods=['POST'])
@limiter.exempt  # Exempt from rate limiting
def manual_cleanup():
    """Manual cleanup endpoint (should be protected)"""
    # TODO: Add authentication for admin endpoints
    try:
        cleaned_count = cleanup_manager.cleanup_old_files()
        return {
            'status': 'success',
            'cleaned_files': cleaned_count,
            'message': f'Cleaned up {cleaned_count} files'
        }, 200
    except Exception as e:
        logger.error(f"Manual cleanup failed: {str(e)}")
        return {
            'status': 'error',
            'message': 'Cleanup failed'
        }, 500
```

### 3. File Size and Type Validation

#### Downloaded File Validation:
```python
def validate_downloaded_file(filepath):
    """Validate downloaded file for security and size"""
    if not os.path.exists(filepath):
        return False, "File not found"
    
    # Check file size
    max_size = int(os.environ.get('MAX_FILE_SIZE', 100 * 1024 * 1024))  # 100MB default
    file_size = os.path.getsize(filepath)
    if file_size > max_size:
        os.remove(filepath)  # Remove oversized file
        return False, f"File too large ({file_size} bytes)"
    
    # Check file type by extension
    allowed_extensions = ['.mp4', '.mov', '.avi']
    _, ext = os.path.splitext(filepath)
    if ext.lower() not in allowed_extensions:
        os.remove(filepath)  # Remove disallowed file type
        return False, f"File type not allowed: {ext}"
    
    # Set secure permissions
    os.chmod(filepath, 0o644)
    
    return True, "File is valid"
```

### 4. Disk Space Monitoring

#### Disk Space Check:
```python
import shutil

def check_disk_space(path, min_free_mb=100):
    """Check if there's enough disk space available"""
    try:
        total, used, free = shutil.disk_usage(path)
        free_mb = free // (1024 * 1024)
        
        if free_mb < min_free_mb:
            logger.warning(f"Low disk space: {free_mb}MB free, minimum {min_free_mb}MB required")
            return False, f"Low disk space: {free_mb}MB free"
        
        return True, f"{free_mb}MB free space available"
    except Exception as e:
        logger.error(f"Error checking disk space: {str(e)}")
        return False, "Error checking disk space"
```

#### Integration with Download Process:
```python
def try_download(url, output_dir=DOWNLOAD_DIR):
    """Enhanced download function with disk space checking"""
    # Check disk space before downloading
    has_space, message = check_disk_space(output_dir)
    if not has_space:
        return False, f"Insufficient disk space: {message}", None
    
    # Try yt-dlp
    success, result = download_with_ytdlp(url, output_dir)
    if success:
        # Validate downloaded file
        is_valid, validation_message = validate_downloaded_file(result)
        if not is_valid:
            return False, validation_message, None
        
        # Find the most recent file in output_dir
        files = [os.path.join(output_dir, f) for f in os.listdir(output_dir)]
        latest_file = max(files, key=os.path.getctime)
        return True, latest_file, 'yt-dlp'
    
    # Try other download methods...
    # ... (similar validation for other methods)
```

## Security Considerations

### 1. Directory Traversal Protection
```python
def is_safe_path(basedir, path):
    """Check if path is safe to access"""
    # Resolve the absolute path
    safe_path = os.path.join(basedir, path)
    # Get the real path (resolve symlinks)
    real_path = os.path.realpath(safe_path)
    # Check if the real path starts with the base directory
    return real_path.startswith(os.path.realpath(basedir))
```

### 2. File Access Control
```python
@app.route('/downloads/<filename>')
def downloaded_file(filename):
    """Serve downloaded files with security checks"""
    # Validate filename
    if not is_safe_filename(filename):
        logger.warning(f"Unsafe filename attempt: {filename}")
        return abort(404)
    
    # Check if file exists
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    if not os.path.exists(filepath):
        logger.warning(f"File not found: {filename}")
        return abort(404)
    
    # Additional security check
    if not is_safe_path(DOWNLOAD_DIR, filename):
        logger.warning(f"Directory traversal attempt: {filename}")
        return abort(403)
    
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)
```

## Configuration Options

### Environment Variables for File Management:
```python
class Config:
    # ... other config ...
    
    # File management settings
    DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR') or os.path.join(os.path.dirname(__file__), 'downloads')
    MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', 100 * 1024 * 1024))  # 100MB
    FILE_CLEANUP_INTERVAL = int(os.environ.get('FILE_CLEANUP_INTERVAL', 300))  # 5 minutes
    MAX_FILE_AGE_HOURS = int(os.environ.get('MAX_FILE_AGE_HOURS', 1))  # 1 hour
    MIN_FREE_DISK_SPACE_MB = int(os.environ.get('MIN_FREE_DISK_SPACE_MB', 100))  # 100MB
```

## Implementation Steps

1. Create download directory management functions
2. Implement file cleanup service with automatic and manual options
3. Add file validation for downloaded content
4. Implement disk space monitoring
5. Add security measures for file access
6. Configure cleanup intervals and file age limits
7. Test file management with various scenarios
8. Document file management procedures

## Testing File Management

### 1. Unit Tests
```python
def test_file_cleanup(self):
    """Test file cleanup functionality"""
    # Create test files with different ages
    # Verify that old files are cleaned up
    # Verify that recent files are preserved

def test_disk_space_check(self):
    """Test disk space checking"""
    # Test with sufficient disk space
    # Test with insufficient disk space
```

### 2. Integration Tests
```python
def test_download_with_cleanup(self):
    """Test download process with cleanup"""
    # Perform download
    # Verify file is created
    # Wait for cleanup interval
    # Verify file is cleaned up
```

## Monitoring and Metrics

### 1. Track File Management Metrics
- Number of files cleaned up
- Disk space usage over time
- Failed download attempts due to space issues
- File validation failures

### 2. Alerting
- Set up alerts for low disk space
- Alert on file cleanup failures
- Monitor for excessive file creation rates

## Backup Considerations

For important files that should be preserved:
1. Implement selective file retention policies
2. Set up backup procedures for important files
3. Consider cloud storage integration for long-term storage

## Performance Optimization

### 1. Efficient File Operations
```python
# Use efficient file operations
def efficient_file_cleanup(download_dir, max_age):
    """More efficient file cleanup using os.scandir"""
    current_time = time.time()
    cleaned_count = 0
    
    try:
        with os.scandir(download_dir) as entries:
            for entry in entries:
                if entry.is_file():
                    # Use stat_result for efficient access
                    file_stat = entry.stat()
                    file_age = current_time - file_stat.st_mtime
                    
                    if file_age > max_age:
                        os.remove(entry.path)
                        cleaned_count += 1
    except Exception as e:
        logger.error(f"Error in efficient cleanup: {str(e)}")
    
    return cleaned_count
```

## Error Handling

### 1. Graceful Failure Handling
```python
def safe_cleanup(download_dir, max_age):
    """Cleanup with comprehensive error handling"""
    try:
        return efficient_file_cleanup(download_dir, max_age)
    except PermissionError as e:
        logger.error(f"Permission error during cleanup: {str(e)}")
        # Try to fix permissions
        try:
            os.chmod(download_dir, 0o755)
            return efficient_file_cleanup(download_dir, max_age)
        except Exception as retry_e:
            logger.error(f"Failed to retry cleanup: {str(retry_e)}")
            return 0
    except Exception as e:
        logger.error(f"Unexpected error during cleanup: {str(e)}")
        return 0
```

## Maintenance Procedures

### 1. Regular Maintenance Tasks
- Monitor disk space usage
- Check cleanup service status
- Review cleanup logs
- Adjust cleanup parameters based on usage patterns

### 2. Manual Intervention Procedures
- Force cleanup when needed
- Adjust cleanup intervals
- Handle cleanup failures
- Restore accidentally deleted files (if backups exist)