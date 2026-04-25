from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


@dataclass(frozen=True, slots=True)
class GatewayIdentity:
    id: str
    public_key: str


@dataclass(frozen=True, slots=True)
class GatewaySigningIdentity:
    id: str
    public_key: str
    private_key_pem: str


class GatewayIdentityService:
    def __init__(self, data_dir: Path) -> None:
        self._identity_path = data_dir / "settings" / "gateway-identity.json"

    def load(self) -> GatewayIdentity:
        identity = self._load_existing()
        if identity is not None:
            return identity
        return self._create_identity()

    def load_signing_identity(self) -> GatewaySigningIdentity:
        identity = self._load_existing_signing_identity()
        if identity is not None:
            return identity
        self._create_identity()
        identity = self._load_existing_signing_identity()
        if identity is None:
            raise RuntimeError("gateway signing identity could not be loaded")
        return identity

    def sign_payload(self, payload: str) -> tuple[str, str]:
        identity = self.load_signing_identity()
        private_key = self._private_key_from_pem(identity.private_key_pem)
        if private_key is None:
            raise ValueError("gateway signing identity private key is invalid")
        signature = private_key.sign(payload.encode("utf-8"))
        return identity.id, self._base64_url(signature)

    def _load_existing(self) -> GatewayIdentity | None:
        try:
            payload = json.loads(self._identity_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        modern_identity = self._load_openclaw_identity(payload)
        if modern_identity is not None:
            return modern_identity
        return self._load_legacy_identity(payload)

    def _load_existing_signing_identity(self) -> GatewaySigningIdentity | None:
        try:
            payload = json.loads(self._identity_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        modern_identity = self._load_openclaw_signing_identity(payload)
        if modern_identity is not None:
            return modern_identity
        return self._load_legacy_signing_identity(payload)

    def _load_openclaw_identity(self, payload: dict[str, Any]) -> GatewayIdentity | None:
        if payload.get("version") != 1:
            return None
        stored_device_id = payload.get("deviceId")
        public_key_pem = payload.get("publicKeyPem")
        private_key_pem = payload.get("privateKeyPem")
        if not isinstance(stored_device_id, str):
            return None
        if not isinstance(public_key_pem, str) or not isinstance(private_key_pem, str):
            return None
        public_key_bytes = self._public_key_bytes_from_pem(public_key_pem)
        if public_key_bytes is None:
            return None
        public_key = self._public_key_string(public_key_bytes)
        derived_device_id = self._identity_id(public_key_bytes)
        if stored_device_id != derived_device_id:
            self._write_openclaw_identity_file(
                device_id=derived_device_id,
                public_key_pem=public_key_pem,
                private_key_pem=private_key_pem,
                created_at_ms=payload.get("createdAtMs"),
            )
        return GatewayIdentity(id=derived_device_id, public_key=public_key)

    def _load_openclaw_signing_identity(
        self, payload: dict[str, Any]
    ) -> GatewaySigningIdentity | None:
        if payload.get("version") != 1:
            return None
        stored_device_id = payload.get("deviceId")
        private_key_pem = payload.get("privateKeyPem")
        if not isinstance(stored_device_id, str):
            return None
        if not isinstance(private_key_pem, str) or not private_key_pem.strip():
            return None
        private_key = self._private_key_from_pem(private_key_pem)
        if private_key is None:
            return None
        public_key_bytes = self._public_key_bytes_from_private_key(private_key)
        public_key = self._public_key_string(public_key_bytes)
        derived_device_id = self._identity_id(public_key_bytes)
        public_key_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")
        if stored_device_id != derived_device_id or payload.get("publicKeyPem") != public_key_pem:
            self._write_openclaw_identity_file(
                device_id=derived_device_id,
                public_key_pem=public_key_pem,
                private_key_pem=private_key_pem,
                created_at_ms=payload.get("createdAtMs"),
            )
        return GatewaySigningIdentity(
            id=derived_device_id,
            public_key=public_key,
            private_key_pem=private_key_pem,
        )

    def _load_legacy_identity(self, payload: dict[str, Any]) -> GatewayIdentity | None:
        private_key_value = payload.get("privateKey")
        if not isinstance(private_key_value, str) or not private_key_value.strip():
            return None
        try:
            private_key_bytes = base64.b64decode(private_key_value.encode("ascii"), validate=True)
            private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        except (ValueError, UnicodeEncodeError):
            return None
        public_key_bytes = self._public_key_bytes_from_private_key(private_key)
        public_key = self._public_key_string(public_key_bytes)
        identity_id = (
            str(payload.get("deviceId") or payload.get("id") or "").strip()
            or self._identity_id(public_key_bytes)
        )
        return GatewayIdentity(id=identity_id, public_key=public_key)

    def _load_legacy_signing_identity(
        self, payload: dict[str, Any]
    ) -> GatewaySigningIdentity | None:
        private_key_value = payload.get("privateKey")
        if not isinstance(private_key_value, str) or not private_key_value.strip():
            return None
        try:
            private_key_bytes = base64.b64decode(private_key_value.encode("ascii"), validate=True)
            private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        except (ValueError, UnicodeEncodeError):
            return None
        public_key_bytes = self._public_key_bytes_from_private_key(private_key)
        public_key = self._public_key_string(public_key_bytes)
        identity_id = (
            str(payload.get("deviceId") or payload.get("id") or "").strip()
            or self._identity_id(public_key_bytes)
        )
        private_key_pem = self._private_key_pem(private_key)
        self._write_openclaw_identity_file(
            device_id=identity_id,
            public_key_pem=private_key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("utf-8"),
            private_key_pem=private_key_pem,
            created_at_ms=payload.get("createdAtMs"),
        )
        return GatewaySigningIdentity(
            id=identity_id,
            public_key=public_key,
            private_key_pem=private_key_pem,
        )

    def _create_identity(self) -> GatewayIdentity:
        private_key = Ed25519PrivateKey.generate()
        public_key_bytes = self._public_key_bytes_from_private_key(private_key)
        public_key = self._public_key_string(public_key_bytes)
        identity = GatewayIdentity(
            id=self._identity_id(public_key_bytes),
            public_key=public_key,
        )
        self._write_identity_file(
            private_key,
            device_id=identity.id,
            created_at_ms=int(time.time() * 1000),
        )
        return identity

    def _write_openclaw_identity_file(
        self,
        *,
        device_id: str,
        public_key_pem: str,
        private_key_pem: str,
        created_at_ms: object | None,
    ) -> None:
        self._identity_path.parent.mkdir(parents=True, exist_ok=True)
        self._identity_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "deviceId": device_id,
                    "publicKeyPem": public_key_pem,
                    "privateKeyPem": private_key_pem,
                    "createdAtMs": created_at_ms,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_identity_file(
        self,
        private_key: Ed25519PrivateKey,
        *,
        device_id: str,
        created_at_ms: object | None,
    ) -> None:
        private_key_pem = self._private_key_pem(private_key)
        public_key_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")
        normalized_created_at_ms = (
            int(created_at_ms)
            if isinstance(created_at_ms, int | float) and int(created_at_ms) >= 0
            else int(time.time() * 1000)
        )
        self._identity_path.parent.mkdir(parents=True, exist_ok=True)
        self._identity_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "deviceId": device_id,
                    "publicKeyPem": public_key_pem,
                    "privateKeyPem": private_key_pem,
                    "createdAtMs": normalized_created_at_ms,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def _public_key_bytes_from_pem(self, public_key_pem: str) -> bytes | None:
        try:
            public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        except (TypeError, ValueError):
            return None
        if not isinstance(public_key, Ed25519PublicKey):
            return None
        return self._public_key_bytes_from_public_key(public_key)

    def _public_key_bytes_from_private_key(self, private_key: Ed25519PrivateKey) -> bytes:
        return self._public_key_bytes_from_public_key(private_key.public_key())

    def _public_key_bytes_from_public_key(self, public_key: Ed25519PublicKey) -> bytes:
        return public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def _public_key_string(self, public_key_bytes: bytes) -> str:
        return self._base64_url(public_key_bytes)

    def _identity_id(self, public_key_bytes: bytes) -> str:
        return hashlib.sha256(public_key_bytes).hexdigest()

    def _private_key_from_pem(self, private_key_pem: str) -> Ed25519PrivateKey | None:
        try:
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode("utf-8"),
                password=None,
            )
        except (TypeError, ValueError):
            return None
        return private_key if isinstance(private_key, Ed25519PrivateKey) else None

    def _private_key_pem(self, private_key: Ed25519PrivateKey) -> str:
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

    def _base64_url(self, value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
