# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Reject tampered secret configuration instead of accepting altered plaintext."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from genomics_microcosting.security import SecureConfigStorage, SecurityError


def test_configuration_tampering_is_rejected(tmp_path: Path) -> None:
    """A valid-JSON bit flip must not survive encrypted configuration loading."""
    path = tmp_path / "secret.json"
    storage = SecureConfigStorage(
        str(path),
        encryption_key=Fernet.generate_key().decode(),
    )
    if not storage.save_config({"amount": 100}):
        raise AssertionError
    envelope = json.loads(path.read_text())
    payload = envelope["data"]
    try:
        ciphertext = bytearray.fromhex(payload)
    except ValueError:
        ciphertext = bytearray(payload.encode())
        ciphertext[len(ciphertext) // 2] ^= 1
        envelope["data"] = ciphertext.decode()
    else:
        position = json.dumps({"amount": 100}, indent=2).index("100")
        ciphertext[position] ^= ord("1") ^ ord("9")
        envelope["data"] = ciphertext.hex()
    path.write_text(json.dumps(envelope))
    with pytest.raises(SecurityError, match="authenticity"):
        storage.load_config()


def test_plaintext_requires_explicit_opt_in(tmp_path: Path) -> None:
    """Secure storage cannot silently persist unencrypted configuration."""
    path = tmp_path / "secret.json"
    with pytest.raises(SecurityError, match="Plaintext"):
        SecureConfigStorage(str(path)).save_config({"secret": "synthetic"})
    if path.exists():
        raise AssertionError


def test_legacy_ciphertext_requires_owner_migration(tmp_path: Path) -> None:
    """Never reinterpret or overwrite legacy encrypted data with a new key."""
    path = tmp_path / "legacy.json"
    original = json.dumps({"encrypted": True, "data": "00112233"})
    path.write_text(original)
    storage = SecureConfigStorage(
        str(path),
        encryption_key=Fernet.generate_key().decode(),
    )
    with pytest.raises(SecurityError, match="explicit migration"):
        storage.load_config()
    if path.read_text() != original:
        raise AssertionError


def test_encrypted_reader_rejects_plaintext_downgrade(tmp_path: Path) -> None:
    """An attacker cannot bypass authentication by changing the envelope mode."""
    path = tmp_path / "secret.json"
    path.write_text(json.dumps({"encrypted": False, "data": '{"amount":900}'}))
    storage = SecureConfigStorage(
        str(path),
        encryption_key=Fernet.generate_key().decode(),
    )
    with pytest.raises(SecurityError, match="downgrade"):
        storage.load_config()


def test_atomic_write_failure_preserves_previous_configuration(tmp_path: Path) -> None:
    """A failed final replacement retains the exact previous encrypted file."""
    path = tmp_path / "secret.json"
    storage = SecureConfigStorage(
        str(path),
        encryption_key=Fernet.generate_key().decode(),
    )
    if not storage.save_config({"amount": 100}):
        raise AssertionError
    before = path.read_bytes()
    with patch.object(Path, "replace", side_effect=OSError("synthetic I/O failure")):
        if storage.save_config({"amount": 200}):
            raise AssertionError
    if path.read_bytes() != before or list(tmp_path.glob("*.tmp")):
        raise AssertionError


def test_encryption_uses_fresh_tokens(tmp_path: Path) -> None:
    """Identical plaintext gets distinct authenticated tokens and round trips."""
    storage = SecureConfigStorage(
        str(tmp_path / "secret.json"),
        encryption_key=Fernet.generate_key().decode(),
    )
    first = storage.encrypt_data("synthetic-message")
    second = storage.encrypt_data("synthetic-message")
    if first == second:
        raise AssertionError
    if (
        storage.decrypt_data(first) != "synthetic-message"
        or storage.decrypt_data(second) != "synthetic-message"
    ):
        raise AssertionError
