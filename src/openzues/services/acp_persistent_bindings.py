from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

from openzues.services.session_keys import (
    normalize_account_id,
    normalize_agent_id,
    resolve_agent_id_from_session_key,
)

AcpRuntimeSessionMode = Literal["persistent", "oneshot"]
AcpResetReason = Literal["new", "reset"]


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


class ConfiguredAcpSessionManager(Protocol):
    async def resolve_session(self, **kwargs: object) -> Mapping[str, object]:
        ...

    async def close_session(self, **kwargs: object) -> Mapping[str, object]:
        ...

    async def initialize_session(self, **kwargs: object) -> Mapping[str, object]:
        ...


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


def _metadata_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


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
    metadata_mapping = _metadata_mapping(record.get("metadata"))
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


def _runtime_options_mapping(meta: Mapping[str, object]) -> Mapping[str, object]:
    return _metadata_mapping(meta.get("runtimeOptions"))


def _session_matches_configured_binding(
    *,
    spec: ConfiguredAcpBindingSpec,
    meta: Mapping[str, object],
    default_backend: str | None,
) -> bool:
    if meta.get("state") == "error":
        return False
    desired_agent = _normalize_optional_lowercase_string(spec.acp_agent_id or spec.agent_id)
    current_agent = _normalize_optional_lowercase_string(meta.get("agent"))
    if current_agent is None or current_agent != desired_agent:
        return False
    if meta.get("mode") != spec.mode:
        return False
    desired_backend = _normalize_text(spec.backend) or _normalize_text(default_backend) or ""
    if desired_backend:
        current_backend = _normalize_text(meta.get("backend"))
        if current_backend is None or current_backend != desired_backend:
            return False
    desired_cwd = _normalize_text(spec.cwd)
    if desired_cwd is not None:
        runtime_options = _runtime_options_mapping(meta)
        current_cwd = _normalize_text(runtime_options.get("cwd")) or _normalize_text(
            meta.get("cwd")
        )
        if current_cwd != desired_cwd:
            return False
    return True


async def ensure_configured_acp_binding_session(
    spec: ConfiguredAcpBindingSpec,
    *,
    manager: ConfiguredAcpSessionManager,
    default_backend: str | None = None,
) -> dict[str, object]:
    session_key = build_configured_acp_session_key(spec)
    try:
        resolution = await manager.resolve_session(session_key=session_key)
        resolution_kind = _normalize_text(resolution.get("kind"))
        meta = _metadata_mapping(resolution.get("meta"))
        if (
            resolution_kind == "ready"
            and _session_matches_configured_binding(
                spec=spec,
                meta=meta,
                default_backend=default_backend,
            )
        ):
            return {"ok": True, "sessionKey": session_key}
        if resolution_kind != "none":
            await manager.close_session(
                session_key=session_key,
                reason="config-binding-reconfigure",
                clear_meta=False,
                allow_backend_unavailable=True,
                require_acp_session=False,
            )
        await manager.initialize_session(
            session_key=session_key,
            agent=spec.acp_agent_id or spec.agent_id,
            mode=spec.mode,
            cwd=spec.cwd,
            backend_id=spec.backend,
        )
        return {"ok": True, "sessionKey": session_key}
    except Exception as exc:
        return {"ok": False, "sessionKey": session_key, "error": str(exc)}


async def reset_acp_session_in_place(
    *,
    session_key: str,
    reason: AcpResetReason,
    manager: ConfiguredAcpSessionManager,
    acp_meta: Mapping[str, object] | None = None,
    configured_binding_spec: ConfiguredAcpBindingSpec | None = None,
    clear_meta: bool | None = None,
) -> dict[str, object]:
    normalized_session_key = session_key.strip()
    if not normalized_session_key:
        return {"ok": False, "skipped": True}

    should_clear_meta = (
        clear_meta if clear_meta is not None else configured_binding_spec is not None
    )
    if acp_meta is None:
        if should_clear_meta:
            return {"ok": True}
        return {"ok": False, "skipped": True}

    try:
        await manager.close_session(
            session_key=normalized_session_key,
            reason=f"{reason}-in-place-reset",
            discard_persistent_state=True,
            clear_meta=should_clear_meta,
            allow_backend_unavailable=True,
            require_acp_session=False,
        )
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
