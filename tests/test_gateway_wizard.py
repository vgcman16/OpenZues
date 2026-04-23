from __future__ import annotations

import pytest

from openzues.services.gateway_wizard import GatewayWizardService


@pytest.mark.asyncio
async def test_wizard_prompts_for_mode_when_session_has_no_saved_mode() -> None:
    state: dict[str, object] = {
        "project_path": None,
        "task_name": None,
    }

    async def load_session() -> dict[str, object]:
        return dict(state)

    async def save_session(patch: dict[str, object]) -> dict[str, object]:
        state.update(patch)
        return dict(state)

    service = GatewayWizardService(
        load_session=load_session,
        save_session=save_session,
    )

    start = await service.start()

    assert start["done"] is False
    assert start["status"] == "running"
    assert start["step"] == {
        "id": start["step"]["id"],
        "field": "mode",
        "type": "select",
        "title": "Setup Mode",
        "message": "Choose how you want the gateway wizard to stage setup.",
        "options": [
            {
                "value": "local",
                "label": "Local",
                "hint": "Use a local control plane and desktop lane.",
            },
            {
                "value": "remote",
                "label": "Remote",
                "hint": "Stage the workspace spine first and bind a lane later.",
            },
        ],
        "initialValue": "local",
        "executor": "client",
    }


@pytest.mark.asyncio
async def test_next_without_answer_replays_pending_step() -> None:
    state: dict[str, object] = {
        "project_path": None,
        "task_name": None,
    }

    async def load_session() -> dict[str, object]:
        return dict(state)

    async def save_session(patch: dict[str, object]) -> dict[str, object]:
        state.update(patch)
        return dict(state)

    service = GatewayWizardService(
        load_session=load_session,
        save_session=save_session,
    )

    start = await service.start()

    current = await service.next(session_id=start["sessionId"])

    assert current == {
        "done": False,
        "status": "running",
        "step": {
            "id": start["step"]["id"],
            "field": "mode",
            "type": "select",
            "title": "Setup Mode",
            "message": "Choose how you want the gateway wizard to stage setup.",
            "options": [
                {
                    "value": "local",
                    "label": "Local",
                    "hint": "Use a local control plane and desktop lane.",
                },
                {
                    "value": "remote",
                    "label": "Remote",
                    "hint": "Stage the workspace spine first and bind a lane later.",
                },
            ],
            "initialValue": "local",
            "executor": "client",
        },
    }


@pytest.mark.asyncio
async def test_local_wizard_collects_operator_name_before_task_name() -> None:
    state: dict[str, object] = {
        "mode": "local",
        "flow": "quickstart",
        "project_path": "C:/workspace/OpenZues",
        "operator_name": None,
        "task_name": None,
    }

    async def load_session() -> dict[str, object]:
        return dict(state)

    async def save_session(patch: dict[str, object]) -> dict[str, object]:
        state.update(patch)
        return dict(state)

    service = GatewayWizardService(
        load_session=load_session,
        save_session=save_session,
    )

    start = await service.start()
    session_id = start["sessionId"]

    assert start["done"] is False
    assert start["status"] == "running"
    assert start["step"] == {
        "id": start["step"]["id"],
        "field": "operator_name",
        "type": "text",
        "title": "Operator Name",
        "message": "Name the operator who should receive the local bootstrap access.",
        "placeholder": "Operator",
        "executor": "client",
    }

    next_step = await service.next(
        session_id=session_id,
        answer={
            "stepId": start["step"]["id"],
            "value": "Skull",
        },
    )

    assert next_step == {
        "done": False,
        "status": "running",
        "step": {
            "id": next_step["step"]["id"],
            "field": "task_name",
            "type": "text",
            "title": "Task Name",
            "message": "Name the recurring setup task.",
            "executor": "client",
        },
    }

    done = await service.next(
        session_id=session_id,
        answer={
            "stepId": next_step["step"]["id"],
            "value": "Parity Loop",
        },
    )

    assert done == {"done": True, "status": "done"}
    assert state == {
        "mode": "local",
        "flow": "quickstart",
        "project_path": "C:/workspace/OpenZues",
        "operator_name": "Skull",
        "task_name": "Parity Loop",
    }


