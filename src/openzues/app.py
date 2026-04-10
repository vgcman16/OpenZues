from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from openzues.database import Database
from openzues.logging_utils import configure_logging
from openzues.schemas import (
    CommandCreate,
    DashboardView,
    DiagnosticsView,
    EventView,
    InstanceCreate,
    MissionCreate,
    PlaybookCreate,
    PlaybookRun,
    PlaybookRunResult,
    PlaybookView,
    ProjectCreate,
    ProjectView,
    RequestResolution,
    ReviewCreate,
    ThreadCreate,
    TurnCreate,
)
from openzues.services.codex_desktop import CodexDesktopService
from openzues.services.environment import EnvironmentService
from openzues.services.github import GitHubService
from openzues.services.hub import BroadcastHub
from openzues.services.manager import RuntimeManager
from openzues.services.missions import MissionService
from openzues.services.playbooks import PlaybookService
from openzues.services.projects import ProjectService
from openzues.settings import Settings, settings

configure_logging()


def create_app(
    app_settings: Settings | None = None,
    *,
    database: Database | None = None,
    hub: BroadcastHub | None = None,
    manager: RuntimeManager | None = None,
    project_service: ProjectService | None = None,
    playbook_service: PlaybookService | None = None,
    environment_service: EnvironmentService | None = None,
    desktop_service: CodexDesktopService | None = None,
    mission_service: MissionService | None = None,
) -> FastAPI:
    active_settings = app_settings or settings
    active_database = database or Database(active_settings.effective_db_path)
    active_hub = hub or BroadcastHub()
    active_desktop_service = desktop_service or CodexDesktopService()
    active_manager = manager or RuntimeManager(
        active_database,
        active_hub,
        desktop_service=active_desktop_service,
    )
    active_project_service = project_service or ProjectService(GitHubService())
    active_playbook_service = playbook_service or PlaybookService()
    active_environment_service = environment_service or EnvironmentService(
        desktop_service=active_desktop_service
    )
    active_mission_service = mission_service or MissionService(
        active_database,
        active_manager,
        active_hub,
    )
    active_manager.add_event_listener(active_mission_service.handle_event)
    active_manager.add_server_request_listener(active_mission_service.handle_server_request)
    templates = Jinja2Templates(directory=str(active_settings.templates_dir))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        active_settings.data_dir.mkdir(parents=True, exist_ok=True)
        await active_database.initialize()
        await active_manager.load()
        await active_mission_service.start()
        yield
        await active_mission_service.close()
        for runtime in active_manager.instances.values():
            if runtime.client is not None:
                await runtime.client.close()

    fastapi_app = FastAPI(title="OpenZues", lifespan=lifespan)
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    fastapi_app.mount(
        "/static",
        StaticFiles(directory=str(active_settings.static_dir)),
        name="static",
    )

    async def build_dashboard() -> DashboardView:
        project_rows = await active_database.list_projects()
        playbook_rows = await active_database.list_playbooks()
        projects = [
            ProjectView.model_validate(active_project_service.inspect(row))
            for row in project_rows
        ]
        playbooks = [PlaybookView.model_validate(row) for row in playbook_rows]
        events = [EventView.model_validate(row) for row in await active_database.list_events(250)]
        missions = await active_mission_service.list_views()
        return DashboardView(
            instances=await active_manager.list_views(),
            missions=missions,
            projects=projects,
            playbooks=playbooks,
            events=events,
        )

    @fastapi_app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"settings": active_settings},
        )

    @fastapi_app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @fastapi_app.get("/api/dashboard")
    async def dashboard() -> DashboardView:
        return await build_dashboard()

    @fastapi_app.get("/api/diagnostics")
    async def diagnostics() -> DiagnosticsView:
        return active_environment_service.collect()

    @fastapi_app.post("/api/instances")
    async def create_instance(payload: InstanceCreate) -> dict:
        command = None if payload.transport == "desktop" else (
            payload.command or active_settings.default_codex_command
        )
        args = None if payload.transport == "desktop" else (
            payload.args or active_settings.default_codex_args
        )
        websocket_url = payload.websocket_url if payload.transport == "websocket" else None
        runtime = await active_manager.create_instance(
            name=payload.name,
            transport=payload.transport,
            command=command,
            args=args,
            websocket_url=websocket_url,
            cwd=payload.cwd,
            auto_connect=payload.auto_connect,
        )
        return runtime.view().model_dump()

    @fastapi_app.post("/api/instances/quick-connect/desktop")
    async def quick_connect_desktop() -> dict:
        runtime = await active_manager.quick_connect_desktop(cwd=str(Path.cwd()))
        return runtime.view().model_dump()

    @fastapi_app.post("/api/instances/{instance_id}/connect")
    async def connect_instance(instance_id: int) -> dict:
        runtime = await active_manager.connect_instance(instance_id)
        return runtime.view().model_dump()

    @fastapi_app.post("/api/instances/{instance_id}/disconnect")
    async def disconnect_instance(instance_id: int) -> dict:
        await active_manager.disconnect_instance(instance_id)
        runtime = await active_manager.get(instance_id)
        return runtime.view().model_dump()

    @fastapi_app.post("/api/instances/{instance_id}/refresh")
    async def refresh_instance(instance_id: int) -> dict:
        runtime = await active_manager.refresh_instance(instance_id)
        return runtime.view().model_dump()

    @fastapi_app.post("/api/instances/{instance_id}/threads")
    async def start_thread(instance_id: int, payload: ThreadCreate) -> dict:
        return await active_manager.start_thread(
            instance_id,
            model=payload.model,
            cwd=payload.cwd,
            reasoning_effort=payload.reasoning_effort,
            collaboration_mode=payload.collaboration_mode,
        )

    @fastapi_app.post("/api/instances/{instance_id}/turns")
    async def start_turn(instance_id: int, payload: TurnCreate) -> dict:
        return await active_manager.start_turn(
            instance_id,
            thread_id=payload.thread_id,
            text=payload.text,
            cwd=payload.cwd,
            model=payload.model,
            reasoning_effort=payload.reasoning_effort,
            collaboration_mode=payload.collaboration_mode,
        )

    @fastapi_app.post("/api/instances/{instance_id}/turns/{thread_id}/interrupt")
    async def interrupt_turn(instance_id: int, thread_id: str) -> dict:
        return await active_manager.interrupt_turn(instance_id, thread_id)

    @fastapi_app.post("/api/instances/{instance_id}/reviews")
    async def start_review(instance_id: int, payload: ReviewCreate) -> dict:
        return await active_manager.start_review(instance_id, payload.thread_id)

    @fastapi_app.post("/api/instances/{instance_id}/commands")
    async def exec_command(instance_id: int, payload: CommandCreate) -> dict:
        return await active_manager.exec_command(
            instance_id,
            command=payload.command,
            cwd=payload.cwd,
            timeout_ms=payload.timeout_ms,
            tty=payload.tty,
        )

    @fastapi_app.post("/api/instances/{instance_id}/requests/{request_id}/resolve")
    async def resolve_request(
        instance_id: int,
        request_id: str,
        payload: RequestResolution,
    ) -> dict[str, bool]:
        await active_manager.resolve_request(instance_id, request_id, payload.result)
        return {"ok": True}

    @fastapi_app.post("/api/projects")
    async def create_project(payload: ProjectCreate) -> ProjectView:
        path = str(Path(payload.path).expanduser())
        label = payload.label or Path(path).name
        await active_database.create_project(path=path, label=label)
        rows = await active_database.list_projects()
        row = next((item for item in rows if Path(item["path"]).expanduser() == Path(path)), None)
        if row is None:
            raise HTTPException(status_code=500, detail="Failed to create project.")
        return ProjectView.model_validate(active_project_service.inspect(row))

    @fastapi_app.post("/api/missions")
    async def create_mission(payload: MissionCreate) -> dict:
        try:
            return (await active_mission_service.create(payload)).model_dump()
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @fastapi_app.post("/api/missions/{mission_id}/start")
    async def start_mission(mission_id: int) -> dict:
        try:
            return (await active_mission_service.resume(mission_id)).model_dump()
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @fastapi_app.post("/api/missions/{mission_id}/pause")
    async def pause_mission(mission_id: int) -> dict:
        try:
            return (await active_mission_service.pause(mission_id)).model_dump()
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @fastapi_app.post("/api/missions/{mission_id}/run-now")
    async def run_mission_now(mission_id: int) -> dict:
        try:
            return (await active_mission_service.run_now(mission_id)).model_dump()
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @fastapi_app.post("/api/missions/{mission_id}/complete")
    async def complete_mission(mission_id: int) -> dict:
        try:
            return (await active_mission_service.complete(mission_id)).model_dump()
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @fastapi_app.delete("/api/missions/{mission_id}")
    async def delete_mission(mission_id: int) -> dict[str, bool]:
        await active_mission_service.delete(mission_id)
        return {"ok": True}

    @fastapi_app.get("/api/playbooks")
    async def list_playbooks() -> list[PlaybookView]:
        rows = await active_database.list_playbooks()
        return [PlaybookView.model_validate(row) for row in rows]

    @fastapi_app.post("/api/playbooks")
    async def create_playbook(payload: PlaybookCreate) -> PlaybookView:
        playbook_id = await active_database.create_playbook(
            name=payload.name,
            description=payload.description,
            kind=payload.kind,
            instance_id=payload.instance_id,
            payload=payload.model_dump(exclude={"name", "description", "kind", "instance_id"}),
        )
        row = await active_database.get_playbook(playbook_id)
        if row is None:
            raise HTTPException(status_code=500, detail="Failed to create playbook.")
        return PlaybookView.model_validate(row)

    @fastapi_app.delete("/api/playbooks/{playbook_id}")
    async def delete_playbook(playbook_id: int) -> dict[str, bool]:
        await active_database.delete_playbook(playbook_id)
        return {"ok": True}

    @fastapi_app.post("/api/playbooks/{playbook_id}/run")
    async def run_playbook(playbook_id: int, payload: PlaybookRun) -> PlaybookRunResult:
        playbook = await active_database.get_playbook(playbook_id)
        if playbook is None:
            raise HTTPException(status_code=404, detail="Playbook not found.")
        try:
            return await active_playbook_service.execute(playbook, payload, active_manager)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @fastapi_app.websocket("/ws")
    async def websocket_events(websocket: WebSocket) -> None:
        await websocket.accept()
        async with active_hub.subscribe() as queue:
            try:
                while True:
                    event = await queue.get()
                    await websocket.send_text(json.dumps(event))
            except WebSocketDisconnect:
                return

    return fastapi_app


app = create_app()
