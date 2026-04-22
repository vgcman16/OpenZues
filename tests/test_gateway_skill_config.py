from __future__ import annotations

import json
from pathlib import Path

from openzues.services.gateway_skill_config import GatewaySkillConfigService


def test_is_config_path_truthy_handles_lists_and_empty_containers(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    config_path = workspace_root / ".codex" / "gateway-skill-config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "features": {
                    "enabled": True,
                    "providers": [{"enabled": True}, {"enabled": False}],
                    "emptyList": [],
                    "emptyObject": {},
                    "blank": "  ",
                }
            }
        ),
        encoding="utf-8",
    )

    service = GatewaySkillConfigService(workspace_root=workspace_root)

    assert service.is_config_path_truthy("features.enabled") is True
    assert service.is_config_path_truthy("features.providers[0].enabled") is True
    assert service.is_config_path_truthy("features.providers[1].enabled") is False
    assert service.is_config_path_truthy("features.emptyList") is False
    assert service.is_config_path_truthy("features.emptyObject") is False
    assert service.is_config_path_truthy("features.blank") is False
    assert service.is_config_path_truthy("features.providers[9].enabled") is False
