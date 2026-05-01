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


def _config_bindings(cfg: Mapping[str, object]) -> list[Mapping[str, object]]:
    bindings = cfg.get("bindings")
    if not isinstance(bindings, list):
        return []
    return [binding for binding in bindings if isinstance(binding, Mapping)]


def _config_agents(cfg: Mapping[str, object]) -> list[Mapping[str, object]]:
    agents = cfg.get("agents")
    if not isinstance(agents, Mapping):
        return []
    agent_list = agents.get("list")
    if not isinstance(agent_list, list):
        return []
    return [agent for agent in agent_list if isinstance(agent, Mapping)]


def _agent_config(cfg: Mapping[str, object], agent_id: str) -> Mapping[str, object]:
    normalized_agent = normalize_agent_id(agent_id)
    for agent in _config_agents(cfg):
        if normalize_agent_id(_normalize_text(agent.get("id"))) == normalized_agent:
            return agent
    return {}


def _agent_acp_runtime_config(agent: Mapping[str, object]) -> Mapping[str, object]:
    runtime = agent.get("runtime")
    if not isinstance(runtime, Mapping):
        return {}
    if _normalize_optional_lowercase_string(runtime.get("type")) != "acp":
        return {}
    acp = runtime.get("acp")
    return acp if isinstance(acp, Mapping) else {}


def _binding_match(binding: Mapping[str, object]) -> Mapping[str, object]:
    match = binding.get("match")
    return match if isinstance(match, Mapping) else {}


def _binding_peer_id(binding: Mapping[str, object]) -> str | None:
    peer = _binding_match(binding).get("peer")
    if isinstance(peer, Mapping):
        return _normalize_text(peer.get("id"))
    return _normalize_text(peer)


def _binding_account_id(binding: Mapping[str, object]) -> str:
    account_id = _normalize_text(_binding_match(binding).get("accountId"))
    if account_id == "*":
        return "*"
    return normalize_account_id(account_id)


def _binding_channel(binding: Mapping[str, object]) -> str | None:
    return _normalize_optional_lowercase_string(_binding_match(binding).get("channel"))


def _binding_acp_config(binding: Mapping[str, object]) -> Mapping[str, object]:
    acp = binding.get("acp")
    return acp if isinstance(acp, Mapping) else {}


def _binding_matches_conversation(
    binding: Mapping[str, object],
    *,
    channel: str,
    account_id: str,
    conversation_id: str,
    parent_conversation_id: str | None,
) -> tuple[int, int] | None:
    if _normalize_optional_lowercase_string(channel) != _binding_channel(binding):
        return None
    binding_account_id = _binding_account_id(binding)
    exact_account = binding_account_id == normalize_account_id(account_id)
    if not exact_account and binding_account_id != "*":
        return None
    binding_conversation_id = _binding_peer_id(binding)
    if binding_conversation_id is None:
        return None
    if binding_conversation_id == conversation_id:
        conversation_rank = 0
    elif parent_conversation_id is not None and binding_conversation_id == parent_conversation_id:
        conversation_rank = 1
    else:
        return None
    account_rank = 0 if exact_account else 1
    return conversation_rank, account_rank


def _configured_acp_spec_from_binding(
    cfg: Mapping[str, object],
    binding: Mapping[str, object],
    *,
    account_id: str,
    parent_conversation_id: str | None,
) -> ConfiguredAcpBindingSpec | None:
    agent_id = _normalize_text(binding.get("agentId"))
    channel = _binding_channel(binding)
    conversation_id = _binding_peer_id(binding)
    if agent_id is None or channel is None or conversation_id is None:
        return None
    agent = _agent_config(cfg, agent_id)
    runtime_defaults = _agent_acp_runtime_config(agent)
    binding_overrides = _binding_acp_config(binding)
    mode = normalize_mode(
        _normalize_text(binding_overrides.get("mode"))
        or _normalize_text(runtime_defaults.get("mode"))
    )
    cwd = (
        _normalize_text(binding_overrides.get("cwd"))
        or _normalize_text(runtime_defaults.get("cwd"))
        or _normalize_text(agent.get("workspace"))
    )
    backend = _normalize_text(binding_overrides.get("backend")) or _normalize_text(
        runtime_defaults.get("backend")
    )
    label = _normalize_text(binding_overrides.get("label"))
    acp_agent_id = _normalize_text(runtime_defaults.get("agent"))
    return ConfiguredAcpBindingSpec(
        channel=channel,
        account_id=normalize_account_id(account_id),
        conversation_id=conversation_id,
        parent_conversation_id=parent_conversation_id,
        agent_id=agent_id,
        acp_agent_id=acp_agent_id,
        mode=mode,
        cwd=cwd,
        backend=backend,
        label=label,
    )


def _resolved_configured_acp_binding_payload(
    spec: ConfiguredAcpBindingSpec,
) -> dict[str, object]:
    return {
        "spec": spec,
        "record": to_configured_acp_binding_record(spec),
    }


def resolve_configured_acp_binding_record(
    cfg: Mapping[str, object],
    *,
    channel: str,
    account_id: str,
    conversation_id: str,
    parent_conversation_id: str | None = None,
) -> dict[str, object] | None:
    normalized_channel = _normalize_optional_lowercase_string(channel)
    normalized_account = normalize_account_id(account_id)
    normalized_conversation = _normalize_text(conversation_id)
    normalized_parent = _normalize_text(parent_conversation_id)
    if normalized_channel is None or normalized_conversation is None:
        return None
    matches: list[tuple[tuple[int, int, int], Mapping[str, object]]] = []
    for index, binding in enumerate(_config_bindings(cfg)):
        if binding.get("type") != "acp":
            continue
        rank = _binding_matches_conversation(
            binding,
            channel=normalized_channel,
            account_id=normalized_account,
            conversation_id=normalized_conversation,
            parent_conversation_id=normalized_parent,
        )
        if rank is None:
            continue
        matches.append(((rank[0], rank[1], index), binding))
    for _rank, binding in sorted(matches, key=lambda item: item[0]):
        spec = _configured_acp_spec_from_binding(
            cfg,
            binding,
            account_id=normalized_account,
            parent_conversation_id=normalized_parent,
        )
        if spec is not None:
            return _resolved_configured_acp_binding_payload(spec)
    return None


def resolve_configured_acp_binding_spec_by_session_key(
    cfg: Mapping[str, object],
    *,
    session_key: str,
) -> ConfiguredAcpBindingSpec | None:
    parsed = parse_configured_acp_session_key(session_key)
    if parsed is None:
        return None
    channel = parsed["channel"]
    account_id = parsed["accountId"]
    matches: list[tuple[int, ConfiguredAcpBindingSpec]] = []
    for index, binding in enumerate(_config_bindings(cfg)):
        if binding.get("type") != "acp":
            continue
        if _binding_channel(binding) != channel:
            continue
        binding_account_id = _binding_account_id(binding)
        if binding_account_id not in {account_id, "*"}:
            continue
        spec = _configured_acp_spec_from_binding(
            cfg,
            binding,
            account_id=account_id,
            parent_conversation_id=None,
        )
        if spec is None:
            continue
        if build_configured_acp_session_key(spec) != session_key.strip():
            continue
        account_rank = 0 if binding_account_id == account_id else 1
        matches.append((account_rank * 1000 + index, spec))
    if not matches:
        return None
    return sorted(matches, key=lambda item: item[0])[0][1]


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
