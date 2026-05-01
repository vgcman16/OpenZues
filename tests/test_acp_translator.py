from __future__ import annotations

import os
from pathlib import Path


def test_acp_translator_builds_prompt_send_request_with_cwd_prefix(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from openzues.services.acp_translator import build_prompt_send_request

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("HOME", str(home))

    request = build_prompt_send_request(
        session={
            "sessionId": "session-1",
            "sessionKey": "agent:main:main",
            "cwd": str(home / "openclaw-test"),
        },
        prompt_request={
            "sessionId": "session-1",
            "prompt": [{"type": "text", "text": "hello"}],
            "_meta": {},
        },
        run_id="run-1",
        opts={},
    )

    assert request["sessionKey"] == "agent:main:main"
    assert request["idempotencyKey"] == "run-1"
    assert request["message"] in {
        "[Working directory: ~/openclaw-test]\n\nhello",
        "[Working directory: ~\\openclaw-test]\n\nhello",
    }
    assert "attachments" not in request


def test_acp_translator_preserves_backslashes_in_cwd_prefix(monkeypatch, tmp_path: Path) -> None:
    from openzues.services.acp_translator import build_prompt_send_request

    home = str(tmp_path / "home")
    monkeypatch.setenv("USERPROFILE", home)
    monkeypatch.setenv("HOME", home)
    cwd = f"{home}\\openclaw-test"

    request = build_prompt_send_request(
        session={"sessionId": "session-1", "sessionKey": "agent:main:main", "cwd": cwd},
        prompt_request={"sessionId": "session-1", "prompt": [{"type": "text", "text": "hello"}]},
        run_id="run-1",
        opts={"prefixCwd": True},
    )

    assert request["message"] == "[Working directory: ~\\openclaw-test]\n\nhello"


def test_acp_translator_can_disable_cwd_prefix_and_forward_meta_options() -> None:
    from openzues.services.acp_translator import build_prompt_send_request

    request = build_prompt_send_request(
        session={"sessionId": "session-1", "sessionKey": "agent:main:main", "cwd": os.getcwd()},
        prompt_request={
            "sessionId": "session-1",
            "prompt": [
                {"type": "text", "text": "hello"},
                {"type": "image", "data": "abc", "mimeType": "image/png"},
            ],
            "_meta": {
                "prefixCwd": False,
                "thinking": "high",
                "deliver": True,
                "timeoutMs": 1234,
            },
        },
        run_id="run-1",
        opts={"prefixCwd": True},
    )

    assert request == {
        "sessionKey": "agent:main:main",
        "message": "hello",
        "attachments": [{"type": "image", "mimeType": "image/png", "content": "abc"}],
        "idempotencyKey": "run-1",
        "thinking": "high",
        "deliver": True,
        "timeoutMs": 1234,
    }


def test_acp_translator_adds_provenance_metadata_and_receipt(monkeypatch, tmp_path: Path) -> None:
    from openzues.services.acp_translator import build_prompt_send_request

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("HOME", str(home))

    request = build_prompt_send_request(
        session={
            "sessionId": "session-1",
            "sessionKey": "agent:main:main",
            "cwd": str(home / "openclaw-test"),
        },
        prompt_request={"sessionId": "session-1", "prompt": [{"type": "text", "text": "hello"}]},
        run_id="run-1",
        opts={"provenanceMode": "meta+receipt"},
    )

    assert request["systemInputProvenance"] == {
        "kind": "external_user",
        "originSessionId": "session-1",
        "sourceChannel": "acp",
        "sourceTool": "openclaw_acp",
    }
    receipt = request["systemProvenanceReceipt"]
    assert isinstance(receipt, str)
    assert "[Source Receipt]" in receipt
    assert "bridge=openclaw-acp" in receipt
    assert "originCwd=~/openclaw-test" in receipt or "originCwd=~\\openclaw-test" in receipt
    assert "originSessionId=session-1" in receipt
    assert "targetSession=agent:main:main" in receipt
