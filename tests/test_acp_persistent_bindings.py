from __future__ import annotations

from openzues.services.acp_persistent_bindings import (
    ConfiguredAcpBindingSpec,
    build_configured_acp_session_key,
    parse_configured_acp_session_key,
    resolve_configured_acp_binding_spec_from_record,
    to_configured_acp_binding_record,
)


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
