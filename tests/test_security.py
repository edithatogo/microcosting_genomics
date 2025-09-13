"""Test cases for the Security module."""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from unimelb_phd_phase_1.security import (
    InputSanitizer, Role, User, AccessControlManager, 
    AuditTrail, SecureConfigStorage, SecurityError
)
from unimelb_phd_phase_1.input_validation import ValidationError


class TestInputSanitizer(unittest.TestCase):
    """Test cases for InputSanitizer."""

    def setUp(self):
        """Set up test fixtures."""
        self.sanitizer = InputSanitizer()

    def test_sanitize_string_input_valid(self):
        """Test sanitizing valid string input."""
        input_str = "Valid input string"
        sanitized = self.sanitizer.sanitize_string_input(input_str)
        self.assertEqual(sanitized, input_str)

    def test_sanitize_string_input_with_html(self):
        """Test sanitizing string input with HTML tags."""
        input_str = "<script>alert('xss')</script>Valid text"
        sanitized = self.sanitizer.sanitize_string_input(input_str)
        self.assertEqual(sanitized, "alert(xss)Valid text")

    def test_sanitize_string_input_with_sql_injection(self):
        """Test sanitizing string input with SQL injection attempts."""
        input_str = "'; DROP TABLE users; --"
        sanitized = self.sanitizer.sanitize_string_input(input_str)
        self.assertEqual(sanitized, "DROP TABLE users --")

    def test_sanitize_string_input_with_control_chars(self):
        """Test sanitizing string input with control characters."""
        input_str = "Text\x00with\x01control\x02characters"
        sanitized = self.sanitizer.sanitize_string_input(input_str)
        self.assertEqual(sanitized, "Textwithcontrolcharacters")

    def test_sanitize_string_input_too_long(self):
        """Test sanitizing string input that's too long."""
        input_str = "A" * 1500
        with self.assertRaises(ValidationError):
            self.sanitizer.sanitize_string_input(input_str, max_length=1000)

    def test_sanitize_file_path_valid(self):
        """Test sanitizing valid file path."""
        file_path = "data/cost_analysis.xlsx"
        sanitized = self.sanitizer.sanitize_file_path(file_path)
        self.assertEqual(sanitized, "data/cost_analysis.xlsx")

    def test_sanitize_file_path_with_traversal(self):
        """Test sanitizing file path with directory traversal."""
        file_path = "../../../etc/passwd"
        sanitized = self.sanitizer.sanitize_file_path(file_path)
        self.assertEqual(sanitized, "etc/passwd")

    def test_sanitize_file_path_with_backslashes(self):
        """Test sanitizing file path with backslashes."""
        file_path = "data\\cost_analysis.xlsx"
        sanitized = self.sanitizer.sanitize_file_path(file_path)
        self.assertEqual(sanitized, "data/cost_analysis.xlsx")

    def test_sanitize_excel_cell_reference_valid(self):
        """Test sanitizing valid Excel cell reference."""
        cell_ref = "a1"
        sanitized = self.sanitizer.sanitize_excel_cell_reference(cell_ref)
        self.assertEqual(sanitized, "A1")

    def test_sanitize_excel_cell_reference_invalid(self):
        """Test sanitizing invalid Excel cell reference."""
        cell_ref = "invalid_cell"
        with self.assertRaises(ValidationError):
            self.sanitizer.sanitize_excel_cell_reference(cell_ref)

    def test_sanitize_sheet_name_valid(self):
        """Test sanitizing valid sheet name."""
        sheet_name = "Detailed Table"
        sanitized = self.sanitizer.sanitize_sheet_name(sheet_name)
        self.assertEqual(sanitized, "Detailed Table")

    def test_sanitize_sheet_name_with_invalid_chars(self):
        """Test sanitizing sheet name with invalid characters."""
        sheet_name = "Sheet<Name>:With?Invalid*Chars"
        sanitized = self.sanitizer.sanitize_sheet_name(sheet_name)
        self.assertEqual(sanitized, "SheetNameWithInvalidChars")


