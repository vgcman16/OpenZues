from __future__ import annotations

from openzues.services.acp_persistent_bindings import (
    ConfiguredAcpBindingSpec,
    build_configured_acp_session_key,
    ensure_configured_acp_binding_session,
    parse_configured_acp_session_key,
    reset_acp_session_in_place,
    resolve_configured_acp_binding_spec_from_record,
    to_configured_acp_binding_record,
)


class FakeConfiguredAcpSessionManager:
    def __init__(self, resolution: dict[str, object] | None = None) -> None:
        self.resolution = resolution or {"kind": "none"}
        self.resolve_calls: list[dict[str, object]] = []
        self.close_calls: list[dict[str, object]] = []
        self.initialize_calls: list[dict[str, object]] = []

    async def resolve_session(self, **kwargs: object) -> dict[str, object]:
        self.resolve_calls.append(kwargs)
        return self.resolution

    async def close_session(self, **kwargs: object) -> dict[str, object]:
        self.close_calls.append(kwargs)
        return {"ok": True}

    async def initialize_session(self, **kwargs: object) -> dict[str, object]:
        self.initialize_calls.append(kwargs)
        return {"ok": True}


def test_configured_acp_session_key_matches_openclaw_hash() -> None:
    spec = ConfiguredAcpBindingSpec(
        channel="discord",
        account_id="default",
        conversation_id="1478836151241412759",
        agent_id="Claude",
        mode="persistent",
    )

    assert (
        build_configured_acp_session_key(spec)
        == "agent:claude:acp:binding:discord:default:f56b4624dd829241"
    )


def test_configured_acp_binding_record_matches_openclaw_shape() -> None:
    spec = ConfiguredAcpBindingSpec(
        channel="discord",
        account_id="default",
        conversation_id="1478836151241412759",
        parent_conversation_id="guild:987654321",
        agent_id="codex",
        acp_agent_id="claude",
        mode="oneshot",
        cwd="C:/work/openzues",
        backend="acpx",
        label="Ops binding",
    )

    assert to_configured_acp_binding_record(spec) == {
        "bindingId": "config:acp:discord:default:1478836151241412759",
        "targetSessionKey": "agent:codex:acp:binding:discord:default:f56b4624dd829241",
        "targetKind": "session",
        "conversation": {
            "channel": "discord",
            "accountId": "default",
            "conversationId": "1478836151241412759",
            "parentConversationId": "guild:987654321",
        },
        "status": "active",
        "boundAt": 0,
        "metadata": {
            "source": "config",
            "mode": "oneshot",
            "agentId": "codex",
            "acpAgentId": "claude",
            "label": "Ops binding",
            "backend": "acpx",
            "cwd": "C:/work/openzues",
        },
    }


def test_parse_configured_acp_session_key_returns_channel_and_account() -> None:
    assert parse_configured_acp_session_key(
        "agent:Claude:acp:binding:Discord:DEFAULT:f56b4624dd829241"
    ) == {"channel": "discord", "accountId": "default"}
    assert parse_configured_acp_session_key("agent:main:acp:other:discord:default:x") is None


def test_resolve_configured_acp_binding_spec_from_record_matches_openclaw_shape() -> None:
    record = {
        "bindingId": "config:acp:discord:default:1478836151241412759",
        "targetSessionKey": "agent:claude:acp:binding:discord:default:f56b4624dd829241",
        "targetKind": "session",
        "conversation": {
            "channel": "discord",
            "accountId": "",
            "conversationId": " 1478836151241412759 ",
            "parentConversationId": " guild:987654321 ",
        },
        "status": "active",
        "boundAt": 0,
        "metadata": {
            "mode": "oneshot",
            "acpAgentId": " claude-harness ",
            "cwd": " C:/work/openzues ",
            "backend": " acpx ",
            "label": " Ops binding ",
        },
    }

    assert resolve_configured_acp_binding_spec_from_record(record) == ConfiguredAcpBindingSpec(
        channel="discord",
        account_id="default",
        conversation_id="1478836151241412759",
        parent_conversation_id="guild:987654321",
        agent_id="claude",
        acp_agent_id="claude-harness",
        mode="oneshot",
        cwd="C:/work/openzues",
        backend="acpx",
        label="Ops binding",
    )


def test_resolve_configured_acp_binding_spec_rejects_non_session_records() -> None:
    assert resolve_configured_acp_binding_spec_from_record(
        {
            "targetKind": "subagent",
            "targetSessionKey": "agent:codex:acp:binding:discord:default:seed",
            "conversation": {
                "channel": "discord",
                "accountId": "default",
                "conversationId": "1478836151241412759",
            },
            "metadata": {"agentId": "codex"},
        }
    ) is None


