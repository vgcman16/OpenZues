from __future__ import annotations

from openzues.services.codex_rpc import extract_thread_id, split_args


def test_split_args_handles_basic_invocation() -> None:
    assert split_args("app-server --config local") == ["app-server", "--config", "local"]


def test_extract_thread_id_from_nested_turn_payload() -> None:
    payload = {"turn": {"thread": {"id": "thread_123"}}}
    assert extract_thread_id(payload) == "thread_123"
