# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Credential verification and retained session objects must fail closed."""

from secrets import token_urlsafe
from unittest.mock import Mock

from genomics_microcosting.security import AccessControlManager


def test_missing_verifier_rejects_identity() -> None:
    """A username and arbitrary password must never create an authenticated user."""
    manager = AccessControlManager()
    if manager.authenticate_user("unverified", "synthetic-untrusted-password"):
        raise AssertionError
    if manager.current_user is not None or manager.users:
        raise AssertionError


def test_logout_revokes_retained_user() -> None:
    """References held outside the manager must not remain authenticated."""
    accepted = token_urlsafe()
    manager = AccessControlManager(
        credential_verifier=lambda _name, supplied: supplied == accepted,
    )
    if not manager.authenticate_user("verified", accepted):
        raise AssertionError
    user = manager.current_user
    if user is None:
        raise AssertionError
    manager.logout_user()
    if user.authenticated or manager.current_user is not None:
        raise AssertionError


def test_rejected_login_revokes_previous_principal() -> None:
    """A failed identity switch cannot retain the old session's authority."""
    accepted = token_urlsafe()
    manager = AccessControlManager(
        credential_verifier=lambda _name, supplied: supplied == accepted,
    )
    if not manager.authenticate_user("verified", accepted):
        raise AssertionError
    user = manager.current_user
    if manager.authenticate_user("unverified", "incorrect-token"):
        raise AssertionError
    if manager.current_user is not None or "unverified" in manager.users:
        raise AssertionError
    if user is None or user.authenticated:
        raise AssertionError


def test_truthy_non_boolean_result_is_not_authentication() -> None:
    """A malformed provider result must fail its runtime bool contract."""
    manager = AccessControlManager(credential_verifier=Mock(return_value="denied"))
    if manager.authenticate_user("unverified", "synthetic-token"):
        raise AssertionError
