# WSGI Server Deployment Plan

## Current Issue
The application currently uses Flask's built-in development server (`app.run(debug=True)`) which is not suitable for production environments due to:
- Poor performance under load
- Lack of security features
- No process management capabilities
- Not designed for production traffic

## Production WSGI Server Options

### 1. Gunicorn (Recommended for Linux/Unix)
**Pros:**
- Pre-fork worker model for efficient resource usage
- Easy to configure and deploy
- Good performance and stability
- Built-in process management

**Cons:**
- Not officially supported on Windows

### 2. uWSGI
**Pros:**
- Highly configurable
- Supports multiple protocols
- Good performance
- Works on multiple platforms

**Cons:**
- More complex configuration
- Steeper learning curve

### 3. Waitress (Recommended for Windows)
**Pros:**
- Pure Python implementation
- Works well on Windows and Unix
- Easy to configure
- Good performance for moderate loads

**Cons:**
- Not as performant as Gunicorn for high loads

## Implementation Plan

### 1. Add WSGI server to requirements
For Linux/Unix deployment, add to `requirements.txt`:
```
gunicorn
```

For Windows deployment, add to `requirements.txt`:
```
waitress
```

### 2. Create a WSGI entry point
Create a `wsgi.py` file:
```python
import os
from tkdl import app

if __name__ == "__main__":
    # For development only
    app.run()
```

### 3. Update application structure
Modify `tkdl.py` to be compatible with WSGI:
- Remove the `if __name__ == '__main__':` block
- Ensure the app instance is properly exported

### 4. Deployment commands
For Gunicorn:
```bash
gunicorn --bind 0.0.0.0:5000 wsgi:app
```

For Waitress:
```bash
waitress-serve --host=0.0.0.0 --port=5000 wsgi:app
```

## Process Management

### Using systemd (Linux)
Create a systemd service file for automatic startup and management.

### Using supervisor (Cross-platform)
Use supervisor for process management and automatic restarts.

## Load Balancing and Scaling
For high-traffic deployments, consider:
1. Multiple WSGI server instances behind a load balancer
2. Using nginx as a reverse proxy
3. Implementing caching mechanisms