@pytest.mark.asyncio
async def test_wizard_persists_start_patch_before_completion() -> None:
    state: dict[str, object] = {}
    saved_patches: list[dict[str, object]] = []

    async def load_session() -> dict[str, object]:
        return dict(state)

    async def save_session(patch: dict[str, object]) -> dict[str, object]:
        saved_patches.append(dict(patch))
        state.update(patch)
        return dict(state)

    service = GatewayWizardService(
        load_session=load_session,
        save_session=save_session,
    )

    start = await service.start(mode="remote", workspace="C:/workspace/OpenZues")

    assert start["done"] is False
    assert start["status"] == "running"
    assert start["step"]["field"] == "operator_name"
    assert state == {
        "mode": "remote",
        "flow": "advanced",
        "instance_mode": "existing",
        "instance_id": None,
        "instance_name": "Local Codex Desktop",
        "project_path": "C:/workspace/OpenZues",
    }
    assert saved_patches == [state]


@pytest.mark.asyncio
async def test_start_honors_prefilled_local_advanced_flow() -> None:
    state: dict[str, object] = {
        "project_path": None,
        "task_name": None,
    }
    saved_patches: list[dict[str, object]] = []

    async def load_session() -> dict[str, object]:
        return dict(state)

    async def save_session(patch: dict[str, object]) -> dict[str, object]:
        saved_patches.append(dict(patch))
        state.update(patch)
        return dict(state)

    service = GatewayWizardService(
        load_session=load_session,
        save_session=save_session,
    )

    start = await service.start(mode="local", flow="advanced")

    assert start == {
        "sessionId": start["sessionId"],
        "done": False,
        "status": "running",
        "step": {
            "id": start["step"]["id"],
            "field": "project_path",
            "type": "text",
            "title": "Workspace",
            "message": "Enter the workspace path to stage for setup.",
            "placeholder": "C:/workspace",
            "executor": "client",
        },
    }
    assert state == {
        "project_path": None,
        "task_name": None,
        "mode": "local",
        "flow": "advanced",
    }
    assert saved_patches == [{"mode": "local", "flow": "advanced"}]


@pytest.mark.asyncio
async def test_wizard_persists_answered_fields_before_completion() -> None:
    state: dict[str, object] = {
        "mode": "local",
        "flow": "quickstart",
        "project_path": "C:/workspace/OpenZues",
        "operator_name": None,
        "task_name": None,
    }
    saved_patches: list[dict[str, object]] = []

    async def load_session() -> dict[str, object]:
        return dict(state)

    async def save_session(patch: dict[str, object]) -> dict[str, object]:
        saved_patches.append(dict(patch))
        state.update(patch)
        return dict(state)

    service = GatewayWizardService(
        load_session=load_session,
        save_session=save_session,
    )

    start = await service.start()
    session_id = start["sessionId"]

    next_step = await service.next(
        session_id=session_id,
        answer={
            "stepId": start["step"]["id"],
            "value": "Skull",
        },
    )

    assert next_step["done"] is False
    assert next_step["status"] == "running"
    assert next_step["step"]["field"] == "task_name"
    assert state["operator_name"] == "Skull"
    assert state["task_name"] is None
    assert saved_patches[-1] == {
        "operator_name": "Skull",
    }


@pytest.mark.asyncio
async def test_local_wizard_prompts_for_flow_before_workspace_when_missing() -> None:
    state: dict[str, object] = {
        "mode": "local",
        "flow": None,
        "project_path": None,
        "task_name": None,
    }

    async def load_session() -> dict[str, object]:
        return dict(state)

    async def save_session(patch: dict[str, object]) -> dict[str, object]:
        state.update(patch)
        return dict(state)

    service = GatewayWizardService(
        load_session=load_session,
        save_session=save_session,
    )

    start = await service.start()
    session_id = start["sessionId"]

    assert start["done"] is False
    assert start["status"] == "running"
    assert start["step"] == {
        "id": start["step"]["id"],
        "field": "flow",
        "type": "select",
        "title": "Setup Flow",
        "message": "Choose how deeply to stage the local bootstrap posture.",
        "options": [
            {
                "value": "quickstart",
                "label": "QuickStart",
                "hint": "Reuse the current control plane and tune the rest later.",
            },
            {
                "value": "advanced",
                "label": "Advanced",
                "hint": "Stage the full local control plane posture before bootstrap.",
            },
        ],
        "initialValue": "quickstart",
        "executor": "client",
    }

    next_step = await service.next(
        session_id=session_id,
        answer={
            "stepId": start["step"]["id"],
            "value": "advanced",
        },
    )

    assert next_step == {
        "done": False,
        "status": "running",
        "step": {
            "id": next_step["step"]["id"],
            "field": "project_path",
            "type": "text",
            "title": "Workspace",
            "message": "Enter the workspace path to stage for setup.",
            "placeholder": "C:/workspace",
            "executor": "client",
        },
    }


