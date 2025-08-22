# Configuration Management Plan

## Environment Variables Needed

### Required Environment Variables
1. `SECRET_KEY` - Flask secret key for sessions and CSRF protection
2. `FLASK_ENV` - Environment mode ('development' or 'production')
3. `DOWNLOAD_DIR` - Directory for storing downloaded files (optional, defaults to './downloads')
4. `MAX_CONTENT_LENGTH` - Maximum allowed content length for uploads (optional)
5. `RATELIMIT_STORAGE_URL` - Storage URL for rate limiting (optional, defaults to memory://)

### Optional Environment Variables
1. `HOST` - Host to bind the server to (defaults to '0.0.0.0')
2. `PORT` - Port to bind the server to (defaults to 5000)
3. `LOG_LEVEL` - Logging level (defaults to 'INFO')

## Configuration Implementation Plan

### 1. Create a configuration class
- Create a `config.py` file with different configuration classes for different environments
- Use environment variables with sensible defaults
- Implement proper validation for configuration values

### 2. Update the main application file
- Load configuration from environment variables
- Use configuration values instead of hardcoded values
- Implement fallback values for optional settings

### 3. Security considerations
- Generate a strong secret key for production
- Document how to set environment variables securely
- Ensure sensitive configuration is not logged

## Sample Configuration Class Structure

```python
import os
from urllib.parse import urlparse

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    FLASK_ENV = os.environ.get('FLASK_ENV') or 'development'
    DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR') or os.path.join(os.path.dirname(__file__), 'downloads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 1024 * 1024 * 16))  # 16MB default
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL') or 'memory://'
    
    # Debug mode should be False in production
    DEBUG = FLASK_ENV == 'development'
    
    # Host and port configuration
    HOST = os.environ.get('HOST') or '0.0.0.0'
    PORT = int(os.environ.get('PORT') or 5000)
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    
    @staticmethod
    def init_app(app):
        """Initialize the application with this configuration"""
        pass

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    
    # Additional production-specific settings
    # For example, use a more secure session configuration
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
```

## Environment Variable Setup Instructions

### For Linux/macOS:
```bash
export SECRET_KEY="your-strong-secret-key-here"
export FLASK_ENV="production"
export DOWNLOAD_DIR="/var/www/tkdl/downloads"
```

### For Windows:
```cmd
set SECRET_KEY=your-strong-secret-key-here
set FLASK_ENV=production
set DOWNLOAD_DIR=C:\tkdl\downloads
```

### Using a .env file:
Create a `.env` file in the project root:
```
SECRET_KEY=your-strong-secret-key-here
FLASK_ENV=production
DOWNLOAD_DIR=./downloads
```
Then load it in your application using python-dotenv package.