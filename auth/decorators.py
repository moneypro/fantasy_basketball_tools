"""Authentication decorators for Flask endpoints."""
from functools import wraps
from flask import request, jsonify
from auth.api_key import get_api_key_manager


def require_api_key(f):
    """Decorator to require valid API key for endpoint.
    
    API key can be provided via:
    - Header: X-API-Key: <key>
    - Query param: ?api_key=<key>
    
    Usage:
        @app.route('/api/v1/protected', methods=['GET'])
        @require_api_key
        def protected_endpoint():
            return jsonify({"data": "only for authenticated users"})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        manager = get_api_key_manager()
        
        # Get API key from header or query param
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({
                "status": "error",
                "message": "API key required",
                "help": "Provide X-API-Key header or ?api_key= query param"
            }), 401
        
        # Verify key exists and is active
        if not manager.verify_key(api_key):
            return jsonify({
                "status": "error",
                "message": "Invalid or revoked API key"
            }), 401
        
        # Check rate limit
        if not manager.check_rate_limit(api_key):
            return jsonify({
                "status": "error",
                "message": "Rate limit exceeded",
                "limit": manager.get_key_info(api_key).rate_limit,
                "help": "You have exceeded your hourly request limit"
            }), 429
        
        # Increment usage
        manager.increment_usage(api_key)
        
        # Add API key info to request for use in endpoint
        request.api_key = api_key
        request.api_key_info = manager.get_key_info(api_key)
        
        return f(*args, **kwargs)
    
    return decorated_function


def optional_api_key(f):
    """Decorator to optionally accept API key.
    
    If API key is provided, it must be valid.
    If not provided, endpoint still works but may return limited data.
    
    Usage:
        @app.route('/api/v1/public', methods=['GET'])
        @optional_api_key
        def public_endpoint():
            if hasattr(request, 'api_key'):
                return jsonify({"data": "premium data"})
            else:
                return jsonify({"data": "basic data"})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        manager = get_api_key_manager()
        
        # Get API key from header or query param (optional)
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if api_key:
            # Verify key if provided
            if not manager.verify_key(api_key):
                return jsonify({
                    "status": "error",
                    "message": "Invalid or revoked API key"
                }), 401
            
            # Check rate limit
            if not manager.check_rate_limit(api_key):
                return jsonify({
                    "status": "error",
                    "message": "Rate limit exceeded"
                }), 429
            
            # Increment usage
            manager.increment_usage(api_key)
            
            # Add API key info to request
            request.api_key = api_key
            request.api_key_info = manager.get_key_info(api_key)
        
        return f(*args, **kwargs)
    
    return decorated_function
