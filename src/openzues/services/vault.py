from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from openzues.database import Database
from openzues.schemas import VaultSecretCreate, VaultSecretView
from openzues.settings import Settings


def mask_secret(value: str | None) -> tuple[bool, str | None]:
    if not value:
        return False, None
    if len(value) <= 4:
        return True, "****"
    return True, f"****{value[-4:]}"


class VaultDecryptionError(RuntimeError):
    pass


class VaultService:
    def __init__(self, database: Database, app_settings: Settings) -> None:
        self.database = database
        self.settings = app_settings
        self._fernet: Fernet | None = None

    def initialize(self) -> None:
        self._get_fernet()

    def _get_fernet(self) -> Fernet:
        if self._fernet is not None:
            return self._fernet

        if self.settings.master_key:
            key = self.settings.master_key.strip().encode("utf-8")
        else:
            key = self._read_or_create_key_file(self.settings.effective_master_key_path)

        try:
            self._fernet = Fernet(key)
        except ValueError as exc:
            raise RuntimeError("OpenZues master key is invalid for Fernet encryption.") from exc
        return self._fernet

    def _read_or_create_key_file(self, path: Path) -> bytes:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            return path.read_text(encoding="utf-8").strip().encode("utf-8")

        key = Fernet.generate_key()
        path.write_text(key.decode("utf-8"), encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass
        return key

    async def list_secret_views(self) -> list[VaultSecretView]:
        usage_counts = await self._usage_counts()
        return [
            self._serialize_secret(row, usage_count=usage_counts.get(int(row["id"]), 0))
            for row in await self.database.list_vault_secrets()
        ]

    async def get_secret_view(self, secret_id: int) -> VaultSecretView | None:
        row = await self.database.get_vault_secret(secret_id)
        if row is None:
            return None
        usage_counts = await self._usage_counts()
        return self._serialize_secret(row, usage_count=usage_counts.get(secret_id, 0))

    async def create_secret(self, payload: VaultSecretCreate) -> VaultSecretView:
        encrypted = self._get_fernet().encrypt(payload.value.encode("utf-8")).decode("utf-8")
        _, preview = mask_secret(payload.value)
        secret_id = await self.database.create_vault_secret(
            label=payload.label,
            kind=payload.kind,
            ciphertext=encrypted,
            preview=preview,
            notes=payload.notes,
        )
        view = await self.get_secret_view(secret_id)
        assert view is not None
        return view

    async def create_secret_value(
        self,
        *,
        label: str,
        value: str,
        kind: str = "token",
        notes: str | None = None,
    ) -> VaultSecretView:
        return await self.create_secret(
            VaultSecretCreate(
                label=label,
                value=value,
                kind=kind,
                notes=notes,
            )
        )

    async def delete_secret(self, secret_id: int) -> None:
        secret = await self.get_secret_view(secret_id)
        if secret is None:
            raise ValueError(f"Unknown vault secret {secret_id}")
        if secret.usage_count:
            raise RuntimeError(
                "Vault secret "
                f"'{secret.label}' is still referenced by {secret.usage_count} record(s)."
            )
        await self.database.delete_vault_secret(secret_id)

    async def get_secret_value(self, secret_id: int) -> str:
        row = await self.database.get_vault_secret(secret_id)
        if row is None:
            raise KeyError(secret_id)
        ciphertext = str(row.get("ciphertext") or "")
        try:
            plaintext = self._get_fernet().decrypt(ciphertext.encode("utf-8"))
        except InvalidToken as exc:
            raise VaultDecryptionError(
                f"Vault secret {secret_id} could not be decrypted with the current master key."
            ) from exc
        return plaintext.decode("utf-8")

    async def probe_secret(self, secret_id: int) -> str | None:
        try:
            await self.get_secret_value(secret_id)
        except KeyError:
            return "Referenced vault secret is missing."
        except VaultDecryptionError:
            return "Vault secret cannot be decrypted with the current master key."
        return None

    async def _usage_counts(self) -> dict[int, int]:
        counts: dict[int, int] = {}
        for row in await self.database.list_integrations():
            raw_secret_id = row.get("vault_secret_id")
            if raw_secret_id is None:
                continue
            secret_id = int(raw_secret_id)
            counts[secret_id] = counts.get(secret_id, 0) + 1
        for row in await self.database.list_notification_routes():
            raw_secret_id = row.get("vault_secret_id")
            if raw_secret_id is None:
                continue
            secret_id = int(raw_secret_id)
            counts[secret_id] = counts.get(secret_id, 0) + 1
        for row in await self.database.list_outbound_deliveries(limit=None):
            route_scope = row.get("route_scope")
            if not isinstance(route_scope, dict):
                continue
            raw_secret_id = route_scope.get("vault_secret_id")
            if raw_secret_id is None:
                continue
            try:
                secret_id = int(raw_secret_id)
            except (TypeError, ValueError):
                continue
            counts[secret_id] = counts.get(secret_id, 0) + 1
        return counts

    def _serialize_secret(
        self,
        row: dict[str, object],
        *,
        usage_count: int,
    ) -> VaultSecretView:
        return VaultSecretView.model_validate(
            {
                **row,
                "secret_preview": row.get("preview"),
                "usage_count": usage_count,
            }
        )
