from __future__ import annotations

import pytest

from openzues.database import Database
from openzues.schemas import ConversationTargetView
from openzues.services.session_keys import (
    build_agent_main_session_key,
    build_agent_session_key,
    build_agent_peer_session_key,
    build_group_history_key,
    build_launch_session_key,
    canonicalize_session_key,
    classify_session_key_shape,
    get_subagent_depth,
    is_acp_session_key,
    is_cron_run_session_key,
    is_cron_session_key,
    is_subagent_session_key,
    is_valid_agent_id,
    normalize_agent_id,
    normalize_account_id,
    normalize_main_key,
    normalize_optional_account_id,
    parse_agent_session_key,
    parse_thread_session_suffix,
    resolve_agent_id_from_session_key,
    resolve_session_key_for_run,
    resolve_thread_parent_session_key,
    resolve_thread_session_keys,
    reset_resolved_session_key_for_run_cache_for_test,
    scoped_heartbeat_wake_options,
    sanitize_agent_id,
    session_key_lookup_aliases,
    to_agent_request_session_key,
    to_agent_store_session_key,
)


def test_build_launch_session_key_preserves_workspace_affinity_shape() -> None:
    session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=5,
        task_id=77,
        project_id=None,
        operator_id=1,
    )

    assert session_key == "launch:mode:workspace_affinity:task:77:operator:1"


def test_build_launch_session_key_keeps_saved_lane_suffix_and_conversation_target() -> None:
    session_key = build_launch_session_key(
        mode="saved_lane",
        preferred_instance_id=9,
        task_id=77,
        project_id=11,
        operator_id=3,
        conversation_target=ConversationTargetView(
            channel="slack",
            account_id="ops",
            peer_kind="channel",
            peer_id="deploy-room",
            summary="slack · account ops · channel deploy-room",
        ),
    )

    assert (
        session_key
        == "launch:mode:saved_lane:task:77:project:11:operator:3:lane:9:channel:slack:"
        "account:ops:peer:channel:deploy-room"
    )


def test_classify_session_key_shape_matches_openclaw_agent_and_legacy_forms() -> None:
    assert classify_session_key_shape(None) == "missing"
    assert classify_session_key_shape("  ") == "missing"
    assert classify_session_key_shape("agent:worker_1:main") == "agent"
    assert classify_session_key_shape("AGENT:Worker_1:thread:abc") == "agent"
    assert classify_session_key_shape("slack:deploy-room") == "legacy_or_alias"
    assert classify_session_key_shape("agent::main") == "malformed_agent"
    assert classify_session_key_shape("agent:bad id:main") == "malformed_agent"


def test_canonicalize_session_key_promotes_main_alias_for_lookup_continuity() -> None:
    assert canonicalize_session_key("  main  ") == "agent:main:main"
    assert session_key_lookup_aliases("main") == ("agent:main:main", "main")
    assert session_key_lookup_aliases("AGENT:Main:Main") == ("agent:main:main", "main")
    assert session_key_lookup_aliases("Slack:Deploy-Room") == ("slack:deploy-room",)


def test_agent_session_helpers_match_openclaw_store_and_request_shapes() -> None:
    parsed = parse_agent_session_key("  AGENT:Worker_1:ThReAd:AbC  ")

    assert parsed is not None
    assert parsed.agent_id == "worker_1"
    assert parsed.rest == "thread:abc"
    assert build_agent_main_session_key(agent_id="Worker 1", main_key=" MAIN ") == (
        "agent:worker-1:main"
    )
    assert to_agent_request_session_key("agent:worker_1:thread:abc") == "thread:abc"
    assert to_agent_request_session_key("slack:deploy-room") == "slack:deploy-room"
    assert to_agent_store_session_key(agent_id="Worker 1", request_key=None) == (
        "agent:worker-1:main"
    )
    assert to_agent_store_session_key(agent_id="Worker 1", request_key="main") == (
        "agent:worker-1:main"
    )
    assert to_agent_store_session_key(
        agent_id="Worker 1",
        request_key="AGENT:Lead_2:THREAD:AbC",
    ) == "agent:lead_2:thread:abc"
    assert to_agent_store_session_key(
        agent_id="Worker 1",
        request_key="Slack:Deploy-Room",
    ) == "agent:worker-1:slack:deploy-room"
    assert to_agent_store_session_key(
        agent_id="Worker 1",
        request_key="AGENT::bad",
    ) == "agent::bad"
    assert resolve_agent_id_from_session_key("agent:Worker_1:main") == "worker_1"
    assert resolve_agent_id_from_session_key("agent::main") == "main"


