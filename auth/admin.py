"""Admin authentication for protected endpoints."""
import os
from functools import wraps
from flask import request, jsonify


def get_admin_token() -> str:
    """Get admin token from environment variable.
    
    Returns:
        Admin token (should be a strong random string)
    """
    token = os.getenv('ADMIN_TOKEN')
    if not token:
        raise ValueError(
            "ADMIN_TOKEN environment variable not set! "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
    return token


def require_admin(f):
    """Decorator to require admin authentication.
    
    Admin token can be provided via:
    - Header: Authorization: Bearer <token>
    - Query param: ?admin_token=<token>
    
    Usage:
        @app.route('/api/v1/admin/keys/generate', methods=['POST'])
        @require_admin
        def admin_generate_key():
            # Only admin can access
            return jsonify({"api_key": "..."})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get admin token from environment
        try:
            admin_token = get_admin_token()
        except ValueError as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500
        
        # Get provided token from header or query param
        provided_token = None
        
        # Check Authorization header (Bearer token)
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            provided_token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Check query parameter as fallback
        if not provided_token:
            provided_token = request.args.get('admin_token')
        
        # Verify token
        if not provided_token:
            return jsonify({
                "status": "error",
                "message": "Admin authentication required",
                "help": "Provide 'Authorization: Bearer <token>' header or '?admin_token=<token>' query param"
            }), 401
        
        if provided_token != admin_token:
            return jsonify({
                "status": "error",
                "message": "Invalid admin token"
            }), 403
        
        # Token valid, proceed
        return f(*args, **kwargs)
    
    return decorated_function
