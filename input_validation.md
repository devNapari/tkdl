# Input Validation and Sanitization Implementation Plan

## Purpose
Input validation and sanitization are critical for production applications to:
- Prevent malicious input from causing security issues
- Ensure data quality and consistency
- Protect against injection attacks
- Improve user experience with better error messages

## Current Issues
The application currently has minimal input validation, which could lead to:
- Processing of invalid or malicious URLs
- Security vulnerabilities
- Poor user experience with unclear error messages
- Resource waste on invalid requests

## Input Validation Implementation

### 1. URL Validation

#### Basic URL Format Validation:
```python
from urllib.parse import urlparse
import re

def validate_tiktok_url(url):
    """Validate that the URL is a proper TikTok URL"""
    if not url or not isinstance(url, str):
        return False, "URL is required"
    
    # Basic URL format validation
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format"
    except Exception:
        return False, "Invalid URL format"
    
    # TikTok domain validation
    allowed_domains = [
        'tiktok.com',
        'www.tiktok.com',
        'vm.tiktok.com',
        'vt.tiktok.com'
    ]
    
    if parsed.netloc not in allowed_domains:
        return False, "URL must be from TikTok"
    
    # Path validation for direct video URLs
    if parsed.netloc in ['tiktok.com', 'www.tiktok.com']:
        # Should match patterns like /@username/video/1234567891234567891
        path_pattern = r'^/@[a-zA-Z0-9_.]+/video/\d{19}$'
        if not re.match(path_pattern, parsed.path):
            return False, "Invalid TikTok video URL format"
    
    return True, None
```

#### Advanced URL Sanitization:
```python
def sanitize_url(url):
    """Sanitize and normalize URL"""
    # Remove any trailing whitespace
    url = url.strip()
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Normalize TikTok URLs
    parsed = urlparse(url)
    if parsed.netloc in ['vm.tiktok.com', 'vt.tiktok.com']:
        # These are short URLs that redirect to full URLs
        # In production, you might want to resolve these
        pass
    elif parsed.netloc == 'tiktok.com':
        # Normalize to www.tiktok.com
        url = url.replace('tiktok.com', 'www.tiktok.com')
    
    return url
```

### 2. Request Validation Decorator

#### Create a decorator for common validation:
```python
from functools import wraps
from flask import request, jsonify

def validate_download_request(f):
    """Decorator to validate download requests"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get URL from form data
        url = request.form.get('url', '').strip()
        
        # Check if URL is provided
        if not url:
            logger.warning("Empty URL provided in download request")
            return render_template('index.html', error="Please provide a TikTok video URL"), 400
        
        # Sanitize URL
        try:
            url = sanitize_url(url)
        except Exception as e:
            logger.error(f"URL sanitization failed: {str(e)}")
            return render_template('index.html', error="Invalid URL format"), 400
        
        # Validate URL
        is_valid, error_message = validate_tiktok_url(url)
        if not is_valid:
            logger.warning(f"URL validation failed: {error_message} for URL: {url}")
            return render_template('index.html', error=error_message), 400
        
        # Add sanitized URL to request for use in the function
        request.validated_url = url
        
        return f(*args, **kwargs)
    return decorated_function
```

#### Apply validation to the main endpoint:
```python
@app.route('/', methods=['GET', 'POST'])
@validate_download_request
def index():
    if request.method == 'POST':
        url = request.validated_url  # Use the validated URL
        logger.info(f"Download request received for URL: {url}")
        
        success, result, method = try_download(url)
        if success:
            logger.info(f"Download successful using {method}")
            filename = os.path.basename(result)
            return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)
        else:
            logger.error(f"Download failed: {result}")
            return render_template('index.html', error="Download failed. Please try again.")
    return render_template('index.html')
```

## Security Considerations

### 1. Prevent Directory Traversal
```python
def is_safe_filename(filename):
    """Check if filename is safe to use"""
    # Remove any path components
    filename = os.path.basename(filename)
    
    # Check for dangerous characters
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    
    # Check filename length
    if len(filename) > 255:
        return False
    
    return True
```

### 2. Content Type Validation
```python
def validate_downloaded_content(file_path):
    """Validate that downloaded content is safe"""
    # Check file extension
    allowed_extensions = ['.mp4', '.mov', '.avi']
    _, ext = os.path.splitext(file_path)
    if ext.lower() not in allowed_extensions:
        return False, "Invalid file type"
    
    # Check file size (prevent extremely large files)
    max_size = 100 * 1024 * 1024  # 100MB
    if os.path.getsize(file_path) > max_size:
        return False, "File too large"
    
    return True, None
```

