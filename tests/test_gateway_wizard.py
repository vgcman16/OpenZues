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
        "initialvalue": "local",
        "executor": "client",
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
        "initialvalue": "quickstart",
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
    }
