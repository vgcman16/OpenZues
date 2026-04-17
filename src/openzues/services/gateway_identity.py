from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


@dataclass(frozen=True, slots=True)
class GatewayIdentity:
    id: str
    public_key: str


class GatewayIdentityService:
    def __init__(self, data_dir: Path) -> None:
        self._identity_path = data_dir / "settings" / "gateway-identity.json"

    def load(self) -> GatewayIdentity:
        identity = self._load_existing()
        if identity is not None:
            return identity
        return self._create_identity()

    def _load_existing(self) -> GatewayIdentity | None:
        try:
            payload = json.loads(self._identity_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        private_key_value = payload.get("privateKey")
        if not isinstance(private_key_value, str) or not private_key_value.strip():
            return None
        try:
            private_key_bytes = base64.b64decode(private_key_value.encode("ascii"), validate=True)
            private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        except (ValueError, UnicodeEncodeError):
            return None
        public_key = self._public_key_string(private_key)
        identity_id = str(payload.get("id") or "").strip() or self._identity_id(public_key)
        return GatewayIdentity(id=identity_id, public_key=public_key)

    def _create_identity(self) -> GatewayIdentity:
        private_key = Ed25519PrivateKey.generate()
        private_key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_key = self._public_key_string(private_key)
        identity = GatewayIdentity(
            id=self._identity_id(public_key),
            public_key=public_key,
        )
        self._identity_path.parent.mkdir(parents=True, exist_ok=True)
        self._identity_path.write_text(
            json.dumps(
                {
                    "id": identity.id,
                    "privateKey": base64.b64encode(private_key_bytes).decode("ascii"),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return identity

    def _public_key_string(self, private_key: Ed25519PrivateKey) -> str:
        public_key_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return base64.b64encode(public_key_bytes).decode("ascii")

    def _identity_id(self, public_key: str) -> str:
        fingerprint = hashlib.sha256(public_key.encode("utf-8")).hexdigest()[:24]
        return f"gateway-{fingerprint}"
