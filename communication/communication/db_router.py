# communication/db_router.py
import threading
from contextvars import ContextVar

# Thread-local storage for current tenant (fallback for older Python versions)
_thread_local = threading.local()

# ContextVar for current tenant (preferred for async support)
_current_tenant = ContextVar("current_tenant", default=None)

def set_current_tenant(tenant_id):
    """Set the current tenant for this thread/context"""
    # Set both for maximum compatibility
    _current_tenant.set(tenant_id)
    _thread_local.tenant_id = tenant_id

def get_current_tenant():
    """Get the current tenant for this thread/context"""
    # Try ContextVar first (better for async), then thread-local
    try:
        tenant_id = _current_tenant.get()
        if tenant_id is not None:
            return tenant_id
    except LookupError:
        pass
    
    return getattr(_thread_local, 'tenant_id', None)

class MultiTenantDatabaseRouter:
    """
    Multi-tenant database router that handles both master and tenant databases.
    
    MASTER apps -> default (SQLite): config, auth, admin, contenttypes, sessions
    POSTGRES_MAIN apps -> postgres_main (PostgreSQL): databases
    TENANT apps -> per-tenant Postgres: api, communicationapp
    """
    
    # Apps that always use the master/default database
    master_apps = {
        "auth", 
        "admin", 
        "contenttypes", 
        "sessions", 
        "config",
        "messages"  # Django messages framework
    }
    
    # Apps that use the main PostgreSQL database
    postgres_main_apps = {
        "databases"  # UserDatabase model goes to main postgres
    }
    
    # Apps that use tenant-specific databases
    tenant_apps = {
        "api", 
        "communicationapp"
    }

    def _get_tenant_db(self, hints=None):
        """Get the tenant database alias"""
        if hints:
            tenant_db = hints.get("tenant_db")
            if tenant_db:
                return tenant_db
        
        tenant_id = get_current_tenant()
        if tenant_id and tenant_id != 'default':
            return f'client_{tenant_id}'
        
        return None

    def db_for_read(self, model, **hints):
        """Suggest the database to read from"""
        app_label = model._meta.app_label
        
        # Master apps always use default database
        if app_label in self.master_apps:
            return "default"
        
        # Databases app uses main postgres
        if app_label in self.postgres_main_apps:
            return "postgres_main"
        
        # Tenant apps use tenant-specific database
        if app_label in self.tenant_apps:
            tenant_db = self._get_tenant_db(hints)
            if tenant_db:
                return tenant_db
        
        # Default fallback
        return "default"

    def db_for_write(self, model, **hints):
        """Suggest the database to write to"""
        app_label = model._meta.app_label
        
        # Master apps always use default database
        if app_label in self.master_apps:
            return "default"
        
        # Databases app uses main postgres
        if app_label in self.postgres_main_apps:
            return "postgres_main"
        
        # Tenant apps use tenant-specific database
        if app_label in self.tenant_apps:
            tenant_db = self._get_tenant_db(hints)
            if tenant_db:
                return tenant_db
        
        # Default fallback
        return "default"

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Determine if migration is allowed"""
        # Master apps only migrate on default database
        if app_label in self.master_apps:
            return db == "default"
        
        # Databases app only migrates to postgres_main
        if app_label in self.postgres_main_apps:
            return db == "postgres_main"
        
        # Tenant apps only migrate on client databases
        if app_label in self.tenant_apps:
            if db == "default":
                return False
            return db.startswith('client_')
        
        # Unknown apps default to default database
        return db == "default"

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if models are in the same database"""
        # Get database for each object
        db1 = self.db_for_read(obj1._meta.model, **hints)
        db2 = self.db_for_read(obj2._meta.model, **hints)
        
        # Allow relations within the same database
        if db1 == db2:
            return True
        
        # Allow relations between default database objects
        if db1 == "default" and db2 == "default":
            return True
        
        # Deny cross-database relations
        return False