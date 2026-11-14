# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Security module for genomics microcosting analysis.

This module provides comprehensive security capabilities including
input sanitization, role-based access control, audit trail tracking,
and secure configuration storage.
"""

import json
import logging
import os
import re
import tempfile
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import TypedDict, Unpack
lazy from collections.abc import Callable, Mapping

from pydantic import ConfigDict, TypeAdapter
from pydantic import ValidationError as ModelValidationError
lazy from cryptography.fernet import Fernet, InvalidToken

from .input_validation import InputValidator, ValidationError
from .logging_config import get_logger

logger = get_logger(__name__)
MAX_INPUT_NAME_LENGTH = 255


class SecurityError(Exception):
    """Custom exception for security-related errors."""


class InputSanitizer:
    """Normalize validated inputs; context-specific escaping remains required."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Initialize the input sanitizer.

        Args:
            logger: Logger instance (optional)

        """
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.validator = InputValidator(self.logger)

    def sanitize_string_input(self, value: str, max_length: int = 1000) -> str:
        """Normalize validated display text without promising contextual escaping.

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
            sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", value)

            # Remove common injection patterns
            sanitized = re.sub(r"<.*?>", "", sanitized)  # Remove HTML tags
            sanitized = re.sub(r'["\']', "", sanitized)  # Remove quotes
            sanitized = re.sub(
                r"[;`|&]",
                "",
                sanitized,
            )  # Remove command injection characters

            # Limit consecutive whitespace
            sanitized = re.sub(r"\s+", " ", sanitized).strip()

            self.logger.debug(
                "Sanitized string input: %s -> %s chars",
                len(value),
                len(sanitized),
            )
        except ValidationError, TypeError, ValueError, AttributeError:
            self.logger.warning("Invalid input rejected")
            message = "Invalid input"
            raise ValidationError(message) from None
        else:
            return sanitized

    def sanitize_file_path(self, file_path: str) -> str:
        """Normalize a path string; callers must still enforce allowed roots.

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
            sanitized = file_path.replace("\x00", "")

            # Remove directory traversal sequences
            sanitized = sanitized.replace("../", "").replace("..\\", "")
            sanitized = sanitized.replace("./", "").replace(".\\", "")

            # Normalize path separators
            sanitized = sanitized.replace("\\", "/")

            # Remove multiple consecutive slashes
            sanitized = re.sub(r"/+", "/", sanitized)

            # Ensure path doesn't start with /
            sanitized = sanitized.removeprefix("/")

            self.logger.debug("Sanitized file path")
        except ValidationError, TypeError, ValueError, AttributeError:
            self.logger.warning("Invalid file path rejected")
            message = "Invalid file path"
            raise ValidationError(message) from None
        else:
            return sanitized

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

            self.logger.debug("Sanitized cell reference")
        except ValidationError, TypeError, ValueError, AttributeError:
            self.logger.warning("Invalid cell reference rejected")
            message = "Invalid cell reference"
            raise ValidationError(message) from None
        else:
            return sanitized

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
            sanitized = re.sub(r'[<>"|:*?/\\]', "", sheet_name)

            # Limit length
            if len(sanitized) > MAX_INPUT_NAME_LENGTH:
                sanitized = sanitized[:MAX_INPUT_NAME_LENGTH]

            # Remove leading/trailing whitespace
            sanitized = sanitized.strip()

            # Then validate the sanitized input
            self.validator.validate_sheet_name(sanitized)

            self.logger.debug("Sanitized sheet name")
        except ValidationError, TypeError, ValueError, AttributeError:
            self.logger.warning("Invalid sheet name rejected")
            message = "Invalid sheet name"
            raise ValidationError(message) from None
        else:
            return sanitized


class Role:
    """Represents a user role with specific permissions."""

    def __init__(self, name: str, permissions: set[str]) -> None:
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

    def add_permission(self, permission: str) -> None:
        """Add a permission to the role.

        Args:
            permission: Permission to add

        """
        self.permissions.add(permission)

    def remove_permission(self, permission: str) -> None:
        """Remove a permission from the role.

        Args:
            permission: Permission to remove

        """
        self.permissions.discard(permission)


class User:
    """Represents a user with roles and authentication status."""

    def __init__(self, username: str, roles: list[Role] | None = None) -> None:
        """Initialize a user.

        Args:
            username: Username
            roles: List of roles for this user

        """
        self.username = username
        self.roles = roles or []
        self.authenticated = False
        self.last_login: str | None = None

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission.

        Args:
            permission: Permission to check

        Returns:
            True if user has permission, False otherwise

        """
        return any(role.has_permission(permission) for role in self.roles)

    def add_role(self, role: Role) -> None:
        """Add a role to the user.

        Args:
            role: Role to add

        """
        if role not in self.roles:
            self.roles.append(role)

    def remove_role(self, role: Role) -> None:
        """Remove a role from the user.

        Args:
            role: Role to remove

        """
        if role in self.roles:
            self.roles.remove(role)


