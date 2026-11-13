# Security Procedures and Best Practices

## Overview

This document outlines the security procedures and best practices for the Genomics Microcosting Project. The security system provides comprehensive protection through input sanitization, role-based access control, audit trail tracking, and secure configuration storage.

## Security Components

### 1. Input Sanitization

The [InputSanitizer](file:///Users/doughnut/GitHub/microcosting_genomics/src/unimelb_phd_phase_1/security.py#L32-L182) class provides protection against injection attacks and other security vulnerabilities by sanitizing all input data.

#### Key Features:
- String input sanitization to prevent XSS and SQL injection
- File path sanitization to prevent directory traversal attacks
- Excel cell reference sanitization for data integrity
- Sheet name sanitization to prevent invalid characters

#### Usage Example:
```python
from unimelb_phd_phase_1.security import InputSanitizer

sanitizer = InputSanitizer()
safe_input = sanitizer.sanitize_string_input(user_input)
safe_path = sanitizer.sanitize_file_path(file_path)
```

### 2. Role-Based Access Control (RBAC)

The RBAC system provides fine-grained access control through the [AccessControlManager](file:///Users/doughnut/GitHub/microcosting_genomics/src/unimelb_phd_phase_1/security.py#L239-L366), [Role](file:///Users/doughnut/GitHub/microcosting_genomics/src/unimelb_phd_phase_1/security.py#L185-L236), and [User](file:///Users/doughnut/GitHub/microcosting_genomics/src/unimelb_phd_phase_1/security.py#L288-L330) classes.

#### Default Roles:
- **admin**: Full system access including configuration and user management
- **analyst**: Read data, run analysis, view reports, export data
- **viewer**: Read-only access to data and reports

#### Usage Example:
```python
from unimelb_phd_phase_1.security import AccessControlManager

access_control = AccessControlManager()
access_control.authenticate_user("researcher")
access_control.add_user_to_role("researcher", "analyst")


# Using decorator for function protection
@access_control.require_permission("run_analysis")
def perform_analysis():
    # This function requires 'run_analysis' permission
    pass
```

### 3. Audit Trail

The [AuditTrail](file:///Users/doughnut/GitHub/microcosting_genomics/src/unimelb_phd_phase_1/security.py#L369-L438) class tracks and logs all security-relevant events for compliance and monitoring.

#### Key Features:
- Event logging with timestamps and user information
- Filtering capabilities by user, event type, and time range
- File-based storage for persistent audit records

#### Usage Example:
```python
from unimelb_phd_phase_1.security import AuditTrail

audit_trail = AuditTrail("logs/audit.log")
audit_trail.log_event("login", "user123", "system", "User logged in", True)
audit_trail.log_event(
    "data_access", "user123", "cost_data.xlsx", "Accessed sensitive data", True
)
```

### 4. Secure Configuration Storage

The [SecureConfigStorage](file:///Users/doughnut/GitHub/microcosting_genomics/src/unimelb_phd_phase_1/security.py#L441-L522) class provides encrypted storage for sensitive configuration data.

#### Key Features:
- Encryption of sensitive configuration parameters
- Support for both encrypted and plaintext storage
- JSON-based configuration format for easy management

#### Usage Example:
```python
from unimelb_phd_phase_1.security import SecureConfigStorage

# Without encryption
storage = SecureConfigStorage("configs/config.json")
storage.save_config({"api_key": "secret_key", "database_url": "postgresql://..."})

# With encryption
encrypted_storage = SecureConfigStorage(
    "configs/secure_config.json", encryption_key="my_secret_key"
)
encrypted_storage.save_config(
    {"api_key": "secret_key", "database_url": "postgresql://..."}
)
```

## Security Best Practices

### 1. Input Validation
- Always sanitize user inputs before processing
- Validate all file paths to prevent directory traversal
- Check Excel cell references and sheet names for validity

### 2. Access Control
- Assign users to appropriate roles based on their responsibilities
- Use the `@require_permission` decorator to protect sensitive functions
- Regularly review user permissions and access logs

### 3. Audit Logging
- Log all security-relevant events including logins, data access, and configuration changes
- Store audit logs in a secure location with appropriate access controls
- Regularly review audit logs for suspicious activity

### 4. Configuration Security
- Store sensitive configuration parameters using encrypted storage
- Use different configuration files for different environments
- Never commit sensitive configuration data to version control

## Implementation Examples

### Complete Security Setup
```python
import os

from genomics_microcosting.security import setup_standard_security

# Set up all security components
sanitizer, access_control, audit_trail, secure_storage = setup_standard_security()

# Authenticate user
access_control.authenticate_user("researcher")
access_control.add_user_to_role("researcher", "analyst")

# Sanitize input
user_input = "<script>alert('xss')</script>../etc/passwd"
safe_input = sanitizer.sanitize_string_input(user_input)

# Log event
audit_trail.log_event(
    "data_processing", "researcher", "analysis.py", "Processing user input", True
)

# Save configuration securely
config_data = {
    "database_url": "postgresql://user:password@localhost/db",
    "api_key": os.environ["MICROCOSTING_API_KEY"],
}
secure_storage.save_config(config_data)
```

### Protected Function Example
```python
from unimelb_phd_phase_1.security import AccessControlManager

access_control = AccessControlManager()
access_control.authenticate_user("admin_user")
access_control.add_user_to_role("admin_user", "admin")


@access_control.require_permission("configure_system")
def update_system_configuration(new_config):
    """Update system configuration - requires admin privileges."""
    # This function can only be called by users with 'configure_system' permission
    pass
```

## Testing Security Features

The security module includes comprehensive unit tests to ensure all features work correctly:

- Input sanitization tests for various attack vectors
- Role-based access control tests for permission checking
- Audit trail tests for event logging and retrieval
- Secure configuration storage tests for encryption and decryption

Run tests with:
```bash
python -m pytest tests/test_security.py -v
```

## Compliance and Standards

The security implementation follows these standards and best practices:

- **OWASP Top 10**: Protection against injection, broken access control, and security misconfiguration
- **NIST Cybersecurity Framework**: Implementation of protective measures and detection capabilities
- **ISO 27001**: Information security management through access control and audit logging

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**: Ensure the user has been assigned to the appropriate role with the required permissions.

2. **Validation Errors**: Check that input data conforms to expected formats and does not contain invalid characters.

3. **Encryption Issues**: Verify that encryption keys are properly managed and stored securely.

### Debugging Tips

- Enable debug logging to see detailed information about security operations
- Check audit logs for information about access attempts and security events
- Use the test suite to verify that security components are functioning correctly

## Future Enhancements

Planned security enhancements include:

- Integration with external authentication systems (LDAP, OAuth)
- Advanced encryption using industry-standard libraries
- Real-time monitoring and alerting for security events
- Multi-factor authentication support