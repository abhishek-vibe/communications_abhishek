from django.conf import settings
from rest_framework import exceptions
from rest_framework.views import APIView

from vendor_service.db_router import set_current_tenant
from .utils import ensure_alias_for_client

def _get_tenant_from_request(request):
    return getattr(request.user, "tenant", None) or getattr(request, "tenant_info", None)

def _ensure_alias_ready(tenant: dict) -> str:
    if not tenant or "alias" not in tenant:
        raise exceptions.AuthenticationFailed("Tenant alias missing in token.")
    alias = tenant["alias"]
    if alias not in settings.DATABASES:
        if tenant.get("client_username"):
            ensure_alias_for_client(client_username=tenant["client_username"])
        elif tenant.get("client_id"):
            ensure_alias_for_client(client_id=int(tenant["client_id"]))
        elif alias.startswith("client_"):
            ensure_alias_for_client(client_id=int(alias.split("_", 1)[1]))
        else:
            raise exceptions.APIException("Unable to resolve tenant DB.")
    return alias

class RouterTenantContextMixin(APIView):
    def initial(self, request, *args, **kwargs):
        alias = _ensure_alias_ready(_get_tenant_from_request(request))
        set_current_tenant(alias)
        return super().initial(request, *args, **kwargs)
    def finalize_response(self, request, response, *args, **kwargs):
        try:
            return super().finalize_response(request, response, *args, **kwargs)
        finally:
            set_current_tenant(None)

class TenantSerializerContextMixin:
    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        alias = _ensure_alias_ready(_get_tenant_from_request(self.request))
        ctx["alias"] = alias
        ctx["request"] = self.request
        return ctx

class _TenantDBMixin:
    def _alias(self) -> str:
        return _ensure_alias_ready(_get_tenant_from_request(self.request))