def test_agent_peer_session_helpers_keep_dm_and_channel_routes_distinct() -> None:
    assert (
        build_agent_session_key(
            agent_id="main",
            channel="discord",
            account_id="default",
            peer_kind="direct",
            peer_id="user123",
            dm_scope="main",
        )
        == "agent:main:main"
    )
    assert (
        build_agent_session_key(
            agent_id="main",
            channel="discord",
            account_id="default",
            peer_kind="direct",
            peer_id="user123",
            dm_scope="per-peer",
        )
        == "agent:main:direct:user123"
    )
    assert (
        build_agent_session_key(
            agent_id="main",
            channel="discord",
            account_id="default",
            peer_kind="channel",
            peer_id="channel456",
        )
        == "agent:main:discord:channel:channel456"
    )
    assert (
        build_agent_peer_session_key(
            agent_id="main",
            channel="discord",
            account_id="ops west",
            peer_kind="direct",
            peer_id="user123",
            dm_scope="per-account-channel-peer",
        )
        == "agent:main:discord:ops-west:direct:user123"
    )
    assert (
        build_group_history_key(
            channel="discord",
            account_id="ops west",
            peer_kind="channel",
            peer_id="channel456",
        )
        == "discord:ops-west:channel:channel456"
    )


def test_classify_session_key_shape_accepts_backward_compatible_direct_agent_keys() -> None:
    for session_key in (
        "agent:main:telegram:dm:123456",
        "agent:main:whatsapp:dm:+15551234567",
        "agent:main:discord:dm:user123",
        "agent:main:telegram:direct:123456",
        "agent:main:whatsapp:direct:+15551234567",
        "agent:main:discord:direct:user123",
    ):
        assert classify_session_key_shape(session_key) == "agent"


def test_openclaw_session_key_helper_surface_matches_cron_subagent_and_acp_shapes() -> None:
    assert is_cron_run_session_key("agent:main:cron:job-1:run:run-1")
    assert not is_cron_run_session_key("agent:main:cron:job-1")
    assert is_cron_session_key("agent:main:cron:job-1")
    assert is_cron_session_key("agent:main:cron:job-1:run:run-1")
    assert not is_cron_session_key("cron:job-1")
    assert is_subagent_session_key("subagent:worker")
    assert is_subagent_session_key("agent:main:subagent:worker")
    assert not is_subagent_session_key("agent:main:main")
    assert get_subagent_depth("agent:main:subagent:parent:subagent:child") == 2
    assert get_subagent_depth("agent:main:main") == 0
    assert is_acp_session_key("acp:control-plane")
    assert is_acp_session_key("agent:main:acp:control-plane")
    assert not is_acp_session_key("agent:main:main")


def test_scoped_heartbeat_wake_options_only_threads_agent_session_keys() -> None:
    assert scoped_heartbeat_wake_options(
        "agent:main:cron:job-1",
        {"reason": "exec-event"},
    ) == {"reason": "exec-event", "session_key": "agent:main:cron:job-1"}
    wake_options = {"reason": "exec-event"}
    assert (
        scoped_heartbeat_wake_options("launch:mode:workspace_affinity", wake_options)
        is wake_options
    )


def test_agent_session_key_keeps_blank_channel_ids_distinct_from_main_session() -> None:
    for channel_id in ("", "   "):
        session_key = build_agent_session_key(
            agent_id="main",
            channel="discord",
            account_id="default",
            peer_kind="channel",
            peer_id=channel_id,
        )

        assert "unknown" in session_key
        assert session_key != "agent:main:main"


def test_agent_id_helpers_normalize_and_validate_values() -> None:
    assert normalize_main_key(" MAIN ") == "main"
    assert normalize_main_key(None) == "main"
    assert normalize_agent_id(None) == "main"
    assert normalize_agent_id("Worker_1") == "worker_1"
    assert normalize_agent_id(" Worker 1 / prod ") == "worker-1-prod"
    assert normalize_account_id(" Ops West ") == "ops-west"
    assert normalize_account_id(None) == "default"
    assert normalize_optional_account_id(" constructor ") is None
    assert sanitize_agent_id(" Worker 1 / prod ") == "worker-1-prod"
    assert is_valid_agent_id("Worker_1")
    assert not is_valid_agent_id("Worker 1 / prod")


def test_parse_thread_session_suffix_preserves_base_key_and_thread_id() -> None:
    parsed = parse_thread_session_suffix(
        "  AGENT:Main:Main:ThReAd:Thread-AbC-123  "
    )

    assert parsed.base_session_key == "AGENT:Main:Main"
    assert parsed.thread_id == "Thread-AbC-123"
    assert parse_thread_session_suffix("launch:mode:saved_lane").base_session_key == (
        "launch:mode:saved_lane"
    )
    assert parse_thread_session_suffix("launch:mode:saved_lane").thread_id is None


def test_parse_thread_session_suffix_does_not_treat_topic_segments_as_thread_suffixes() -> None:
    feishu_topic_session = (
        "agent:main:feishu:group:oc_group_chat:topic:om_topic_root:sender:ou_topic_user"
    )
    telegram_topic_session = "agent:main:telegram:group:-100123:topic:77"

    feishu_parsed = parse_thread_session_suffix(feishu_topic_session)
    telegram_parsed = parse_thread_session_suffix(telegram_topic_session)

    assert feishu_parsed.base_session_key == feishu_topic_session
    assert feishu_parsed.thread_id is None
    assert resolve_thread_parent_session_key(feishu_topic_session) is None
    assert telegram_parsed.base_session_key == telegram_topic_session
    assert telegram_parsed.thread_id is None
    assert resolve_thread_parent_session_key(telegram_topic_session) is None


