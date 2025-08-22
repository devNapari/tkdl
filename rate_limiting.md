# Rate Limiting Implementation Plan

## Purpose
Rate limiting is essential for production applications to:
- Prevent abuse and denial of service attacks
- Ensure fair usage for all users
- Protect server resources
- Maintain application performance and availability

## Rate Limiting Options

### 1. Flask-Limiter (Recommended)
A Flask extension that provides rate limiting capabilities:

**Benefits:**
- Easy integration with Flask applications
- Multiple storage backends (memory, Redis, etc.)
- Flexible rate limiting strategies
- Built-in decorators for easy implementation

**Installation:**
Add to `requirements.txt`:
```
Flask-Limiter
```

### 2. Custom Implementation
A simple in-memory rate limiter:

**Benefits:**
- No additional dependencies
- Full control over implementation
- Lightweight

**Drawbacks:**
- Not suitable for multi-instance deployments
- Limited persistence

## Implementation Plan

### 1. Using Flask-Limiter

#### Basic Setup:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize rate limiter
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per hour", "10 per minute"]
)

# Apply rate limiting to specific routes
@app.route('/', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def index():
    # ... existing code ...
    pass

# Global rate limits for all routes
# Can be overridden by route-specific limits
```

#### Advanced Configuration:
```python
from flask_limiter.util import get_ipaddr

# Use a more sophisticated key function
def get_true_client_ip():
    """Get the true client IP, considering proxies"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return get_ipaddr()

# Configure rate limiter with Redis for production
limiter = Limiter(
    app,
    key_func=get_true_client_ip,
    default_limits=["200 per hour"],
    storage_uri="redis://localhost:6379",
    strategy="fixed-window-elastic-expiry"
)

# Custom rate limit messages
@app.errorhandler(429)
def ratelimit_handler(e):
    logger.warning(f"Rate limit exceeded for IP: {get_true_client_ip()}")
    return {
        "error": "Rate limit exceeded",
        "message": "Too many requests, please try again later"
    }, 429
```

### 2. Route-Specific Rate Limits

#### Download Endpoint:
```python
@app.route('/', methods=['GET', 'POST'])
@limiter.limit("3 per minute; 10 per hour")
def index():
    """Main download endpoint with stricter rate limits"""
    if request.method == 'POST':
        # ... existing code ...
        pass
    return render_template('index.html')
```

#### Health Check Endpoints:
```python
# No rate limits for health checks
@app.route('/health')
@limiter exempt
def health_check():
    """Health check endpoint - no rate limits"""
    return {'status': 'healthy'}, 200
```

### 3. User-Agent Based Rate Limiting
```python
def get_rate_limit_key():
    """Custom key function that considers User-Agent"""
    return f"{get_remote_address()}:{request.headers.get('User-Agent', '')[:50]}"

limiter = Limiter(
    app,
    key_func=get_rate_limit_key,
    default_limits=["100 per hour"]
)
```

## Rate Limiting Strategies

### 1. Fixed Window
- Simple to implement
- Can lead to traffic spikes at window boundaries

### 2. Sliding Window
- More smooth rate limiting
- More complex implementation

### 3. Token Bucket
- Allows for burst traffic within limits
- Good for handling variable traffic patterns

## Storage Options

### 1. In-Memory (Development)
```python
limiter = Limiter(
    app,
    key_func=get_remote_address,
    storage_uri="memory://"
)
```

### 2. Redis (Production)
```python
limiter = Limiter(
    app,
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379/0"
)
```

### 3. Memcached
```python
limiter = Limiter(
    app,
    key_func=get_remote_address,
    storage_uri="memcached://localhost:11211"
)
```

## Rate Limiting Rules for TikTok Downloader

### 1. Global Limits
- 100 requests per hour per IP
- 10 requests per minute per IP

### 2. Download Endpoint Limits
- 3 download requests per minute per IP
- 10 download requests per hour per IP

### 3. Burst Protection
- Allow short bursts but enforce stricter average limits
- Implement exponential backoff for repeated violations

## Implementation Steps

1. Add Flask-Limiter to requirements.txt
2. Initialize rate limiter in the application
3. Configure global rate limits
4. Apply specific rate limits to download endpoints
5. Exempt health check endpoints from rate limiting
6. Implement custom error handling for rate limit exceeded
7. Add logging for rate limit violations
8. Test rate limiting in development environment
9. Configure appropriate storage backend for production

## Security Considerations

### 1. IP Address Spoofing
- Use proper IP detection considering proxies
- Implement additional identification methods

### 2. Rate Limit Evasion
- Use multiple identification factors (IP + User-Agent)
- Implement account-based rate limiting if users authenticate

### 3. Logging and Monitoring
- Log rate limit violations
- Monitor for abuse patterns
- Set up alerts for excessive violations

## Configuration with Environment Variables

```python
class Config:
    # ... other config ...
    
    # Rate limiting configuration
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL') or 'memory://'
    RATELIMIT_GLOBAL_LIMITS = os.environ.get('RATELIMIT_GLOBAL_LIMITS') or '100 per hour'
    
    # Download-specific limits
    RATELIMIT_DOWNLOAD_LIMITS = os.environ.get('RATELIMIT_DOWNLOAD_LIMITS') or '3 per minute'
```

## Testing Rate Limiting

### 1. Unit Tests
```python
def test_rate_limiting(self):
    """Test that rate limits are enforced"""
    # Make multiple requests
    for i in range(5):
        response = self.client.post('/', data={'url': 'test_url'})
    
    # Check that rate limit is enforced
    self.assertEqual(response.status_code, 429)
```

### 2. Load Testing
- Use tools like Apache Bench or Locust
- Test rate limit behavior under load
- Verify rate limit recovery

## Monitoring and Metrics

### 1. Track Rate Limit Events
- Count of rate limit violations
- Top violating IPs
- Violation patterns over time

### 2. Alerting
- Set up alerts for excessive rate limit violations
- Monitor for potential DDoS attacks
- Track legitimate user impact