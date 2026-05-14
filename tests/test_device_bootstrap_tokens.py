from __future__ import annotations

import json

from openzues.services.device_bootstrap_tokens import issue_device_bootstrap_token


def test_issue_device_bootstrap_token_bounds_explicit_profile_to_handoff_scopes(
    tmp_path,
) -> None:
    issued = issue_device_bootstrap_token(
        base_dir=tmp_path,
        profile={
            "roles": ["node", "operator"],
            "scopes": [
                "node.exec",
                "operator.admin",
                "operator.approvals",
                "operator.pairing",
                "operator.read",
                "operator.talk.secrets",
                "operator.write",
            ],
        },
    )

    state = json.loads((tmp_path / "devices" / "bootstrap.json").read_text())
    record = state[issued.token]

    assert record["profile"] == {
        "roles": ["node", "operator"],
        "scopes": [
            "operator.approvals",
            "operator.read",
            "operator.talk.secrets",
            "operator.write",
        ],
    }
