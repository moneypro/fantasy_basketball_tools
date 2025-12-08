"""Authentication decorators for Flask endpoints."""
import time
from functools import wraps
from flask import request, jsonify
from auth.api_key import get_api_key_manager
from auth.authz import check_endpoint_access, APITier
from auth.request_logger import log_request, log_request_to_json


def require_api_key(f):
    """Decorator to require valid API key for endpoint.
    
    API key can be provided via:
    - Bearer Token: Authorization: Bearer <key>
    - Header: X-API-Key: <key>
    - Query param: ?api_key=<key>
    - Request body: {"api_key": "<key>"} (for POST requests)
    
    Includes:
    - Authentication verification
    - Authorization (authZ) checks based on API tier
    - Request logging for usage tracking
    - Rate limiting
    
    Usage:
        @app.route('/api/v1/protected', methods=['GET'])
        @require_api_key
        def protected_endpoint():
            return jsonify({"data": "only for authenticated users"})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        manager = get_api_key_manager()
        start_time = time.time()
        
        # Get API key from Bearer token, header, query param, or request body
        api_key = None
        
        # Check Bearer token first (preferred)
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            api_key = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Fall back to X-API-Key header or query param
        if not api_key:
            api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        # For POST requests, also check request body
        if not api_key and request.method == 'POST':
            try:
                data = request.get_json() or {}
                api_key = data.get('api_key')
            except:
                pass
        
        if not api_key:
            response_time = (time.time() - start_time) * 1000
            log_request(
                method=request.method,
                path=request.path,
                status_code=401,
                key_name="unknown",
                tier="unknown",
                response_time_ms=response_time,
                error_message="No API key provided"
            )
            return jsonify({
                "status": "error",
                "message": "API key required",
                "help": "Provide one of: X-API-Key header, ?api_key= query param, or api_key in request body"
            }), 401
        
        # Verify key exists and is active
        if not manager.verify_key(api_key):
            response_time = (time.time() - start_time) * 1000
            log_request(
                method=request.method,
                path=request.path,
                status_code=401,
                key_name="unknown",
                tier="unknown",
                response_time_ms=response_time,
                error_message="Invalid or revoked API key"
            )
            return jsonify({
                "status": "error",
                "message": "Invalid or revoked API key"
            }), 401
        
        key_info = manager.get_key_info(api_key)
        
        # Check authorization (authZ) - verify tier has access to this endpoint
        if not check_endpoint_access(APITier(key_info.tier), request.method, request.path):
            response_time = (time.time() - start_time) * 1000
            log_request(
                method=request.method,
                path=request.path,
                status_code=403,
                key_name=key_info.name,
                tier=key_info.tier,
                response_time_ms=response_time,
                error_message=f"Tier '{key_info.tier}' does not have access to this endpoint"
            )
            log_request_to_json(
                method=request.method,
                path=request.path,
                status_code=403,
                key_name=key_info.name,
                tier=key_info.tier,
                response_time_ms=response_time,
                endpoint=request.path,
                error_message="Authorization denied - insufficient tier",
                user_agent=request.headers.get('User-Agent'),
                ip_address=request.remote_addr
            )
            return jsonify({
                "status": "error",
                "message": "Access denied",
                "reason": f"Your tier '{key_info.tier}' does not have access to this endpoint",
                "required_tier": "contact support for upgrade"
            }), 403
        
        # Check rate limit
        if not manager.check_rate_limit(api_key):
            response_time = (time.time() - start_time) * 1000
            log_request(
                method=request.method,
                path=request.path,
                status_code=429,
                key_name=key_info.name,
                tier=key_info.tier,
                response_time_ms=response_time,
                error_message="Rate limit exceeded"
            )
            log_request_to_json(
                method=request.method,
                path=request.path,
                status_code=429,
                key_name=key_info.name,
                tier=key_info.tier,
                response_time_ms=response_time,
                endpoint=request.path,
                error_message="Rate limit exceeded",
                user_agent=request.headers.get('User-Agent'),
                ip_address=request.remote_addr
            )
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
        
        # Call the actual endpoint
        try:
            result = f(*args, **kwargs)
            
            # Extract status code from result
            if isinstance(result, tuple):
                response_data, status_code = result[0], result[1] if len(result) > 1 else 200
            else:
                status_code = 200
            
            # Log successful request
            response_time = (time.time() - start_time) * 1000
            log_request(
                method=request.method,
                path=request.path,
                status_code=status_code,
                key_name=key_info.name,
                tier=key_info.tier,
                response_time_ms=response_time
            )
            log_request_to_json(
                method=request.method,
                path=request.path,
                status_code=status_code,
                key_name=key_info.name,
                tier=key_info.tier,
                response_time_ms=response_time,
                endpoint=request.path,
                user_agent=request.headers.get('User-Agent'),
                ip_address=request.remote_addr
            )
            
            return result
        except Exception as e:
            # Log error
            response_time = (time.time() - start_time) * 1000
            error_msg = str(e)
            log_request(
                method=request.method,
                path=request.path,
                status_code=500,
                key_name=key_info.name,
                tier=key_info.tier,
                response_time_ms=response_time,
                error_message=error_msg
            )
            log_request_to_json(
                method=request.method,
                path=request.path,
                status_code=500,
                key_name=key_info.name,
                tier=key_info.tier,
                response_time_ms=response_time,
                endpoint=request.path,
                error_message=error_msg,
                user_agent=request.headers.get('User-Agent'),
                ip_address=request.remote_addr
            )
            raise
    
    return decorated_function


def optional_api_key(f):
    """Decorator to optionally accept API key.
    
    If API key is provided, it must be valid.
    If not provided, endpoint still works but may return limited data.
    
    Includes:
    - Optional authentication
    - Authorization (authZ) checks if key is provided
    - Request logging for usage tracking
    - Rate limiting if authenticated
    
    API key can be provided via:
    - Bearer Token: Authorization: Bearer <key>
    - Header: X-API-Key: <key>
    - Query param: ?api_key=<key>
    
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
        start_time = time.time()
        
        # Get API key from Bearer token, header, or query param (optional)
        api_key = None
        
        # Check Bearer token first (preferred)
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            api_key = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Fall back to X-API-Key header or query param
        if not api_key:
            api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if api_key:
            # Verify key if provided
            if not manager.verify_key(api_key):
                response_time = (time.time() - start_time) * 1000
                log_request(
                    method=request.method,
                    path=request.path,
                    status_code=401,
                    key_name="unknown",
                    tier="unknown",
                    response_time_ms=response_time,
                    error_message="Invalid or revoked API key"
                )
                return jsonify({
                    "status": "error",
                    "message": "Invalid or revoked API key"
                }), 401
            
            key_info = manager.get_key_info(api_key)
            
            # Check authorization (authZ) if key is provided
            if not check_endpoint_access(APITier(key_info.tier), request.method, request.path):
                response_time = (time.time() - start_time) * 1000
                log_request(
                    method=request.method,
                    path=request.path,
                    status_code=403,
                    key_name=key_info.name,
                    tier=key_info.tier,
                    response_time_ms=response_time,
                    error_message="Insufficient tier for endpoint"
                )
                log_request_to_json(
                    method=request.method,
                    path=request.path,
                    status_code=403,
                    key_name=key_info.name,
                    tier=key_info.tier,
                    response_time_ms=response_time,
                    endpoint=request.path,
                    error_message="Authorization denied - insufficient tier",
                    user_agent=request.headers.get('User-Agent'),
                    ip_address=request.remote_addr
                )
                return jsonify({
                    "status": "error",
                    "message": "Access denied",
                    "reason": f"Your tier '{key_info.tier}' does not have access to this endpoint"
                }), 403
            
            # Check rate limit
            if not manager.check_rate_limit(api_key):
                response_time = (time.time() - start_time) * 1000
                log_request(
                    method=request.method,
                    path=request.path,
                    status_code=429,
                    key_name=key_info.name,
                    tier=key_info.tier,
                    response_time_ms=response_time,
                    error_message="Rate limit exceeded"
                )
                log_request_to_json(
                    method=request.method,
                    path=request.path,
                    status_code=429,
                    key_name=key_info.name,
                    tier=key_info.tier,
                    response_time_ms=response_time,
                    endpoint=request.path,
                    error_message="Rate limit exceeded",
                    user_agent=request.headers.get('User-Agent'),
                    ip_address=request.remote_addr
                )
                return jsonify({
                    "status": "error",
                    "message": "Rate limit exceeded"
                }), 429
            
            # Increment usage
            manager.increment_usage(api_key)
            
            # Add API key info to request
            request.api_key = api_key
            request.api_key_info = manager.get_key_info(api_key)
        
        # Call the actual endpoint
        try:
            result = f(*args, **kwargs)
            
            # Log successful request if authenticated
            if api_key:
                response_time = (time.time() - start_time) * 1000
                if isinstance(result, tuple):
                    status_code = result[1] if len(result) > 1 else 200
                else:
                    status_code = 200
                
                log_request(
                    method=request.method,
                    path=request.path,
                    status_code=status_code,
                    key_name=key_info.name,
                    tier=key_info.tier,
                    response_time_ms=response_time
                )
                log_request_to_json(
                    method=request.method,
                    path=request.path,
                    status_code=status_code,
                    key_name=key_info.name,
                    tier=key_info.tier,
                    response_time_ms=response_time,
                    endpoint=request.path,
                    user_agent=request.headers.get('User-Agent'),
                    ip_address=request.remote_addr
                )
            
            return result
        except Exception as e:
            # Log error if authenticated
            if api_key:
                response_time = (time.time() - start_time) * 1000
                error_msg = str(e)
                log_request(
                    method=request.method,
                    path=request.path,
                    status_code=500,
                    key_name=key_info.name,
                    tier=key_info.tier,
                    response_time_ms=response_time,
                    error_message=error_msg
                )
                log_request_to_json(
                    method=request.method,
                    path=request.path,
                    status_code=500,
                    key_name=key_info.name,
                    tier=key_info.tier,
                    response_time_ms=response_time,
                    endpoint=request.path,
                    error_message=error_msg,
                    user_agent=request.headers.get('User-Agent'),
                    ip_address=request.remote_addr
                )
            raise
    
    return decorated_function
