"""Security module for genomics microcosting analysis.

This module provides comprehensive security capabilities including
input sanitization, role-based access control, audit trail tracking,
and secure configuration storage.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from datetime import datetime
import re
from functools import wraps

from .logging_config import get_logger
from .input_validation import InputValidator, ValidationError


logger = get_logger(__name__)


class SecurityError(Exception):
    """Custom exception for security-related errors."""
    pass


class InputSanitizer:
    """Sanitizes input data to prevent security vulnerabilities."""
    
    def __init__(self, logger: logging.Logger = None):
        """Initialize the input sanitizer.
        
        Args:
            logger: Logger instance (optional)
        """
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.validator = InputValidator(self.logger)
    
    def sanitize_string_input(self, value: str, max_length: int = 1000) -> str:
        """Sanitize string input to prevent injection attacks.
        
        Args:
            value: String value to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
            
        Raises:
            ValidationError: If input is invalid
        """
        try:
            # Validate input
            self.validator.validate_string_value(value, max_length=max_length)
            
            # Remove potentially dangerous characters
            # Remove control characters except common whitespace
            sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', value)
            
            # Remove common injection patterns
            sanitized = re.sub(r'<.*?>', '', sanitized)  # Remove HTML tags
            sanitized = re.sub(r'["\']', '', sanitized)  # Remove quotes
            sanitized = re.sub(r'[;`|&]', '', sanitized)   # Remove command injection characters
            
            # Limit consecutive whitespace
            sanitized = re.sub(r'\s+', ' ', sanitized).strip()
            
            self.logger.debug(f"Sanitized string input: {len(value)} -> {len(sanitized)} chars")
            return sanitized
            
        except Exception as e:
            self.logger.error(f"Error sanitizing string input: {e}")
            raise ValidationError(f"Invalid input: {e}")
    
    def sanitize_file_path(self, file_path: str) -> str:
        """Sanitize file path to prevent directory traversal attacks.
        
        Args:
            file_path: File path to sanitize
            
        Returns:
            Sanitized file path
            
        Raises:
            ValidationError: If path is invalid
        """
        try:
            # Validate input
            self.validator.validate_string_value(file_path, max_length=500)
            
            # Remove null bytes
            sanitized = file_path.replace('\x00', '')
            
            # Remove directory traversal sequences
            sanitized = sanitized.replace('../', '').replace('..\\', '')
            sanitized = sanitized.replace('./', '').replace('.\\', '')
            
            # Normalize path separators
            sanitized = sanitized.replace('\\', '/')
            
            # Remove multiple consecutive slashes
            sanitized = re.sub(r'/+', '/', sanitized)
            
            # Ensure path doesn't start with /
            if sanitized.startswith('/'):
                sanitized = sanitized[1:]
                
            self.logger.debug(f"Sanitized file path: {file_path} -> {sanitized}")
            return sanitized
            
        except Exception as e:
            self.logger.error(f"Error sanitizing file path: {e}")
            raise ValidationError(f"Invalid file path: {e}")
    
    def sanitize_excel_cell_reference(self, cell_ref: str) -> str:
        """Sanitize Excel cell reference.
        
        Args:
            cell_ref: Cell reference to sanitize
            
        Returns:
            Sanitized cell reference
            
        Raises:
            ValidationError: If cell reference is invalid
        """
        try:
            # First sanitize by converting to uppercase
            sanitized = cell_ref.upper().strip()
            
            # Then validate the sanitized input
            self.validator.validate_cell_reference(sanitized)
            
            self.logger.debug(f"Sanitized cell reference: {cell_ref} -> {sanitized}")
            return sanitized
            
        except Exception as e:
            self.logger.error(f"Error sanitizing cell reference: {e}")
            raise ValidationError(f"Invalid cell reference: {e}")
    
    def sanitize_sheet_name(self, sheet_name: str) -> str:
        """Sanitize Excel sheet name.
        
        Args:
            sheet_name: Sheet name to sanitize
            
        Returns:
            Sanitized sheet name
            
        Raises:
            ValidationError: If sheet name is invalid
        """
        try:
            # Remove potentially dangerous characters first
            sanitized = re.sub(r'[<>"|:*?/\\]', '', sheet_name)
            
            # Limit length
            if len(sanitized) > 255:
                sanitized = sanitized[:255]
                
            # Remove leading/trailing whitespace
            sanitized = sanitized.strip()
            
            # Then validate the sanitized input
            self.validator.validate_sheet_name(sanitized)
            
            self.logger.debug(f"Sanitized sheet name: {sheet_name} -> {sanitized}")
            return sanitized
            
        except Exception as e:
            self.logger.error(f"Error sanitizing sheet name: {e}")
            raise ValidationError(f"Invalid sheet name: {e}")


class Role:
    """Represents a user role with specific permissions."""
    
    def __init__(self, name: str, permissions: Set[str]):
        """Initialize a role.
        
        Args:
            name: Role name
            permissions: Set of permissions for this role
        """
        self.name = name
        self.permissions = set(permissions)
    
    def has_permission(self, permission: str) -> bool:
        """Check if role has a specific permission.
        
        Args:
            permission: Permission to check
            
        Returns:
            True if role has permission, False otherwise
        """
        return permission in self.permissions
    
    def add_permission(self, permission: str):
        """Add a permission to the role.
        
        Args:
            permission: Permission to add
        """
        self.permissions.add(permission)
    
    def remove_permission(self, permission: str):
        """Remove a permission from the role.
        
        Args:
            permission: Permission to remove
        """
        self.permissions.discard(permission)


class User:
    """Represents a user with roles and authentication status."""
    
    def __init__(self, username: str, roles: List[Role] = None):
        """Initialize a user.
        
        Args:
            username: Username
            roles: List of roles for this user
        """
        self.username = username
        self.roles = roles or []
        self.authenticated = False
        self.last_login = None
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission.
        
        Args:
            permission: Permission to check
            
        Returns:
            True if user has permission, False otherwise
        """
        return any(role.has_permission(permission) for role in self.roles)
    
    def add_role(self, role: Role):
        """Add a role to the user.
        
        Args:
            role: Role to add
        """
        if role not in self.roles:
            self.roles.append(role)
    
    def remove_role(self, role: Role):
        """Remove a role from the user.
        
        Args:
            role: Role to remove
        """
        if role in self.roles:
            self.roles.remove(role)