### 3. Rate Limiting Integration
```python
# Combine validation with rate limiting
@app.route('/', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
@validate_download_request
def index():
    # ... implementation ...
    pass
```

## User Experience Improvements

### 1. Better Error Messages
```python
def get_user_friendly_error(error_code, technical_error):
    """Convert technical errors to user-friendly messages"""
    error_messages = {
        'invalid_url': "Please enter a valid TikTok video URL",
        'not_tiktok': "The URL must be from TikTok",
        'download_failed': "We couldn't download that video. Please try again later.",
        'file_too_large': "That video is too large to download",
        'unsupported_format': "That video format is not supported"
    }
    
    return error_messages.get(error_code, "An error occurred. Please try again.")
```

### 2. Input Validation Feedback
```html
<!-- In templates/index.html -->
<form method="post" enctype="multipart/form-data" autocomplete="off" id="downloadForm">
  <input type="text" id="urlInput" name="url" placeholder="Paste TikTok video URL" required>
  <div id="urlError" class="error-message" style="color: red; display: none;"></div>
  <!-- ... rest of form ... -->
</form>

<script>
function validateUrlInput() {
    const urlInput = document.getElementById('urlInput');
    const urlError = document.getElementById('urlError');
    const url = urlInput.value.trim();
    
    if (url && !url.match(/^https?:\/\/(www\.)?tiktok\.com\/@[\w.]+\/video\/\d+/)) {
        urlError.textContent = 'Please enter a valid TikTok video URL';
        urlError.style.display = 'block';
        return false;
    } else {
        urlError.style.display = 'none';
        return true;
    }
}

document.getElementById('urlInput').addEventListener('input', validateUrlInput);
</script>
```

## Implementation Steps

1. Create URL validation and sanitization functions
2. Implement validation decorator for download requests
3. Add directory traversal protection
4. Implement content type validation for downloaded files
5. Create user-friendly error messages
6. Add client-side validation for better user experience
7. Integrate with rate limiting
8. Test validation with various input scenarios
9. Document validation rules for future maintenance

## Testing Validation

### 1. Unit Tests
```python
def test_url_validation(self):
    """Test URL validation function"""
    # Valid URLs
    self.assertTrue(validate_tiktok_url("https://www.tiktok.com/@user/video/1234567891234567891")[0])
    
    # Invalid URLs
    self.assertFalse(validate_tiktok_url("https://youtube.com/watch?v=123")[0])
    self.assertFalse(validate_tiktok_url("not-a-url")[0])
    self.assertFalse(validate_tiktok_url("")[0])

def test_url_sanitization(self):
    """Test URL sanitization function"""
    # Test adding protocol
    self.assertEqual(sanitize_url("tiktok.com/@user/video/123"), 
                     "https://tiktok.com/@user/video/123")
```

### 2. Integration Tests
```python
def test_download_with_invalid_url(self):
    """Test that invalid URLs are rejected"""
    response = self.client.post('/', data={'url': 'invalid-url'})
    self.assertEqual(response.status_code, 400)
```

## Error Handling Integration

### 1. Log Validation Failures
```python
def validate_tiktok_url(url):
    """Validate TikTok URL with detailed logging"""
    validation_start = time.time()
    
    # ... validation logic ...
    
    validation_time = time.time() - validation_start
    logger.info(f"URL validation took {validation_time:.3f}s for URL: {url}")
    
    if not is_valid:
        logger.warning(f"URL validation failed: {error_message} for URL: {url}")
    
    return is_valid, error_message
```

## Performance Considerations

### 1. Caching Validation Results
```python
from functools import lru_cache
import time

@lru_cache(maxsize=1000)
def cached_url_validation(url):
    """Cache validation results to improve performance"""
    # Add timestamp to cache key to prevent indefinite caching
    return validate_tiktok_url(url)
```

### 2. Asynchronous Validation
For high-traffic applications, consider async validation:
```python
import asyncio

async def async_validate_url(url):
    """Asynchronously validate URL"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, validate_tiktok_url, url)
```

## Configuration Options

### 1. Environment-Based Validation Settings
```python
class Config:
    # ... other config ...
    
    # Validation settings
    MAX_URL_LENGTH = int(os.environ.get('MAX_URL_LENGTH', 2048))
    ALLOWED_DOMAINS = os.environ.get('ALLOWED_DOMAINS', 'tiktok.com,www.tiktok.com').split(',')
    MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', 100 * 1024 * 1024))  # 100MB