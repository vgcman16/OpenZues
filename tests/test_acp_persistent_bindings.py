from __future__ import annotations

from openzues.services.acp_persistent_bindings import (
    ConfiguredAcpBindingSpec,
    build_configured_acp_session_key,
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
