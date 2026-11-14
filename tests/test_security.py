# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test cases for the Security module."""

import tempfile
import unittest
from pathlib import Path
from secrets import token_urlsafe

import pytest
from cryptography.fernet import Fernet

from genomics_microcosting.input_validation import ValidationError
from genomics_microcosting.security import (
    AccessControlManager,
    AuditTrail,
    InputSanitizer,
    Role,
    SecureConfigStorage,
    SecurityError,
    User,
)
from tests.checks import require_runtime_instance


class TestInputSanitizer(unittest.TestCase):
    """Test cases for InputSanitizer."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.sanitizer = InputSanitizer()

    def test_sanitize_string_input_valid(self) -> None:
        """Test sanitizing valid string input."""
        input_str = "Valid input string"
        sanitized = self.sanitizer.sanitize_string_input(input_str)
        if not ((sanitized) == (input_str)):
            raise AssertionError

    def test_sanitize_string_input_with_html(self) -> None:
        """Test sanitizing string input with HTML tags."""
        input_str = "<script>alert('xss')</script>Valid text"
        sanitized = self.sanitizer.sanitize_string_input(input_str)
        if not ((sanitized) == ("alert(xss)Valid text")):
            raise AssertionError

    def test_sanitize_string_input_with_sql_injection(self) -> None:
        """Test sanitizing string input with SQL injection attempts."""
        input_str = "'; DROP TABLE users; --"
        sanitized = self.sanitizer.sanitize_string_input(input_str)
        if not ((sanitized) == ("DROP TABLE users --")):
            raise AssertionError

    def test_sanitize_string_input_with_control_chars(self) -> None:
        """Test sanitizing string input with control characters."""
        input_str = "Text\x00with\x01control\x02characters"
        sanitized = self.sanitizer.sanitize_string_input(input_str)
        if not ((sanitized) == ("Textwithcontrolcharacters")):
            raise AssertionError

    def test_sanitize_string_input_too_long(self) -> None:
        """Test sanitizing string input that's too long."""
        input_str = "A" * 1500
        with pytest.raises(ValidationError):
            self.sanitizer.sanitize_string_input(input_str, max_length=1000)

    def test_sanitize_file_path_valid(self) -> None:
        """Test sanitizing valid file path."""
        file_path = "data/cost_analysis.xlsx"
        sanitized = self.sanitizer.sanitize_file_path(file_path)
        if not ((sanitized) == ("data/cost_analysis.xlsx")):
            raise AssertionError

    def test_sanitize_file_path_with_traversal(self) -> None:
        """Test sanitizing file path with directory traversal."""
        file_path = "../../../etc/passwd"
        sanitized = self.sanitizer.sanitize_file_path(file_path)
        if not ((sanitized) == ("etc/passwd")):
            raise AssertionError

    def test_sanitize_file_path_with_backslashes(self) -> None:
        """Test sanitizing file path with backslashes."""
        file_path = "data\\cost_analysis.xlsx"
        sanitized = self.sanitizer.sanitize_file_path(file_path)
        if not ((sanitized) == ("data/cost_analysis.xlsx")):
            raise AssertionError

    def test_sanitize_excel_cell_reference_valid(self) -> None:
        """Test sanitizing valid Excel cell reference."""
        cell_ref = "a1"
        sanitized = self.sanitizer.sanitize_excel_cell_reference(cell_ref)
        if not ((sanitized) == ("A1")):
            raise AssertionError

    def test_sanitize_excel_cell_reference_invalid(self) -> None:
        """Test sanitizing invalid Excel cell reference."""
        cell_ref = "invalid_cell"
        with pytest.raises(ValidationError):
            self.sanitizer.sanitize_excel_cell_reference(cell_ref)

    def test_sanitize_sheet_name_valid(self) -> None:
        """Test sanitizing valid sheet name."""
        sheet_name = "Detailed Table"
        sanitized = self.sanitizer.sanitize_sheet_name(sheet_name)
        if not ((sanitized) == ("Detailed Table")):
            raise AssertionError

    def test_sanitize_sheet_name_with_invalid_chars(self) -> None:
        """Test sanitizing sheet name with invalid characters."""
        sheet_name = "Sheet<Name>:With?Invalid*Chars"
        sanitized = self.sanitizer.sanitize_sheet_name(sheet_name)
        if not ((sanitized) == ("SheetNameWithInvalidChars")):
            raise AssertionError


