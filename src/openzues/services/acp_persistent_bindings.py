from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

from openzues.services.session_keys import normalize_agent_id

AcpRuntimeSessionMode = Literal["persistent", "oneshot"]


@dataclass(frozen=True, slots=True)
class ConfiguredAcpBindingSpec:
    channel: str
    account_id: str
    conversation_id: str
    agent_id: str
    mode: AcpRuntimeSessionMode
    parent_conversation_id: str | None = None
    acp_agent_id: str | None = None
    cwd: str | None = None
    backend: str | None = None
    label: str | None = None


def _binding_hash(
    *,
    channel: str,
    account_id: str,
    conversation_id: str,
) -> str:
    digest = hashlib.sha256(f"{channel}:{account_id}:{conversation_id}".encode()).hexdigest()
    return digest[:16]


def build_configured_acp_session_key(spec: ConfiguredAcpBindingSpec) -> str:
    binding_hash = _binding_hash(
        channel=spec.channel,
        account_id=spec.account_id,
        conversation_id=spec.conversation_id,
    )
    return (
        f"agent:{normalize_agent_id(spec.agent_id)}:acp:binding:"
        f"{spec.channel}:{spec.account_id}:{binding_hash}"
    )


def to_configured_acp_binding_record(
    spec: ConfiguredAcpBindingSpec,
) -> dict[str, object]:
    conversation: dict[str, object] = {
        "channel": spec.channel,
        "accountId": spec.account_id,
        "conversationId": spec.conversation_id,
    }
    if spec.parent_conversation_id is not None:
        conversation["parentConversationId"] = spec.parent_conversation_id

    metadata: dict[str, object] = {
        "source": "config",
        "mode": spec.mode,
        "agentId": spec.agent_id,
    }
    if spec.acp_agent_id is not None:
        metadata["acpAgentId"] = spec.acp_agent_id
    if spec.label is not None:
        metadata["label"] = spec.label
    if spec.backend is not None:
        metadata["backend"] = spec.backend
    if spec.cwd is not None:
        metadata["cwd"] = spec.cwd

    return {
        "bindingId": (
            f"config:acp:{spec.channel}:{spec.account_id}:{spec.conversation_id}"
        ),
        "targetSessionKey": build_configured_acp_session_key(spec),
        "targetKind": "session",
        "conversation": conversation,
        "status": "active",
        "boundAt": 0,
        "metadata": metadata,
    }
