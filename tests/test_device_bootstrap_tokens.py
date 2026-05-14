from __future__ import annotations

import json

from openzues.services.device_bootstrap_tokens import (
    clear_device_bootstrap_tokens,
    get_device_bootstrap_token_profile,
    issue_device_bootstrap_token,
    revoke_device_bootstrap_token,
)


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


def test_get_device_bootstrap_token_profile_loads_valid_trimmed_token(
    tmp_path,
) -> None:
    issued = issue_device_bootstrap_token(
        base_dir=tmp_path,
        profile={
            "roles": [" operator ", "operator"],
            "scopes": ["operator.read", " operator.read "],
        },
    )

    profile = get_device_bootstrap_token_profile(
        base_dir=tmp_path,
        token=f" {issued.token} ",
    )
    missing = get_device_bootstrap_token_profile(base_dir=tmp_path, token="missing")

    assert profile == {
        "roles": ["operator"],
        "scopes": ["operator.read"],
    }
    assert missing is None


def test_revoke_device_bootstrap_token_removes_specific_trimmed_token(
    tmp_path,
) -> None:
    issued = issue_device_bootstrap_token(
        base_dir=tmp_path,
        profile={"roles": ["operator"], "scopes": ["operator.read"]},
    )

    revoked = revoke_device_bootstrap_token(base_dir=tmp_path, token=f" {issued.token} ")
    missing = revoke_device_bootstrap_token(base_dir=tmp_path, token=issued.token)
    state = json.loads((tmp_path / "devices" / "bootstrap.json").read_text())

    assert revoked == {
        "removed": True,
        "record": {
            "token": issued.token,
            "ts": revoked["record"]["ts"],
            "issuedAtMs": revoked["record"]["issuedAtMs"],
            "expiresAtMs": revoked["record"]["expiresAtMs"],
            "profile": {"roles": ["operator"], "scopes": ["operator.read"]},
            "redeemedProfile": {"roles": [], "scopes": []},
        },
    }
    assert missing == {"removed": False}
    assert issued.token not in state


def test_clear_device_bootstrap_tokens_removes_outstanding_tokens(tmp_path) -> None:
    first = issue_device_bootstrap_token(base_dir=tmp_path)
    second = issue_device_bootstrap_token(base_dir=tmp_path)

    cleared = clear_device_bootstrap_tokens(base_dir=tmp_path)
    cleared_again = clear_device_bootstrap_tokens(base_dir=tmp_path)
    state = json.loads((tmp_path / "devices" / "bootstrap.json").read_text())

    assert first.token != second.token
    assert cleared == {"removed": 2}
    assert cleared_again == {"removed": 0}
    assert state == {}