@pytest.mark.asyncio
async def test_remote_wizard_collects_optional_identity_fields_before_task_name() -> None:
    state: dict[str, object] = {
        "mode": "remote",
        "flow": "advanced",
        "project_path": "C:/workspace/OpenZues",
        "operator_name": None,
        "operator_email": None,
        "team_name": None,
        "task_name": None,
    }

    async def load_session() -> dict[str, object]:
        return dict(state)

    async def save_session(patch: dict[str, object]) -> dict[str, object]:
        state.update(patch)
        return dict(state)

    service = GatewayWizardService(
        load_session=load_session,
        save_session=save_session,
    )

    start = await service.start(mode="remote", workspace="C:/workspace/OpenZues")
    session_id = start["sessionId"]

    assert start["done"] is False
    assert start["status"] == "running"
    assert start["step"] == {
        "id": start["step"]["id"],
        "field": "operator_name",
        "type": "text",
        "title": "Operator Name",
        "message": "Name the operator who should receive the remote ingress API key.",
        "placeholder": "Remote Builder",
        "executor": "client",
    }

    next_step = await service.next(
        session_id=session_id,
        answer={
            "stepId": start["step"]["id"],
            "value": "Remote Builder",
        },
    )

    assert next_step == {
        "done": False,
        "status": "running",
        "step": {
            "id": next_step["step"]["id"],
            "field": "operator_email",
            "type": "text",
            "title": "Operator Email",
            "message": "Optionally add an email for the remote API key handoff.",
            "placeholder": "builder@example.com",
            "required": False,
            "inputType": "email",
            "executor": "client",
        },
    }

    team_step = await service.next(
        session_id=session_id,
        answer={
            "stepId": next_step["step"]["id"],
            "value": "remote.builder@example.com",
        },
    )

    assert team_step == {
        "done": False,
        "status": "running",
        "step": {
            "id": team_step["step"]["id"],
            "field": "team_name",
            "type": "text",
            "title": "Operator Team",
            "message": "Optionally group the remote operator under a team label.",
            "placeholder": "Platform Ops",
            "required": False,
            "executor": "client",
        },
    }

    task_step = await service.next(
        session_id=session_id,
        answer={
            "stepId": team_step["step"]["id"],
            "value": "Platform Ops",
        },
    )

    assert task_step == {
        "done": False,
        "status": "running",
        "step": {
            "id": task_step["step"]["id"],
            "field": "task_name",
            "type": "text",
            "title": "Task Name",
            "message": "Name the recurring setup task.",
            "executor": "client",
        },
    }

    done = await service.next(
        session_id=session_id,
        answer={
            "stepId": task_step["step"]["id"],
            "value": "Remote Parity Loop",
        },
    )

    assert done == {"done": True, "status": "done"}
    assert state == {
        "mode": "remote",
        "flow": "advanced",
        "project_path": "C:/workspace/OpenZues",
        "operator_name": "Remote Builder",
        "operator_email": "remote.builder@example.com",
        "team_name": "Platform Ops",
        "task_name": "Remote Parity Loop",
        "instance_mode": "existing",
    }


@pytest.mark.asyncio
async def test_remote_wizard_prompts_for_optional_saved_lane_before_task_name() -> None:
    state: dict[str, object] = {
        "mode": "remote",
        "flow": "advanced",
        "project_path": "C:/workspace/OpenZues",
        "operator_name": "Remote Builder",
        "operator_email": "remote.builder@example.com",
        "team_name": "Platform Ops",
        "task_name": None,
    }

    async def load_session() -> dict[str, object]:
        return dict(state)

    async def save_session(patch: dict[str, object]) -> dict[str, object]:
        state.update(patch)
        return dict(state)

    async def list_instances() -> list[dict[str, object]]:
        return [
            {"id": 7, "name": "Pinned Lane", "connected": True},
            {"id": 9, "name": "Fallback Lane", "connected": False},
        ]

    service = GatewayWizardService(
        load_session=load_session,
        save_session=save_session,
        list_instances=list_instances,
    )

    start = await service.start(mode="remote", workspace="C:/workspace/OpenZues")
    session_id = start["sessionId"]

    assert start == {
        "sessionId": session_id,
        "done": False,
        "status": "running",
        "step": {
            "id": start["step"]["id"],
            "field": "instance_id",
            "type": "select",
            "title": "Saved Lane",
            "message": (
                "Optionally pin the first remote launch to a saved lane now, "
                "or leave it flexible."
            ),
            "options": [
                {
                    "value": "",
                    "label": "Bind at launch time",
                    "instanceName": "Local Codex Desktop",
                },
                {
                    "value": "9",
                    "label": "Fallback Lane (offline)",
                    "instanceName": "Fallback Lane",
                },
                {
                    "value": "7",
                    "label": "Pinned Lane (connected)",
                    "instanceName": "Pinned Lane",
                },
            ],
            "required": False,
            "executor": "client",
        },
    }

    task_step = await service.next(
        session_id=session_id,
        answer={
            "stepId": start["step"]["id"],
            "value": "7",
        },
    )

    assert task_step == {
        "done": False,
        "status": "running",
        "step": {
            "id": task_step["step"]["id"],
            "field": "task_name",
            "type": "text",
            "title": "Task Name",
            "message": "Name the recurring setup task.",
            "executor": "client",
        },
    }
    assert state["instance_mode"] == "existing"
    assert state["instance_id"] == 7
    assert state["instance_name"] == "Pinned Lane"


