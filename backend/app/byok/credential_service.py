"""
CredentialService — encrypted storage + masking for BYOK API keys (spec §11, §18).

Guarantees:
  * The raw API key is never returned by any API, never logged, and never
    persisted in plaintext.
  * At rest the key is stored as an authenticated ciphertext string.
  * The UI only ever receives a masked rendering: sk-••••••••••••••••••••••1234

Two cipher backends are supported. AES-256-GCM is used when the `cryptography`
package is installed (recommended, and listed in requirements.txt). Otherwise a
stdlib-only construction is used: PBKDF2-HMAC-SHA256 key derivation, an
HMAC-SHA256 CTR keystream, and an encrypt-then-MAC HMAC-SHA256 tag. Both are
standard constructions — no primitives are hand-rolled.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
import stat
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

try:  # pragma: no cover - depends on deployment environment
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    _HAS_AESGCM = True
except Exception:  # pragma: no cover
    AESGCM = None  # type: ignore[assignment]
    _HAS_AESGCM = False


_PBKDF2_ROUNDS = 210_000
_MASK_CHAR = "•"  # •


class CredentialError(Exception):
    """Raised when a credential cannot be sealed or opened."""


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


class CredentialService:
    """Seals and opens BYOK credentials. Stateless apart from the master key."""

    def __init__(self) -> None:
        self._master: bytes | None = None

    # ── master key ────────────────────────────────────────────
    def _load_master_key(self) -> bytes:
        if self._master is not None:
            return self._master

        configured = (settings.BYOK_ENCRYPTION_KEY or "").strip()
        if configured:
            self._master = hashlib.sha256(configured.encode("utf-8")).digest()
            return self._master

        key_path = Path(settings.BYOK_KEY_FILE)
        try:
            if key_path.exists():
                material = key_path.read_text(encoding="utf-8").strip()
                if material:
                    self._master = hashlib.sha256(material.encode("utf-8")).digest()
                    return self._master
            generated = secrets.token_urlsafe(48)
            key_path.parent.mkdir(parents=True, exist_ok=True)
            key_path.write_text(generated + "\n", encoding="utf-8")
            os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
            logger.warning(
                "AURA_BYOK_ENCRYPTION_KEY is not set; generated a local master key "
                "file. Set AURA_BYOK_ENCRYPTION_KEY in production."
            )
            self._master = hashlib.sha256(generated.encode("utf-8")).digest()
            return self._master
        except OSError:
            # Last resort: ephemeral, process-scoped key. Stored credentials will
            # not survive a restart, which is safe (they simply need re-entry).
            logger.warning(
                "Unable to persist a BYOK master key; using an ephemeral key. "
                "Saved BYOK credentials will require re-entry after restart."
            )
            self._master = secrets.token_bytes(32)
            return self._master

    def _derive(self, salt: bytes, info: bytes) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256", self._load_master_key() + info, salt, _PBKDF2_ROUNDS, dklen=32
        )

    # ── stdlib fallback cipher ────────────────────────────────
    @staticmethod
    def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
        out = bytearray()
        counter = 0
        while len(out) < length:
            block = hmac.new(
                key, nonce + counter.to_bytes(8, "big"), hashlib.sha256
            ).digest()
            out.extend(block)
            counter += 1
        return bytes(out[:length])

    # ── public API ────────────────────────────────────────────
    def seal(self, plaintext: str, *, aad: str = "") -> str:
        """Encrypt a secret. Returns an opaque, storable token string."""
        if plaintext is None or plaintext == "":
            raise CredentialError("Cannot store an empty credential.")

        data = plaintext.encode("utf-8")
        salt = secrets.token_bytes(16)
        info = aad.encode("utf-8")

        if _HAS_AESGCM:
            key = self._derive(salt, info)
            nonce = secrets.token_bytes(12)
            ct = AESGCM(key).encrypt(nonce, data, info or None)
            return ":".join(["byok1", "aesgcm", _b64e(salt), _b64e(nonce), _b64e(ct)])

        enc_key = self._derive(salt, info + b"|enc")
        mac_key = self._derive(salt, info + b"|mac")
        nonce = secrets.token_bytes(16)
        ct = bytes(a ^ b for a, b in zip(data, self._keystream(enc_key, nonce, len(data))))
        tag = hmac.new(mac_key, nonce + ct + info, hashlib.sha256).digest()
        return ":".join(
            ["byok1", "hmacctr", _b64e(salt), _b64e(nonce), _b64e(ct), _b64e(tag)]
        )

    def open(self, token: str, *, aad: str = "") -> str:
        """Decrypt a token produced by :meth:`seal`."""
        if not token:
            raise CredentialError("Missing stored credential.")
        parts = token.split(":")
        if len(parts) < 4 or parts[0] != "byok1":
            raise CredentialError("Stored credential is malformed.")

        algo = parts[1]
        info = aad.encode("utf-8")
        try:
            if algo == "aesgcm":
                if not _HAS_AESGCM:
                    raise CredentialError(
                        "This credential needs the 'cryptography' package to be "
                        "installed. Re-enter the API key or install cryptography."
                    )
                salt, nonce, ct = (_b64d(parts[2]), _b64d(parts[3]), _b64d(parts[4]))
                key = self._derive(salt, info)
                return AESGCM(key).decrypt(nonce, ct, info or None).decode("utf-8")

            if algo == "hmacctr":
                salt, nonce, ct, tag = (
                    _b64d(parts[2]),
                    _b64d(parts[3]),
                    _b64d(parts[4]),
                    _b64d(parts[5]),
                )
                enc_key = self._derive(salt, info + b"|enc")
                mac_key = self._derive(salt, info + b"|mac")
                expected = hmac.new(mac_key, nonce + ct + info, hashlib.sha256).digest()
                if not hmac.compare_digest(expected, tag):
                    raise CredentialError("Stored credential failed integrity check.")
                keystream = self._keystream(enc_key, nonce, len(ct))
                return bytes(a ^ b for a, b in zip(ct, keystream)).decode("utf-8")
        except CredentialError:
            raise
        except Exception as exc:
            raise CredentialError(
                "Stored credential could not be decrypted. Re-enter the API key."
            ) from exc

        raise CredentialError(f"Unsupported credential format '{algo}'.")

    # ── masking ───────────────────────────────────────────────
    @staticmethod
    def mask(api_key: str) -> str:
        """Mask a key for display: sk-••••••••••••••••••••••1234."""
        if not api_key:
            return ""
        key = api_key.strip()
        prefix = ""
        for marker in ("sk-proj-", "sk-or-v1-", "sk-ant-", "sk-", "nvapi-", "gsk_", "AIza"):
            if key.startswith(marker):
                prefix = marker
                break
        tail = key[-4:] if len(key) > 8 else ""
        hidden = max(8, min(22, len(key) - len(prefix) - len(tail)))
        return f"{prefix}{_MASK_CHAR * hidden}{tail}"

    @staticmethod
    def fingerprint(api_key: str) -> str:
        """Short non-reversible id, useful for duplicate detection in the UI."""
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]

    @property
    def cipher_name(self) -> str:
        return "AES-256-GCM" if _HAS_AESGCM else "HMAC-SHA256-CTR + HMAC (stdlib)"


credential_service = CredentialService()