class TestRoleAndUser(unittest.TestCase):
    """Test cases for Role and User classes."""

    def test_role_creation(self):
        """Test creating a role."""
        permissions = {"read_data", "write_data"}
        role = Role("analyst", permissions)
        self.assertEqual(role.name, "analyst")
        self.assertEqual(role.permissions, permissions)

    def test_role_has_permission(self):
        """Test checking role permissions."""
        role = Role("analyst", {"read_data", "write_data"})
        self.assertTrue(role.has_permission("read_data"))
        self.assertFalse(role.has_permission("delete_data"))

    def test_role_add_remove_permission(self):
        """Test adding and removing permissions from role."""
        role = Role("analyst", {"read_data"})
        self.assertFalse(role.has_permission("write_data"))
        
        role.add_permission("write_data")
        self.assertTrue(role.has_permission("write_data"))
        
        role.remove_permission("write_data")
        self.assertFalse(role.has_permission("write_data"))

    def test_user_creation(self):
        """Test creating a user."""
        user = User("researcher")
        self.assertEqual(user.username, "researcher")
        self.assertFalse(user.authenticated)
        self.assertIsNone(user.last_login)

    def test_user_has_permission(self):
        """Test checking user permissions."""
        role = Role("analyst", {"read_data", "write_data"})
        user = User("researcher", [role])
        self.assertTrue(user.has_permission("read_data"))
        self.assertFalse(user.has_permission("delete_data"))

    def test_user_add_remove_role(self):
        """Test adding and removing roles from user."""
        user = User("researcher")
        role = Role("analyst", {"read_data"})
        
        self.assertFalse(user.has_permission("read_data"))
        user.add_role(role)
        self.assertTrue(user.has_permission("read_data"))
        
        user.remove_role(role)
        self.assertFalse(user.has_permission("read_data"))


class TestAccessControlManager(unittest.TestCase):
    """Test cases for AccessControlManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.access_control = AccessControlManager()

    def test_default_roles_created(self):
        """Test that default roles are created."""
        self.assertIn("admin", self.access_control.roles)
        self.assertIn("analyst", self.access_control.roles)
        self.assertIn("viewer", self.access_control.roles)

    def test_authenticate_user_new(self):
        """Test authenticating a new user."""
        success = self.access_control.authenticate_user("new_user")
        self.assertTrue(success)
        self.assertIn("new_user", self.access_control.users)

    def test_authenticate_user_existing(self):
        """Test authenticating an existing user."""
        # First authentication
        self.access_control.authenticate_user("existing_user")
        
        # Second authentication
        success = self.access_control.authenticate_user("existing_user")
        self.assertTrue(success)

    def test_logout_user(self):
        """Test logging out user."""
        self.access_control.authenticate_user("test_user")
        self.assertIsNotNone(self.access_control.current_user)
        
        self.access_control.logout_user()
        self.assertIsNone(self.access_control.current_user)

    def test_add_user_to_role(self):
        """Test adding user to role."""
        success = self.access_control.add_user_to_role("test_user", "analyst")
        self.assertTrue(success)
        
        # Check that user has analyst permissions
        permissions = self.access_control.get_user_permissions("test_user")
        self.assertIn("read_data", permissions)
        self.assertIn("run_analysis", permissions)

    def test_add_user_to_nonexistent_role(self):
        """Test adding user to non-existent role."""
        success = self.access_control.add_user_to_role("test_user", "nonexistent_role")
        self.assertFalse(success)

    def test_get_user_permissions(self):
        """Test getting user permissions."""
        # Add user to analyst role
        self.access_control.add_user_to_role("test_user", "analyst")
        
        permissions = self.access_control.get_user_permissions("test_user")
        self.assertIsInstance(permissions, set)
        self.assertIn("read_data", permissions)
        self.assertIn("run_analysis", permissions)

    def test_require_permission_decorator_success(self):
        """Test require_permission decorator with sufficient permissions."""
        # Authenticate and give user admin role
        self.access_control.authenticate_user("admin_user")
        self.access_control.add_user_to_role("admin_user", "admin")
        
        # Define a protected function
        @self.access_control.require_permission("configure_system")
        def protected_function():
            return "success"
        
        # Should succeed
        result = protected_function()
        self.assertEqual(result, "success")

    def test_require_permission_decorator_failure(self):
        """Test require_permission decorator with insufficient permissions."""
        # Authenticate user with only viewer role
        self.access_control.authenticate_user("viewer_user")
        self.access_control.add_user_to_role("viewer_user", "viewer")
        
        # Define a protected function
        @self.access_control.require_permission("configure_system")
        def protected_function():
            return "success"
        
        # Should fail
        with self.assertRaises(SecurityError):
            protected_function()

    def test_require_permission_decorator_unauthenticated(self):
        """Test require_permission decorator with unauthenticated user."""
        # Define a protected function
        @self.access_control.require_permission("read_data")
        def protected_function():
            return "success"
        
        # Should fail
        with self.assertRaises(SecurityError):
            protected_function()


class TestAuditTrail(unittest.TestCase):
    """Test cases for AuditTrail."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_file = Path(self.temp_dir.name) / "audit.log"
        self.audit_trail = AuditTrail(str(self.log_file))

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_log_event(self):
        """Test logging an event."""
        self.audit_trail.log_event("login", "test_user", "system", "User logged in", True)
        
        self.assertEqual(len(self.audit_trail.events), 1)
        event = self.audit_trail.events[0]
        self.assertEqual(event["event_type"], "login")
        self.assertEqual(event["user"], "test_user")
        self.assertEqual(event["resource"], "system")
        self.assertEqual(event["details"], "User logged in")
        self.assertTrue(event["success"])

    def test_get_events_filtered(self):
        """Test getting filtered events."""
        # Log multiple events
        self.audit_trail.log_event("login", "user1", "system", "Login 1", True)
        self.audit_trail.log_event("data_access", "user1", "data.xlsx", "Access data", True)
        self.audit_trail.log_event("login", "user2", "system", "Login 2", True)
        
        # Filter by user
        user1_events = self.audit_trail.get_events(user="user1")
        self.assertEqual(len(user1_events), 2)
        
        # Filter by event type
        login_events = self.audit_trail.get_events(event_type="login")
        self.assertEqual(len(login_events), 2)
        
        # Filter by both
        user1_login_events = self.audit_trail.get_events(user="user1", event_type="login")
        self.assertEqual(len(user1_login_events), 1)

    def test_clear_events(self):
        """Test clearing events."""
        self.audit_trail.log_event("login", "test_user", "system", "User logged in", True)
        self.assertEqual(len(self.audit_trail.events), 1)
        
        self.audit_trail.clear_events()
        self.assertEqual(len(self.audit_trail.events), 0)

    def test_log_to_file(self):
        """Test logging events to file."""
        self.audit_trail.log_event("test_event", "test_user", "test_resource", "Test details", True)
        
        # Check that file was created and contains the event
        self.assertTrue(self.log_file.exists())
        
        with open(self.log_file, 'r') as f:
            content = f.read()
            self.assertIn("test_event", content)
            self.assertIn("test_user", content)