class TestRoleAndUser(unittest.TestCase):
    """Test cases for Role and User classes."""

    def test_role_creation(self) -> None:
        """Test creating a role."""
        permissions = {"read_data", "write_data"}
        role = Role("analyst", permissions)
        if not ((role.name) == ("analyst")):
            raise AssertionError
        if not ((role.permissions) == (permissions)):
            raise AssertionError

    def test_role_has_permission(self) -> None:
        """Test checking role permissions."""
        role = Role("analyst", {"read_data", "write_data"})
        if not (role.has_permission("read_data")):
            raise AssertionError
        if role.has_permission("delete_data"):
            raise AssertionError

    def test_role_add_remove_permission(self) -> None:
        """Test adding and removing permissions from role."""
        role = Role("analyst", {"read_data"})
        if role.has_permission("write_data"):
            raise AssertionError

        role.add_permission("write_data")
        if not (role.has_permission("write_data")):
            raise AssertionError

        role.remove_permission("write_data")
        if role.has_permission("write_data"):
            raise AssertionError

    def test_user_creation(self) -> None:
        """Test creating a user."""
        user = User("researcher")
        if not ((user.username) == ("researcher")):
            raise AssertionError
        if user.authenticated:
            raise AssertionError
        if (user.last_login) is not None:
            raise AssertionError

    def test_user_has_permission(self) -> None:
        """Test checking user permissions."""
        role = Role("analyst", {"read_data", "write_data"})
        user = User("researcher", [role])
        if not (user.has_permission("read_data")):
            raise AssertionError
        if user.has_permission("delete_data"):
            raise AssertionError

    def test_user_add_remove_role(self) -> None:
        """Test adding and removing roles from user."""
        user = User("researcher")
        role = Role("analyst", {"read_data"})

        if user.has_permission("read_data"):
            raise AssertionError
        user.add_role(role)
        if not (user.has_permission("read_data")):
            raise AssertionError

        user.remove_role(role)
        if user.has_permission("read_data"):
            raise AssertionError


class TestAccessControlManager(unittest.TestCase):
    """Test cases for AccessControlManager."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.credential = token_urlsafe()
        self.access_control = AccessControlManager(
            credential_verifier=lambda _username, supplied: supplied == self.credential,
        )

    def test_default_roles_created(self) -> None:
        """Test that default roles are created."""
        if ("admin") not in (self.access_control.roles):
            raise AssertionError
        if ("analyst") not in (self.access_control.roles):
            raise AssertionError
        if ("viewer") not in (self.access_control.roles):
            raise AssertionError

    def test_authenticate_user_new(self) -> None:
        """Test authenticating a new user."""
        success = self.access_control.authenticate_user("new_user", self.credential)
        if not (success):
            raise AssertionError
        if ("new_user") not in (self.access_control.users):
            raise AssertionError

    def test_authenticate_user_existing(self) -> None:
        """Test authenticating an existing user."""
        # First authentication
        self.access_control.authenticate_user("existing_user", self.credential)

        # Second authentication
        success = self.access_control.authenticate_user(
            "existing_user",
            self.credential,
        )
        if not (success):
            raise AssertionError

    def test_logout_user(self) -> None:
        """Test logging out user."""
        self.access_control.authenticate_user("test_user", self.credential)
        if not ((self.access_control.current_user) is not None):
            raise AssertionError

        self.access_control.logout_user()
        require_runtime_instance(self.access_control.current_user, type(None))

    def test_add_user_to_role(self) -> None:
        """Test adding user to role."""
        success = self.access_control.add_user_to_role("test_user", "analyst")
        if not (success):
            raise AssertionError

        # Check that user has analyst permissions
        permissions = self.access_control.get_user_permissions("test_user")
        if ("read_data") not in (permissions):
            raise AssertionError
        if ("run_analysis") not in (permissions):
            raise AssertionError

    def test_add_user_to_nonexistent_role(self) -> None:
        """Test adding user to non-existent role."""
        success = self.access_control.add_user_to_role("test_user", "nonexistent_role")
        if success:
            raise AssertionError

    def test_get_user_permissions(self) -> None:
        """Test getting user permissions."""
        # Add user to analyst role
        self.access_control.add_user_to_role("test_user", "analyst")

        permissions = self.access_control.get_user_permissions("test_user")
        require_runtime_instance(permissions, set)
        if ("read_data") not in (permissions):
            raise AssertionError
        if ("run_analysis") not in (permissions):
            raise AssertionError

    def test_require_permission_decorator_success(self) -> None:
        """Test require_permission decorator with sufficient permissions."""
        # Authenticate and give user admin role
        self.access_control.authenticate_user("admin_user", self.credential)
        self.access_control.add_user_to_role("admin_user", "admin")

        # Define a protected function
        @self.access_control.require_permission("configure_system")
        def protected_function() -> str:
            return "success"

        # Should succeed
        result = protected_function()
        if not ((result) == ("success")):
            raise AssertionError

    def test_require_permission_decorator_failure(self) -> None:
        """Test require_permission decorator with insufficient permissions."""
        # Authenticate user with only viewer role
        self.access_control.authenticate_user("viewer_user", self.credential)
        self.access_control.add_user_to_role("viewer_user", "viewer")

        # Define a protected function
        @self.access_control.require_permission("configure_system")
        def protected_function() -> str:
            return "success"

        # Should fail
        with pytest.raises(SecurityError):
            protected_function()

    def test_require_permission_decorator_unauthenticated(self) -> None:
        """Test require_permission decorator with unauthenticated user."""

        # Define a protected function
        @self.access_control.require_permission("read_data")
        def protected_function() -> str:
            return "success"

        # Should fail
        with pytest.raises(SecurityError):
            protected_function()


class TestAuditTrail(unittest.TestCase):
    """Test cases for AuditTrail."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_file = Path(self.temp_dir.name) / "audit.log"
        self.audit_trail = AuditTrail(str(self.log_file))

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_log_event(self) -> None:
        """Test logging an event."""
        self.audit_trail.log_event(
            "login",
            "test_user",
            "system",
            "User logged in",
            success=True,
        )

        if not ((len(self.audit_trail.events)) == (1)):
            raise AssertionError
        event = self.audit_trail.events[0]
        if not ((event["event_type"]) == ("login")):
            raise AssertionError
        if not ((event["user"]) == ("test_user")):
            raise AssertionError
        if not ((event["resource"]) == ("system")):
            raise AssertionError
        if not ((event["details"]) == ("User logged in")):
            raise AssertionError
        if not (event["success"]):
            raise AssertionError

    def test_get_events_filtered(self) -> None:
        """Test getting filtered events."""
        # Log multiple events
        self.audit_trail.log_event("login", "user1", "system", "Login 1", success=True)
        self.audit_trail.log_event(
            "data_access",
            "user1",
            "data.xlsx",
            "Access data",
            success=True,
        )
        self.audit_trail.log_event("login", "user2", "system", "Login 2", success=True)

        # Filter by user
        user1_events = self.audit_trail.get_events(user="user1")
        expected_user_events = 2
        if not ((len(user1_events)) == expected_user_events):
            raise AssertionError

        # Filter by event type
        login_events = self.audit_trail.get_events(event_type="login")
        expected_login_events = 2
        if not ((len(login_events)) == expected_login_events):
            raise AssertionError

        # Filter by both
        user1_login_events = self.audit_trail.get_events(
            user="user1",
            event_type="login",
        )
        if not ((len(user1_login_events)) == (1)):
            raise AssertionError

    def test_clear_events(self) -> None:
        """Test clearing events."""
        self.audit_trail.log_event(
            "login",
            "test_user",
            "system",
            "User logged in",
            success=True,
        )
        if not ((len(self.audit_trail.events)) == (1)):
            raise AssertionError

        self.audit_trail.clear_events()
        if not ((len(self.audit_trail.events)) == (0)):
            raise AssertionError

    def test_log_to_file(self) -> None:
        """Test logging events to file."""
        self.audit_trail.log_event(
            "test_event",
            "test_user",
            "test_resource",
            "Test details",
            success=True,
        )

        # Check that file was created and contains the event
        if not (self.log_file.exists()):
            raise AssertionError

        with self.log_file.open() as f:
            content = f.read()
            if ("test_event") not in (content):
                raise AssertionError
            if ("test_user") not in (content):
                raise AssertionError