class AccessControlManager:
    """Manages role-based access control for the application."""
    
    def __init__(self, logger: logging.Logger = None):
        """Initialize the access control manager.
        
        Args:
            logger: Logger instance (optional)
        """
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.roles: Dict[str, Role] = {}
        self.users: Dict[str, User] = {}
        self.current_user: Optional[User] = None
        
        # Create default roles
        self._create_default_roles()
    
    def _create_default_roles(self):
        """Create default roles for the application."""
        # Administrator role with all permissions
        admin_role = Role("admin", {
            "read_data", "write_data", "delete_data",
            "configure_system", "manage_users",
            "access_sensitive_data", "export_data",
            "run_analysis", "view_reports"
        })
        self.roles["admin"] = admin_role
        
        # Analyst role with analysis permissions
        analyst_role = Role("analyst", {
            "read_data", "run_analysis", "view_reports",
            "export_data"
        })
        self.roles["analyst"] = analyst_role
        
        # Viewer role with read-only permissions
        viewer_role = Role("viewer", {
            "read_data", "view_reports"
        })
        self.roles["viewer"] = viewer_role
        
        self.logger.info("Created default roles: admin, analyst, viewer")
    
    def authenticate_user(self, username: str, password: str = None) -> bool:
        """Authenticate a user.
        
        Args:
            username: Username
            password: Password (optional for demo purposes)
            
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # In a real implementation, this would check credentials against a secure store
            # For demo purposes, we'll just check if user exists
            
            if username not in self.users:
                # Create user if it doesn't exist (demo behavior)
                self.users[username] = User(username)
                self.logger.info(f"Created new user: {username}")
            
            user = self.users[username]
            user.authenticated = True
            user.last_login = datetime.now().isoformat()
            self.current_user = user
            
            self.logger.info(f"User authenticated: {username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error authenticating user {username}: {e}")
            return False
    
    def logout_user(self):
        """Log out the current user."""
        if self.current_user:
            self.logger.info(f"User logged out: {self.current_user.username}")
            self.current_user = None
    
    def require_permission(self, permission: str):
        """Decorator to require a specific permission for a function.
        
        Args:
            permission: Required permission
            
        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.current_user:
                    raise SecurityError("User not authenticated")
                
                if not self.current_user.has_permission(permission):
                    raise SecurityError(f"User {self.current_user.username} lacks permission: {permission}")
                
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def add_user_to_role(self, username: str, role_name: str) -> bool:
        """Add a user to a role.
        
        Args:
            username: Username
            role_name: Role name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if username not in self.users:
                self.users[username] = User(username)
            
            if role_name not in self.roles:
                self.logger.error(f"Role {role_name} not found")
                return False
                
            user = self.users[username]
            role = self.roles[role_name]
            
            user.add_role(role)
            self.logger.info(f"Added user {username} to role {role_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding user {username} to role {role_name}: {e}")
            return False
    
    def get_user_permissions(self, username: str) -> Set[str]:
        """Get all permissions for a user.
        
        Args:
            username: Username
            
        Returns:
            Set of permissions
        """
        if username not in self.users:
            return set()
            
        user = self.users[username]
        permissions = set()
        for role in user.roles:
            permissions.update(role.permissions)
            
        return permissions


class AuditTrail:
    """Tracks and logs security-relevant events."""
    
    def __init__(self, log_file: Optional[str] = None, logger: logging.Logger = None):
        """Initialize the audit trail.
        
        Args:
            log_file: File to store audit logs (optional)
            logger: Logger instance (optional)
        """
        self.log_file = log_file
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.events: List[Dict[str, Any]] = []
    
    def log_event(self, event_type: str, user: Optional[str], resource: str, 
                  details: Optional[str] = None, success: bool = True):
        """Log a security-relevant event.
        
        Args:
            event_type: Type of event (e.g., 'login', 'access', 'modification')
            user: Username (if authenticated)
            resource: Resource being accessed or modified
            details: Additional details about the event
            success: Whether the event was successful
        """
        try:
            event = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "user": user,
                "resource": resource,
                "details": details,
                "success": success
            }
            
            self.events.append(event)
            
            # Log to file if specified
            if self.log_file:
                try:
                    with open(self.log_file, 'a') as f:
                        f.write(json.dumps(event) + '\n')
                except Exception as e:
                    self.logger.error(f"Error writing to audit log file: {e}")
            
            # Log to standard logger
            log_level = logging.INFO if success else logging.WARNING
            self.logger.log(log_level, f"Audit: {event_type} by {user} on {resource} - {success}")
            
        except Exception as e:
            self.logger.error(f"Error logging audit event: {e}")
    
    def get_events(self, user: Optional[str] = None, 
                   event_type: Optional[str] = None,
                   start_time: Optional[str] = None,
                   end_time: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get audit events matching criteria.
        
        Args:
            user: Filter by username
            event_type: Filter by event type
            start_time: Filter by start time (ISO format)
            end_time: Filter by end time (ISO format)
            
        Returns:
            List of matching events
        """
        filtered_events = self.events
        
        if user:
            filtered_events = [e for e in filtered_events if e.get("user") == user]
            
        if event_type:
            filtered_events = [e for e in filtered_events if e.get("event_type") == event_type]
            
        if start_time:
            filtered_events = [e for e in filtered_events if e.get("timestamp") >= start_time]
            
        if end_time:
            filtered_events = [e for e in filtered_events if e.get("timestamp") <= end_time]
            
        return filtered_events
    
    def clear_events(self):
        """Clear all audit events."""
        self.events.clear()
        self.logger.info("Audit events cleared")


