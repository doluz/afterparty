"""Encrypt Partiful refresh tokens at rest.

By default a Fernet key (ENCRYPTION_KEY) encrypts them. Set KMS_KEY to use a
Google Cloud KMS key instead: then only the service account can decrypt, and the
database alone is useless to whoever reads it. Ciphertexts carry a one-byte
prefix, so the two kinds can never be confused.
"""

from __future__ import annotations

from functools import cache

from .config import settings

_KMS = b"k"
_FERNET = b"f"


@cache
def _kms():
    from google.cloud import kms

    return kms.KeyManagementServiceClient()


@cache
def _fernet():
    from cryptography.fernet import Fernet

    if not settings.encryption_key:
        raise RuntimeError("Set ENCRYPTION_KEY (a Fernet key) or KMS_KEY to store Partiful tokens")
    return Fernet(settings.encryption_key.encode())


def encrypt(plaintext: str) -> bytes:
    data = plaintext.encode()
    if settings.kms_key:
        resp = _kms().encrypt(request={"name": settings.kms_key, "plaintext": data})
        return _KMS + resp.ciphertext
    return _FERNET + _fernet().encrypt(data)


def decrypt(blob: bytes) -> str:
    blob = bytes(blob)
    kind, body = blob[:1], blob[1:]
    if kind == _KMS:
        resp = _kms().decrypt(request={"name": settings.kms_key, "ciphertext": body})
        return resp.plaintext.decode()
    if kind == _FERNET:
        return _fernet().decrypt(body).decode()
    raise ValueError("unknown ciphertext format")