class TestSecureConfigStorage(unittest.TestCase):
    """Test cases for SecureConfigStorage."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = Path(self.temp_dir.name) / "config.json"
        self.encrypted_config_file = Path(self.temp_dir.name) / "encrypted_config.json"

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_save_and_load_config_no_encryption(self) -> None:
        """Test saving and loading config without encryption."""
        storage = SecureConfigStorage(str(self.config_file), allow_plaintext=True)

        config_data = {
            "parameter1": "value1",
            "parameter2": 42,
            "nested": {
                "subparam": "subvalue",
            },
        }

        # Save config
        success = storage.save_config(config_data)
        if not (success):
            raise AssertionError
        if not (self.config_file.exists()):
            raise AssertionError

        # Load config
        loaded_config = storage.load_config()
        if not ((loaded_config) == (config_data)):
            raise AssertionError

    def test_save_and_load_config_with_encryption(self) -> None:
        """Test saving and loading config with encryption."""
        storage = SecureConfigStorage(
            str(self.encrypted_config_file),
            encryption_key=Fernet.generate_key().decode(),
        )

        config_data = {
            "secret_parameter": "secret_value",
            "api_key": "super_secret_api_key_123",
        }

        # Save config
        success = storage.save_config(config_data)
        if not (success):
            raise AssertionError
        if not (self.encrypted_config_file.exists()):
            raise AssertionError

        # Load config
        loaded_config = storage.load_config()
        if not ((loaded_config) == (config_data)):
            raise AssertionError

    def test_load_nonexistent_config(self) -> None:
        """Test loading config that doesn't exist."""
        storage = SecureConfigStorage(str(self.config_file), allow_plaintext=True)
        loaded_config = storage.load_config()
        if (loaded_config) is not None:
            raise AssertionError

    def test_encryption_decryption(self) -> None:
        """Test encryption and decryption functions."""
        storage = SecureConfigStorage(
            str(self.encrypted_config_file),
            encryption_key=Fernet.generate_key().decode(),
        )

        original_data = "This is secret data that should be encrypted"
        encrypted_data = storage.encrypt_data(original_data)
        decrypted_data = storage.decrypt_data(encrypted_data)

        if not ((encrypted_data) != (original_data)):
            raise AssertionError
        if not ((decrypted_data) == (original_data)):
            raise AssertionError


if __name__ == "__main__":
    unittest.main()