class SecureConfigStorage:
    """Securely stores configuration data with encryption."""
    
    def __init__(self, config_file: str, encryption_key: Optional[str] = None,
                 logger: logging.Logger = None):
        """Initialize secure configuration storage.
        
        Args:
            config_file: Path to configuration file
            encryption_key: Encryption key (optional)
            logger: Logger instance (optional)
        """
        self.config_file = Path(config_file)
        self.encryption_key = encryption_key
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # Create config directory if it doesn't exist
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt data using simple XOR cipher (demo implementation).
        
        Args:
            data: Data to encrypt
            
        Returns:
            Encrypted data
        """
        if not self.encryption_key:
            return data  # No encryption if no key provided
            
        # Simple XOR encryption for demo purposes
        # In production, use proper encryption library like cryptography
        key_bytes = self.encryption_key.encode('utf-8')
        data_bytes = data.encode('utf-8')
        
        encrypted_bytes = bytearray()
        for i, byte in enumerate(data_bytes):
            key_byte = key_bytes[i % len(key_bytes)]
            encrypted_bytes.append(byte ^ key_byte)
            
        return encrypted_bytes.hex()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data using simple XOR cipher (demo implementation).
        
        Args:
            encrypted_data: Encrypted data
            
        Returns:
            Decrypted data
        """
        if not self.encryption_key:
            return encrypted_data  # No decryption if no key provided
            
        # Simple XOR decryption for demo purposes
        encrypted_bytes = bytes.fromhex(encrypted_data)
        key_bytes = self.encryption_key.encode('utf-8')
        
        decrypted_bytes = bytearray()
        for i, byte in enumerate(encrypted_bytes):
            key_byte = key_bytes[i % len(key_bytes)]
            decrypted_bytes.append(byte ^ key_byte)
            
        return decrypted_bytes.decode('utf-8')
    
    def save_config(self, config_data: Dict[str, Any]) -> bool:
        """Save configuration data securely.
        
        Args:
            config_data: Configuration data to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to JSON
            config_json = json.dumps(config_data, indent=2, default=str)
            
            # Encrypt if key is provided
            if self.encryption_key:
                encrypted_data = self._encrypt_data(config_json)
                config_to_save = {"encrypted": True, "data": encrypted_data}
            else:
                config_to_save = {"encrypted": False, "data": config_json}
            
            # Save to file
            with open(self.config_file, 'w') as f:
                json.dump(config_to_save, f, indent=2)
                
            self.logger.info(f"Configuration saved to {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def load_config(self) -> Optional[Dict[str, Any]]:
        """Load configuration data securely.
        
        Returns:
            Configuration data, or None if failed
        """
        try:
            # Check if file exists
            if not self.config_file.exists():
                self.logger.info(f"Configuration file {self.config_file} does not exist")
                return None
                
            # Load from file
            with open(self.config_file, 'r') as f:
                config_stored = json.load(f)
            
            # Decrypt if needed
            if config_stored.get("encrypted", False):
                decrypted_json = self._decrypt_data(config_stored["data"])
                config_data = json.loads(decrypted_json)
            else:
                config_data = json.loads(config_stored["data"])
                
            self.logger.info(f"Configuration loaded from {self.config_file}")
            return config_data
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            return None


# Convenience functions
def setup_standard_security(logger: logging.Logger = None) -> tuple:
    """Set up standard security components.
    
    Args:
        logger: Logger instance (optional)
        
    Returns:
        Tuple of (InputSanitizer, AccessControlManager, AuditTrail, SecureConfigStorage)
    """
    logger = logger or get_logger(__name__)
    
    sanitizer = InputSanitizer(logger)
    access_control = AccessControlManager(logger)
    audit_trail = AuditTrail(logger=logger)
    secure_storage = SecureConfigStorage("configs/secure_config.json", logger=logger)
    
    return sanitizer, access_control, audit_trail, secure_storage


# Example usage:
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create security components
    sanitizer, access_control, audit_trail, secure_storage = setup_standard_security()
    
    # Example 1: Input sanitization
    try:
        unsafe_input = "<script>alert('xss')</script>../etc/passwd"
        safe_input = sanitizer.sanitize_string_input(unsafe_input)
        print(f"Sanitized input: {safe_input}")
    except ValidationError as e:
        print(f"Validation error: {e}")
    
    # Example 2: Role-based access control
    access_control.authenticate_user("researcher")
    access_control.add_user_to_role("researcher", "analyst")
    
    permissions = access_control.get_user_permissions("researcher")
    print(f"Researcher permissions: {permissions}")
    
    # Example 3: Audit trail
    audit_trail.log_event("login", "researcher", "system", "User logged in", True)
    audit_trail.log_event("data_access", "researcher", "cost_data.xlsx", "Accessed sensitive data", True)
    
    events = audit_trail.get_events(user="researcher")
    print(f"Audit events for researcher: {len(events)}")
    
    # Example 4: Secure configuration storage
    config_data = {
        "database_url": "postgresql://user:password@localhost/db",
        "api_key": "secret_api_key_12345",
        "analysis_parameters": {
            "monte_carlo_iterations": 1000,
            "confidence_level": 0.95
        }
    }
    
    # Save with encryption
    secure_storage_encrypted = SecureConfigStorage("configs/secure_config_encrypted.json", 
                                                  encryption_key="my_secret_key")
    success = secure_storage_encrypted.save_config(config_data)
    print(f"Encrypted config save success: {success}")
    
    # Load encrypted config
    loaded_config = secure_storage_encrypted.load_config()
    print(f"Loaded encrypted config: {loaded_config is not None}")