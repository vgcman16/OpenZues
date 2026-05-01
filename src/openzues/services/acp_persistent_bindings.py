from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from openzues.services.session_keys import (
    normalize_account_id,
    normalize_agent_id,
    resolve_agent_id_from_session_key,
)

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


def _normalize_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_optional_lowercase_string(value: object) -> str | None:
    normalized = _normalize_text(value)
    return normalized.lower() if normalized is not None else None


def normalize_mode(value: object) -> AcpRuntimeSessionMode:
    return "oneshot" if _normalize_optional_lowercase_string(value) == "oneshot" else "persistent"


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


def parse_configured_acp_session_key(session_key: str) -> dict[str, str] | None:
    trimmed = session_key.strip()
    if not trimmed.startswith("agent:"):
        return None
    rest = trimmed[trimmed.index(":") + 1 :]
    next_separator = rest.find(":")
    if next_separator == -1:
        return None
    tokens = rest[next_separator + 1 :].split(":")
    if len(tokens) != 5 or tokens[0] != "acp" or tokens[1] != "binding":
        return None
    channel = _normalize_optional_lowercase_string(tokens[2])
    if channel is None:
        return None
    return {
        "channel": channel,
        "accountId": normalize_account_id(tokens[3] if len(tokens) > 3 else None),
    }


def resolve_configured_acp_binding_spec_from_record(
    record: Mapping[str, object],
) -> ConfiguredAcpBindingSpec | None:
    if record.get("targetKind") != "session":
        return None
    conversation = record.get("conversation")
    if not isinstance(conversation, Mapping):
        return None
    conversation_id = _normalize_text(conversation.get("conversationId"))
    if conversation_id is None:
        return None
    metadata = record.get("metadata")
    metadata_mapping: Mapping[str, object] = metadata if isinstance(metadata, Mapping) else {}
    agent_id = _normalize_text(
        metadata_mapping.get("agentId")
    ) or resolve_agent_id_from_session_key(
        _normalize_text(record.get("targetSessionKey")),
    )
    if not agent_id:
        return None
    return ConfiguredAcpBindingSpec(
        channel=_normalize_text(conversation.get("channel")) or "",
        account_id=normalize_account_id(_normalize_text(conversation.get("accountId"))),
        conversation_id=conversation_id,
        parent_conversation_id=_normalize_text(conversation.get("parentConversationId")),
        agent_id=agent_id,
        acp_agent_id=_normalize_text(metadata_mapping.get("acpAgentId")),
        mode=normalize_mode(metadata_mapping.get("mode")),
        cwd=_normalize_text(metadata_mapping.get("cwd")),
        backend=_normalize_text(metadata_mapping.get("backend")),
        label=_normalize_text(metadata_mapping.get("label")),
    )
