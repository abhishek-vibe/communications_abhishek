# api/utils.py
import os
import psycopg2
from cryptography.fernet import Fernet
from django.conf import settings
from django.db import connections


def get_encryption_key():
    """Get or create encryption key for database passwords"""
    key = getattr(settings, 'DB_ENCRYPTION_KEY', None)
    if not key:
        # Generate a key if not provided
        key = Fernet.generate_key()
        print(f"Generated encryption key: {key.decode()}")
        print("Please add this to your .env file as DB_ENCRYPTION_KEY")
    else:
        key = key.encode() if isinstance(key, str) else key
    return key


def encrypt_password(password):
    """Encrypt database password"""
    try:
        key = get_encryption_key()
        f = Fernet(key)
        encrypted_password = f.encrypt(password.encode())
        return encrypted_password.decode()
    except Exception as e:
        print(f"Encryption error: {e}")
        return password  # Return original if encryption fails


def decrypt_password(encrypted_password):
    """Decrypt database password - supports both new and legacy encryption"""
    try:
        # First try with DB_ENCRYPTION_KEY (new method)
        key = getattr(settings, 'DB_ENCRYPTION_KEY', None)
        if key:
            if isinstance(key, str):
                key = key.encode()
            f = Fernet(key)
            if isinstance(encrypted_password, str):
                decrypted_password = f.decrypt(encrypted_password.encode())
                return decrypted_password.decode()
        else:
            # Fallback to legacy method using SECRET_KEY
            key = settings.SECRET_KEY[:32].encode()  # Fernet requires 32 bytes
            fernet = Fernet(key)
            return fernet.decrypt(encrypted_password.encode()).decode()
        
        return encrypted_password
    except Exception as e:
        print(f"Decryption error: {e}")
        return encrypted_password  # Return original if decryption fails


def test_db_connection(name=None, user=None, password=None, host=None, port=None, config=None):
    """Test database connection - supports both individual params and config dict"""
    try:
        if config:
            # Support for config dict format (your existing style)
            conn = psycopg2.connect(
                dbname=config.get("NAME"),
                user=config.get("USER"),
                password=config.get("PASSWORD"),
                host=config.get("HOST"),
                port=config.get("PORT"),
                connect_timeout=10
            )
        else:
            # Support for individual parameters (new style)
            # Convert port to integer if it's a string
            if isinstance(port, str):
                port = int(port)
                
            conn = psycopg2.connect(
                database=name,
                user=user,
                password=password,
                host=host,
                port=port,
                connect_timeout=10
            )
        
        conn.close()
        
        if config:
            return True  # Your existing format returns boolean
        else:
            return True, "Connection successful"  # New format returns tuple
            
    except psycopg2.Error as e:
        print(f"Database connection failed: {e}")
        if config:
            return False
        else:
            return False, str(e)
    except Exception as e:
        print(f"Database connection failed: {e}")
        if config:
            return False
        else:
            return False, f"Connection failed: {str(e)}"


def add_db_alias(alias, db_name=None, db_user=None, db_password=None, db_host=None, db_port=None, config=None):
    """Add database alias to Django settings - supports both individual params and config dict"""
    if config:
        settings.DATABASES[alias] = config
    else:
        # Convert port to int if needed
        if isinstance(db_port, str):
            db_port = int(db_port)

        cfg = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': db_name,
            'USER': db_user,
            'PASSWORD': db_password,
            'HOST': db_host,
            'PORT': db_port,
            'TIME_ZONE': getattr(settings, "TIME_ZONE", None),
            'CONN_MAX_AGE': 60,   # keep connection alive for reuse
            'CONN_HEALTH_CHECKS': True,
            'AUTOCOMMIT': True,
            'OPTIONS': {
                'connect_timeout': 10,
            }
        }

        settings.DATABASES[alias] = cfg
        connections.databases[alias] = cfg  # register with Django’s connection handler