# Security policy

## Supported configuration

Use the locked environment on Python 3.15.1. Static, package, privacy and hosted
qualification gates are recorded in Conductor; local test success does not establish
production deployment or scientific acceptance.

## Authentication

AccessControlManager requires a caller-supplied trusted credential verifier.
Without one, authentication is denied. Verifier failures revoke any previous
principal. This adapter is not an identity provider or a production web session
implementation; deployment must qualify its identity, authorization and session
boundaries separately.

## Configuration encryption and migration

Install the `security` extra for authenticated configuration storage. Supply an
owner-managed Fernet key; do not put keys or credentials in source, logs or the
configuration envelope. Key generation and custody are the owner's responsibility.
There is no automatic key rotation, legacy decryption or file migration.

Legacy XOR envelopes and arbitrary password strings are rejected. Retain the
original files and keys until their owner explicitly authorizes and verifies a
migration in an isolated location. Authenticated readers reject tampered tokens
and plaintext downgrade attempts. Plaintext storage requires explicit
`allow_plaintext=True` and is only for nonsecret configuration; encrypted and
plaintext modes cannot be combined.

Writes use a same-directory temporary file and atomic replacement. Files receive
0600 permissions on POSIX; this is not a claim of Windows ACL or power-loss
qualification. A failed replacement retains the previous destination. The local
module demonstration operates in a disposable directory and does not overwrite
existing configuration.

## Reporting vulnerabilities

Do not put credentials, patient information, workbooks or private evidence in
public issues. Use GitHub private vulnerability reporting when available, or an
already established private channel with the maintainer. No new contact endpoint
or service activation is implied by this document.