@pytest.mark.asyncio
async def test_remote_wizard_surfaces_note_when_no_saved_lane_exists() -> None:
    state: dict[str, object] = {
        "mode": "remote",
        "flow": "advanced",
        "project_path": "C:/workspace/OpenZues",
        "instance_mode": "existing",
        "instance_id": None,
        "instance_name": "Local Codex Desktop",
        "operator_name": "Remote Builder",
        "operator_email": "remote.builder@example.com",
        "team_name": "Platform Ops",
        "task_name": None,
    }

    async def load_session() -> dict[str, object]:
        return dict(state)

    async def save_session(patch: dict[str, object]) -> dict[str, object]:
        state.update(patch)
        return dict(state)

    async def list_instances() -> list[dict[str, object]]:
        return []

    service = GatewayWizardService(
        load_session=load_session,
        save_session=save_session,
        list_instances=list_instances,
    )

    start = await service.start(mode="remote", workspace="C:/workspace/OpenZues")
    session_id = start["sessionId"]

    assert start == {
        "sessionId": session_id,
        "done": False,
        "status": "running",
        "step": {
            "id": start["step"]["id"],
            "field": "remote_lane_note",
            "type": "note",
            "title": "Lane Binding Can Wait",
            "message": (
                "No saved lane is staged yet. Remote setup can still save the workspace, "
                "operator access, and recurring task now, then bind a lane when the first "
                "launch is ready."
            ),
            "executor": "client",
        },
    }

    task_step = await service.next(
        session_id=session_id,
        answer={
            "stepId": start["step"]["id"],
        },
    )

    assert task_step == {
        "done": False,
        "status": "running",
        "step": {
            "id": task_step["step"]["id"],
            "field": "task_name",
            "type": "text",
            "title": "Task Name",
            "message": "Name the recurring setup task.",
            "executor": "client",
        },
    }
    assert state["instance_mode"] == "existing"
    assert state["instance_id"] is None
    assert state["instance_name"] == "Local Codex Desktop"


@pytest.mark.asyncio
async def test_remote_wizard_skipping_optional_saved_lane_clears_stale_selection() -> None:
    state: dict[str, object] = {
        "mode": "remote",
        "flow": "advanced",
        "project_path": "C:/workspace/OpenZues",
        "instance_mode": "existing",
        "instance_id": 7,
        "instance_name": "Pinned Lane",
        "operator_name": "Remote Builder",
        "operator_email": "remote.builder@example.com",
        "team_name": "Platform Ops",
        "task_name": None,
    }

    async def load_session() -> dict[str, object]:
        return dict(state)

    async def save_session(patch: dict[str, object]) -> dict[str, object]:
        state.update(patch)
        return dict(state)

    async def list_instances() -> list[dict[str, object]]:
        return [{"id": 7, "name": "Pinned Lane", "connected": True}]

    service = GatewayWizardService(
        load_session=load_session,
        save_session=save_session,
        list_instances=list_instances,
    )

    start = await service.start(mode="remote", workspace="C:/workspace/OpenZues")
    session_id = start["sessionId"]

    assert start["step"]["field"] == "instance_id"
    assert start["step"]["initialValue"] == "7"

    task_step = await service.next(
        session_id=session_id,
        answer={
            "stepId": start["step"]["id"],
            "value": "",
        },
    )

    assert task_step["done"] is False
    assert task_step["step"]["field"] == "task_name"
    assert state["instance_mode"] == "existing"
    assert state["instance_id"] is None
    assert state["instance_name"] == "Local Codex Desktop"