class TestSecureConfigStorage(unittest.TestCase):
    """Test cases for SecureConfigStorage."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = Path(self.temp_dir.name) / "config.json"
        self.encrypted_config_file = Path(self.temp_dir.name) / "encrypted_config.json"

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_save_and_load_config_no_encryption(self):
        """Test saving and loading config without encryption."""
        storage = SecureConfigStorage(str(self.config_file))
        
        config_data = {
            "parameter1": "value1",
            "parameter2": 42,
            "nested": {
                "subparam": "subvalue"
            }
        }
        
        # Save config
        success = storage.save_config(config_data)
        self.assertTrue(success)
        self.assertTrue(self.config_file.exists())
        
        # Load config
        loaded_config = storage.load_config()
        self.assertEqual(loaded_config, config_data)

    def test_save_and_load_config_with_encryption(self):
        """Test saving and loading config with encryption."""
        storage = SecureConfigStorage(str(self.encrypted_config_file), encryption_key="test_key")
        
        config_data = {
            "secret_parameter": "secret_value",
            "api_key": "super_secret_api_key_123"
        }
        
        # Save config
        success = storage.save_config(config_data)
        self.assertTrue(success)
        self.assertTrue(self.encrypted_config_file.exists())
        
        # Load config
        loaded_config = storage.load_config()
        self.assertEqual(loaded_config, config_data)

    def test_load_nonexistent_config(self):
        """Test loading config that doesn't exist."""
        storage = SecureConfigStorage(str(self.config_file))
        loaded_config = storage.load_config()
        self.assertIsNone(loaded_config)

    def test_encryption_decryption(self):
        """Test encryption and decryption functions."""
        storage = SecureConfigStorage(str(self.encrypted_config_file), encryption_key="test_key")
        
        original_data = "This is secret data that should be encrypted"
        encrypted_data = storage._encrypt_data(original_data)
        decrypted_data = storage._decrypt_data(encrypted_data)
        
        self.assertNotEqual(encrypted_data, original_data)
        self.assertEqual(decrypted_data, original_data)


if __name__ == '__main__':
    unittest.main()