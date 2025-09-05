# communication/middleware.py
from django.utils.deprecation import MiddlewareMixin
from .db_router import set_current_tenant


class TenantMiddleware(MiddlewareMixin):
    """Middleware to handle multi-tenant database routing"""
    
    def __init__(self, get_response=None):
        # Support both old-style MiddlewareMixin and new-style middleware
        self.get_response = get_response
        super().__init__(get_response) if get_response else None
    
    def __call__(self, request):
        """New-style middleware call method"""
        if hasattr(self, 'get_response') and self.get_response:
            # Extract tenant information from request
            self.process_request(request)
            response = self.get_response(request)
            return self.process_response(request, response)
        return None
    
    def process_request(self, request):
        """Extract and set tenant information from the request"""
        # Try multiple sources for tenant identification
        tenant_id = (
            request.headers.get("X-Tenant") or  # Your existing header approach
            request.GET.get("tenant") or        # URL parameter
            request.META.get("HTTP_X_TENANT") or # Alternative header format
            "default"                           # Fallback to default
        )
        
        # Set the tenant for the database router
        set_current_tenant(tenant_id)
        
        # Also store it on the request for easy access in views
        request.tenant_db = f'client_{tenant_id}' if tenant_id != 'default' else 'default'
        request.tenant_id = tenant_id
    
    def process_response(self, request, response):
        """Clean up tenant context after request processing"""
        set_current_tenant(None)
        return response