def test_resolve_thread_parent_session_key_requires_a_real_suffix() -> None:
    assert (
        resolve_thread_parent_session_key("launch:mode:saved_lane:THREAD:Thread-123")
        == "launch:mode:saved_lane"
    )
    assert resolve_thread_parent_session_key("launch:mode:saved_lane") is None
    assert resolve_thread_parent_session_key(":thread:") is None


def test_resolve_thread_session_keys_matches_openclaw_suffix_and_parent_passthrough() -> None:
    resolved = resolve_thread_session_keys(
        base_session_key="launch:mode:workspace_affinity:task:7:operator:1",
        thread_id=" Thread-AbC ",
        parent_session_key="launch:mode:workspace_affinity:task:7:operator:1",
    )

    assert (
        resolved.session_key
        == "launch:mode:workspace_affinity:task:7:operator:1:thread:thread-abc"
    )
    assert (
        resolved.parent_session_key
        == "launch:mode:workspace_affinity:task:7:operator:1"
    )


def test_resolve_thread_session_keys_skips_parent_when_thread_id_is_blank() -> None:
    resolved = resolve_thread_session_keys(
        base_session_key="launch:mode:workspace_affinity:task:7:operator:1",
        thread_id="   ",
        parent_session_key="launch:mode:workspace_affinity:task:7:operator:1",
    )

    assert resolved.session_key == "launch:mode:workspace_affinity:task:7:operator:1"
    assert resolved.parent_session_key is None


def test_resolve_thread_session_keys_can_preserve_base_key_without_suffix() -> None:
    resolved = resolve_thread_session_keys(
        base_session_key="launch:mode:workspace_affinity:task:7:operator:1",
        thread_id="Topic-77",
        parent_session_key="launch:mode:workspace_affinity:task:7:operator:1",
        use_suffix=False,
        normalize_thread_id=lambda value: value.lower(),
    )

    assert resolved.session_key == "launch:mode:workspace_affinity:task:7:operator:1"
    assert (
        resolved.parent_session_key
        == "launch:mode:workspace_affinity:task:7:operator:1"
    )


@pytest.mark.asyncio
async def test_resolve_session_key_for_run_reads_swarm_mission_state_from_store(tmp_path) -> None:
    reset_resolved_session_key_for_run_cache_for_test()
    database = Database(tmp_path / "session-keys.db")
    await database.initialize()

    await database.create_mission(
        name="Swarm mission",
        objective="Resolve run id back to session key.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread-123",
        session_key="agent:main:thread:thread-123",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=4,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        swarm={"run_id": "run-123"},
        toolsets=["debugging"],
    )

    assert await resolve_session_key_for_run("run-123", database=database) == "thread:thread-123"


@pytest.mark.asyncio
async def test_resolve_session_key_for_run_uses_positive_cache_after_store_hit(tmp_path) -> None:
    reset_resolved_session_key_for_run_cache_for_test()
    database = Database(tmp_path / "session-keys.db")
    await database.initialize()

    mission_id = await database.create_mission(
        name="Cached swarm mission",
        objective="Keep run lookup stable after the store changes.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread-456",
        session_key="agent:main:thread:thread-456",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=4,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        swarm={"run_id": "run-456"},
        toolsets=["debugging"],
    )

    assert await resolve_session_key_for_run("run-456", database=database) == "thread:thread-456"
    await database.delete_mission(mission_id)

    assert await resolve_session_key_for_run("run-456", database=database) == "thread:thread-456"


@pytest.mark.asyncio
async def test_resolve_session_key_for_run_caches_misses_for_short_ttl(tmp_path) -> None:
    reset_resolved_session_key_for_run_cache_for_test()
    database = Database(tmp_path / "session-keys.db")
    await database.initialize()

    now_ms = 1_000.0

    def fake_now_ms() -> float:
        return now_ms

    assert (
        await resolve_session_key_for_run(
            "run-miss",
            database=database,
            now_ms=fake_now_ms,
        )
        is None
    )

    await database.create_mission(
        name="Late swarm mission",
        objective="Become visible after the miss cache expires.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread-789",
        session_key="agent:main:thread:thread-789",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=4,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        swarm={"run_id": "run-miss"},
        toolsets=["debugging"],
    )

    assert (
        await resolve_session_key_for_run(
            "run-miss",
            database=database,
            now_ms=fake_now_ms,
        )
        is None
    )

    now_ms += 1_001.0

    assert (
        await resolve_session_key_for_run(
            "run-miss",
            database=database,
            now_ms=fake_now_ms,
        )
        == "thread:thread-789"
    )