async def test_ensure_configured_acp_binding_session_keeps_matching_ready_session() -> None:
    spec = ConfiguredAcpBindingSpec(
        channel="discord",
        account_id="default",
        conversation_id="1478836151241412759",
        agent_id="codex",
        mode="persistent",
    )
    session_key = build_configured_acp_session_key(spec)
    manager = FakeConfiguredAcpSessionManager(
        {
            "kind": "ready",
            "meta": {
                "agent": "codex",
                "mode": "persistent",
                "backend": "acpx",
                "runtimeOptions": {"cwd": "C:/work/openzues"},
            },
        }
    )

    result = await ensure_configured_acp_binding_session(
        spec,
        manager=manager,
    )

    assert result == {"ok": True, "sessionKey": session_key}
    assert manager.close_calls == []
    assert manager.initialize_calls == []


async def test_ensure_configured_acp_binding_session_reinitializes_mismatched_cwd() -> None:
    spec = ConfiguredAcpBindingSpec(
        channel="discord",
        account_id="default",
        conversation_id="1478836151241412759",
        agent_id="codex",
        mode="persistent",
        cwd="C:/work/openzues",
    )
    session_key = build_configured_acp_session_key(spec)
    manager = FakeConfiguredAcpSessionManager(
        {
            "kind": "ready",
            "meta": {
                "agent": "codex",
                "mode": "persistent",
                "runtimeOptions": {"cwd": "C:/work/other"},
            },
        }
    )

    result = await ensure_configured_acp_binding_session(
        spec,
        manager=manager,
    )

    assert result == {"ok": True, "sessionKey": session_key}
    assert manager.close_calls == [
        {
            "session_key": session_key,
            "reason": "config-binding-reconfigure",
            "clear_meta": False,
            "allow_backend_unavailable": True,
            "require_acp_session": False,
        }
    ]
    assert manager.initialize_calls == [
        {
            "session_key": session_key,
            "agent": "codex",
            "mode": "persistent",
            "cwd": "C:/work/openzues",
            "backend_id": None,
        }
    ]


async def test_ensure_configured_acp_binding_session_uses_acp_agent_override() -> None:
    spec = ConfiguredAcpBindingSpec(
        channel="discord",
        account_id="default",
        conversation_id="1478836151241412759",
        agent_id="coding",
        acp_agent_id="codex",
        mode="persistent",
        backend="acpx",
    )
    session_key = build_configured_acp_session_key(spec)
    manager = FakeConfiguredAcpSessionManager()

    result = await ensure_configured_acp_binding_session(
        spec,
        manager=manager,
    )

    assert result == {"ok": True, "sessionKey": session_key}
    assert manager.initialize_calls == [
        {
            "session_key": session_key,
            "agent": "codex",
            "mode": "persistent",
            "cwd": None,
            "backend_id": "acpx",
        }
    ]


async def test_reset_acp_session_in_place_clears_configured_binding_metadata() -> None:
    spec = ConfiguredAcpBindingSpec(
        channel="discord",
        account_id="default",
        conversation_id="1478836151241412759",
        agent_id="claude",
        mode="persistent",
    )
    session_key = build_configured_acp_session_key(spec)
    manager = FakeConfiguredAcpSessionManager()

    result = await reset_acp_session_in_place(
        session_key=session_key,
        reason="reset",
        manager=manager,
        acp_meta={"agent": "claude", "mode": "persistent", "backend": "acpx"},
        configured_binding_spec=spec,
    )

    assert result == {"ok": True}
    assert manager.close_calls == [
        {
            "session_key": session_key,
            "reason": "reset-in-place-reset",
            "discard_persistent_state": True,
            "clear_meta": True,
            "allow_backend_unavailable": True,
            "require_acp_session": False,
        }
    ]
    assert manager.initialize_calls == []


async def test_reset_acp_session_in_place_keeps_metadata_for_non_configured_session() -> None:
    session_key = "agent:claude:acp:binding:demo-binding:default:9373ab192b2317f4"
    manager = FakeConfiguredAcpSessionManager()

    result = await reset_acp_session_in_place(
        session_key=session_key,
        reason="reset",
        manager=manager,
        acp_meta={"agent": "claude", "mode": "persistent", "backend": "acpx"},
    )

    assert result == {"ok": True}
    assert manager.close_calls == [
        {
            "session_key": session_key,
            "reason": "reset-in-place-reset",
            "discard_persistent_state": True,
            "clear_meta": False,
            "allow_backend_unavailable": True,
            "require_acp_session": False,
        }
    ]


async def test_reset_acp_session_in_place_treats_configured_missing_meta_as_reset() -> None:
    spec = ConfiguredAcpBindingSpec(
        channel="discord",
        account_id="default",
        conversation_id="1478836151241412759",
        agent_id="claude",
        mode="persistent",
    )
    manager = FakeConfiguredAcpSessionManager()

    result = await reset_acp_session_in_place(
        session_key=build_configured_acp_session_key(spec),
        reason="new",
        manager=manager,
        configured_binding_spec=spec,
    )

    assert result == {"ok": True}
    assert manager.close_calls == []


async def test_reset_acp_session_in_place_skips_blank_session_key() -> None:
    manager = FakeConfiguredAcpSessionManager()

    result = await reset_acp_session_in_place(
        session_key=" ",
        reason="reset",
        manager=manager,
    )

    assert result == {"ok": False, "skipped": True}
    assert manager.close_calls == []
