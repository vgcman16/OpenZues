from __future__ import annotations

from typing import Any

from openzues.schemas import ControlUiBootstrapConfigView


class GatewayConfigService:
    def __init__(
        self,
        *,
        assistant_name: str,
        assistant_avatar: str,
        assistant_agent_id: str,
        server_version: str | None,
        base_path: str = "",
        local_media_preview_roots: list[str] | None = None,
        embed_sandbox: str = "scripts",
        allow_external_embed_urls: bool = False,
    ) -> None:
        self._assistant_name = assistant_name
        self._assistant_avatar = assistant_avatar
        self._assistant_agent_id = assistant_agent_id
        self._server_version = server_version
        self._base_path = base_path
        self._local_media_preview_roots = list(local_media_preview_roots or [])
        self._embed_sandbox = embed_sandbox
        self._allow_external_embed_urls = allow_external_embed_urls

    def build_snapshot(self) -> dict[str, Any]:
        return ControlUiBootstrapConfigView.model_validate(
            {
                "basePath": self._base_path,
                "assistantName": self._assistant_name,
                "assistantAvatar": self._assistant_avatar,
                "assistantAgentId": self._assistant_agent_id,
                "serverVersion": self._server_version,
                "localMediaPreviewRoots": self._local_media_preview_roots,
                "embedSandbox": self._embed_sandbox,
                "allowExternalEmbedUrls": self._allow_external_embed_urls,
            }
        ).model_dump(mode="json", by_alias=True)