class AccessControlManager:
    """Manages role-based access control for the application."""

    def __init__(
        self,
        logger: logging.Logger | None = None,
        *,
        credential_verifier: Callable[[str, str | None], bool] | None = None,
    ) -> None:
        """Initialize the access control manager.

        Args:
            logger: Logger instance (optional)
            credential_verifier: Trusted verifier. Authentication is denied
                when it is absent.

        """
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.credential_verifier = credential_verifier
        self.roles: dict[str, Role] = {}
        self.users: dict[str, User] = {}
        self.current_user: User | None = None

        # Create default roles
        self._create_default_roles()

    def _create_default_roles(self) -> None:
        """Create default roles for the application."""
        # Administrator role with all permissions
        admin_role = Role(
            "admin",
            {
                "read_data",
                "write_data",
                "delete_data",
                "configure_system",
                "manage_users",
                "access_sensitive_data",
                "export_data",
                "run_analysis",
                "view_reports",
            },
        )
        self.roles["admin"] = admin_role

        # Analyst role with analysis permissions
        analyst_role = Role(
            "analyst",
            {
                "read_data",
                "run_analysis",
                "view_reports",
                "export_data",
            },
        )
        self.roles["analyst"] = analyst_role

        # Viewer role with read-only permissions
        viewer_role = Role(
            "viewer",
            {
                "read_data",
                "view_reports",
            },
        )
        self.roles["viewer"] = viewer_role

        self.logger.info("Created default roles: admin, analyst, viewer")

    def authenticate_user(self, username: str, password: str | None = None) -> bool:
        """Authenticate only after explicit trusted credential verification.

        No verifier means no authentication. Verifier exceptions propagate after
        revoking any previous principal; credentials are never logged here.
        """
        self.logout_user()
        verifier = self.credential_verifier
        if verifier is None or verifier(username, password) is not True:
            self.logger.warning("Credential verification did not establish an identity")
            return False
        if username not in self.users:
            self.users[username] = User(username)
        user = self.users[username]
        user.authenticated = True
        user.last_login = datetime.now(UTC).isoformat()
        self.current_user = user
        self.logger.info("User authenticated: %r", username)
        return True

    def logout_user(self) -> None:
        """Revoke both the current principal and retained user authentication flags."""
        if self.current_user:
            self.current_user.authenticated = False
            self.logger.info("User logged out: %r", self.current_user.username)
            self.current_user = None

    def require_permission[**P, R](
        self,
        permission: str,
    ) -> Callable[[Callable[P, R]], Callable[P, R]]:
        """Require an authenticated principal with the specified permission.

        Args:
            permission: Required permission

        Returns:
            Decorator function

        """

        def decorator(func: Callable[P, R]) -> Callable[P, R]:
            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                if not self.current_user:
                    message = "User not authenticated"
                    raise SecurityError(message)

                if not self.current_user.has_permission(permission):
                    message = (
                        f"User {self.current_user.username} "
                        f"lacks permission: {permission}"
                    )
                    raise SecurityError(
                        message,
                    )

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
        if username not in self.users:
            self.users[username] = User(username)

        if role_name not in self.roles:
            self.logger.error("Role %s not found", role_name)
            return False

        user = self.users[username]
        role = self.roles[role_name]

        user.add_role(role)
        self.logger.info("Added user %s to role %s", username, role_name)
        return True

    def get_user_permissions(self, username: str) -> set[str]:
        """Get all permissions for a user.

        Args:
            username: Username

        Returns:
            Set of permissions

        """
        if username not in self.users:
            return set()

        user = self.users[username]
        permissions: set[str] = set()
        for role in user.roles:
            permissions.update(role.permissions)

        return permissions


