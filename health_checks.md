# Health Check Endpoints Implementation Plan

## Purpose
Health check endpoints are essential for monitoring the application's status and ensuring it's running properly in production. They provide:
- Application availability monitoring
- Dependency health checking
- Performance metrics
- Automated deployment validation

## Health Check Endpoints

### 1. Basic Health Check (`/health`)
A simple endpoint to verify the application is running:

```python
@app.route('/health')
def health_check():
    """Basic health check endpoint"""
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'tkdl-downloader'
    }, 200
```

### 2. Detailed Health Check (`/health/detail`)
A more comprehensive health check that verifies dependencies:

```python
import requests
from datetime import datetime

@app.route('/health/detail')
def detailed_health_check():
    """Detailed health check including dependencies"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'tkdl-downloader',
        'checks': {}
    }
    
    # Check file system access
    try:
        download_dir = app.config.get('DOWNLOAD_DIR', './downloads')
        if os.path.exists(download_dir) and os.access(download_dir, os.W_OK):
            health_status['checks']['filesystem'] = 'healthy'
        else:
            health_status['checks']['filesystem'] = 'unhealthy'
            health_status['status'] = 'unhealthy'
    except Exception as e:
        health_status['checks']['filesystem'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Check external service connectivity (example with a simple HTTP request)
    try:
        response = requests.get('https://httpbin.org/get', timeout=5)
        if response.status_code == 200:
            health_status['checks']['httpbin'] = 'healthy'
        else:
            health_status['checks']['httpbin'] = f'unhealthy: status {response.status_code}'
            health_status['status'] = 'unhealthy'
    except Exception as e:
        health_status['checks']['httpbin'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Check if required directories exist
    try:
        if os.path.exists('templates') and os.path.exists('static'):
            health_status['checks']['templates_static'] = 'healthy'
        else:
            health_status['checks']['templates_static'] = 'unhealthy'
            health_status['status'] = 'unhealthy'
    except Exception as e:
        health_status['checks']['templates_static'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return health_status, status_code
```

### 3. Readiness Check (`/health/ready`)
Indicates if the application is ready to serve traffic:

```python
@app.route('/health/ready')
def readiness_check():
    """Readiness check - indicates if app is ready to serve traffic"""
    # Check if all required services are initialized
    if not hasattr(app, 'initialized') or not app.initialized:
        return {
            'status': 'not_ready',
            'reason': 'Application not fully initialized'
        }, 503
    
    # Check if download directory is writable
    download_dir = app.config.get('DOWNLOAD_DIR', './downloads')
    if not os.path.exists(download_dir) or not os.access(download_dir, os.W_OK):
        return {
            'status': 'not_ready',
            'reason': 'Download directory not accessible'
        }, 503
    
    return {
        'status': 'ready',
        'timestamp': datetime.utcnow().isoformat()
    }, 200
```

## Monitoring Integration

### 1. Prometheus Metrics Endpoint
For more advanced monitoring, consider adding a Prometheus metrics endpoint:

```python
# Add to requirements.txt: prometheus-client

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Metrics
download_counter = Counter('tkdl_downloads_total', 'Total number of downloads')
download_duration = Histogram('tkdl_download_duration_seconds', 'Download duration in seconds')

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}
```

### 2. Response Time Monitoring
Add timing to key endpoints:

```python
import time

@app.route('/', methods=['GET', 'POST'])
def index():
    start_time = time.time()
    
    # ... existing code ...
    
    # Record metrics
    if request.method == 'POST' and success:
        download_counter.inc()
        download_duration.observe(time.time() - start_time)
```

## Health Check Best Practices

### 1. Keep Health Checks Lightweight
- Avoid heavy operations in health checks
- Don't perform actual downloads or heavy processing
- Use cached results where appropriate

### 2. Different Levels of Health Checks
- **Liveness**: Is the process running?
- **Readiness**: Is the service ready to handle requests?
- **Startup**: Has the service completed initialization?

### 3. Security Considerations
- Don't expose sensitive information in health checks
- Consider protecting health endpoints with authentication in some environments
- Limit the amount of internal information exposed

### 4. Response Format
Use a consistent JSON format:
```json
{
  "status": "healthy|unhealthy|degraded",
  "timestamp": "ISO8601 timestamp",
  "service": "service name",
  "version": "service version",
  "checks": {
    "check_name": "healthy|unhealthy|degraded"
  }
}
```

## Implementation Steps

1. Add basic `/health` endpoint
2. Implement detailed health check with dependency verification
3. Add readiness check endpoint
4. (Optional) Implement Prometheus metrics
5. Configure monitoring systems to use these endpoints
6. Set up alerts based on health check results
7. Document the health check endpoints for operations team