class AuditEvent(TypedDict):
    """One complete local security event, including explicit success status."""

    timestamp: str
    event_type: str
    user: str | None
    resource: str
    details: str | None
    success: bool


def _audit_success(value: object) -> bool:
    """Require a real boolean rather than truthiness for audit outcomes."""
    if not isinstance(value, bool):
        message = "Audit success must be an explicit boolean"
        raise TypeError(message)
    return value


class AuditOptions(TypedDict, total=False):
    """Keyword status options with the legacy positional form retained."""

    success: bool


class AuditTrail:
    """Tracks and logs security-relevant events."""

    def __init__(
        self,
        log_file: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the audit trail.

        Args:
            log_file: File to store audit logs (optional)
            logger: Logger instance (optional)

        """
        self.log_file = log_file
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.events: list[AuditEvent] = []

    def log_event(
        self,
        event_type: str,
        user: str | None,
        resource: str,
        details: str | None = None,
        *legacy_success: bool,
        **options: Unpack[AuditOptions],
    ) -> None:
        """Log a security-relevant event.

        Args:
            event_type: Type of event (e.g., 'login', 'access', 'modification')
            user: Username (if authenticated)
            resource: Resource being accessed or modified
            details: Additional details about the event
            success: Whether the event was successful
            *legacy_success: Preserve one positional success flag for existing callers.

        """
        if len(legacy_success) > 1 or (legacy_success and "success" in options):
            message = "Audit success was supplied more than once"
            raise TypeError(message)
        if options.keys() - {"success"}:
            message = "Unexpected audit event option"
            raise TypeError(message)
        success = _audit_success(
            legacy_success[0] if legacy_success else options.get("success", True),
        )
        event: AuditEvent = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "user": user,
            "resource": resource,
            "details": details,
            "success": success,
        }

        self.events.append(event)

        # Log to file if specified
        if self.log_file:
            try:
                with Path(self.log_file).open("a") as f:
                    f.write(json.dumps(event) + "\n")
            except OSError:
                self.logger.exception("Audit file persistence failed")

        # Log to standard logger
        log_level = logging.INFO if success else logging.WARNING
        self.logger.log(
            log_level,
            "Audit: %s by %r on %r - %s",
            event_type,
            user,
            resource,
            success,
        )

    def get_events(
        self,
        user: str | None = None,
        event_type: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> list[AuditEvent]:
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
            filtered_events = [
                e for e in filtered_events if e.get("event_type") == event_type
            ]

        if start_time:
            filtered_events = [
                e for e in filtered_events if e["timestamp"] >= start_time
            ]

        if end_time:
            filtered_events = [e for e in filtered_events if e["timestamp"] <= end_time]

        return [event.copy() for event in filtered_events]

    def clear_events(self) -> None:
        """Clear all audit events."""
        self.events.clear()
        self.logger.info("Audit events cleared")


_CONFIG_OBJECT = TypeAdapter(dict[str, object], config=ConfigDict(strict=True))


class SecureConfigStorage:
    """Store versioned authenticated configuration with atomic file replacement.

    Existing legacy XOR data requires explicit migration by its owner. Plaintext
    is permitted only by explicit opt-in for nonsecret configuration.
    """

    def __init__(
        self,
        config_file: str,
        encryption_key: str | None = None,
        logger: logging.Logger | None = None,
        *,
        allow_plaintext: bool = False,
    ) -> None:
        """Validate caller-owned keys before touching the destination directory."""
        self.config_file = Path(config_file)
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.allow_plaintext = allow_plaintext
        self._cipher: Fernet | None = None
        if encryption_key is not None:
            if allow_plaintext:
                message = "Encrypted and plaintext modes cannot be combined"
                raise SecurityError(message)
            try:
                self._cipher = Fernet(encryption_key.encode("ascii"))
            except ImportError:
                message = (
                    "Install the security extra to use authenticated configuration"
                )
                raise SecurityError(message) from None
            except ValueError, UnicodeEncodeError:
                message = (
                    "A valid Fernet key is required; "
                    "legacy keys need explicit migration"
                )
                raise SecurityError(message) from None
        self.config_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    def encrypt_data(self, data: str) -> str:
        """Encrypt UTF-8 data with a fresh authenticated token."""
        if self._cipher is None:
            message = "Authenticated encryption requires a key"
            raise SecurityError(message)
        return self._cipher.encrypt(data.encode("utf-8")).decode("ascii")

    def decrypt_data(self, encrypted_data: str) -> str:
        """Verify authenticity before returning any decrypted data."""
        if self._cipher is None:
            message = "Authenticated decryption requires a key"
            raise SecurityError(message)
        try:
            return self._cipher.decrypt(encrypted_data.encode("ascii")).decode("utf-8")
        except InvalidToken, UnicodeError:
            message = "Configuration authenticity check failed"
            raise SecurityError(message) from None

    def _encrypt_data(self, data: str) -> str:
        """Retain the compatibility entry point without legacy XOR behavior."""
        return self.encrypt_data(data)

    def _decrypt_data(self, encrypted_data: str) -> str:
        """Retain the compatibility entry point with authentication required."""
        return self.decrypt_data(encrypted_data)

    def save_config(self, config_data: Mapping[str, object]) -> bool:
        """Replace configuration atomically; return false only for I/O failure."""
        config_json = json.dumps(dict(config_data), indent=2, default=str)
        if self._cipher is not None:
            envelope = {
                "encrypted": True,
                "scheme": "fernet-v1",
                "data": self.encrypt_data(config_json),
            }
        elif self.allow_plaintext:
            envelope = {"encrypted": False, "data": config_json}
        else:
            message = "Plaintext storage requires explicit nonsecret opt-in"
            raise SecurityError(message)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.config_file.parent,
                prefix=f".{self.config_file.name}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                if os.name == "posix":
                    os.fchmod(stream.fileno(), 0o600)
                json.dump(envelope, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.config_file)
            temporary = None
        except OSError:
            self.logger.exception("Configuration persistence failed")
            return False
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self.logger.info("Configuration saved")
        return True

    def load_config(self) -> dict[str, object] | None:
        """Reject legacy, downgraded or unauthenticated envelopes before parsing."""
        if not self.config_file.exists():
            return None
        try:
            stored = _CONFIG_OBJECT.validate_json(
                self.config_file.read_text(encoding="utf-8"),
            )
        except ModelValidationError, UnicodeError:
            message = "Configuration envelope is invalid"
            raise SecurityError(message) from None
        payload = stored.get("data")
        if not isinstance(payload, str):
            message = "Configuration payload is invalid"
            raise SecurityError(message)
        if stored.get("encrypted") is True:
            if stored.get("scheme") != "fernet-v1":
                message = "Legacy encrypted configuration requires explicit migration"
                raise SecurityError(message)
            decoded = self.decrypt_data(payload)
        elif (
            stored.get("encrypted") is False
            and self.allow_plaintext
            and self._cipher is None
        ):
            decoded = payload
        else:
            message = "Configuration encryption downgrade or unsupported mode"
            raise SecurityError(message)
        try:
            return _CONFIG_OBJECT.validate_json(decoded)
        except ModelValidationError:
            message = "Configuration data is invalid"
            raise SecurityError(message) from None


# Convenience functions
def setup_standard_security(
    logger: logging.Logger | None = None,
) -> tuple[InputSanitizer, AccessControlManager, AuditTrail, SecureConfigStorage]:
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


def main() -> None:
    """Demonstrate authenticated configuration only in a disposable directory."""
    logging.basicConfig(level=logging.INFO)
    with tempfile.TemporaryDirectory(prefix="microcosting-security-demo-") as directory:
        key = Fernet.generate_key().decode("ascii")
        storage = SecureConfigStorage(str(Path(directory) / "demo.json"), key)
        payload = {"analysis_parameters": {"iterations": 1000}}
        if not storage.save_config(payload) or storage.load_config() != payload:
            message = "Synthetic security demonstration failed"
            raise SecurityError(message)
        logger.info("Synthetic authenticated-configuration demonstration passed")


if __name__ == "__main__":
    main()
