from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from openzues.database import Database, utcnow
from openzues.schemas import (
    DashboardAccessPostureView,
    OperatorCreate,
    OperatorCredentialView,
    OperatorView,
    RemoteRequestView,
    TeamCreate,
    TeamView,
)
from openzues.services.gateway_method_policy import (
    ADMIN_GATEWAY_METHOD_SCOPE,
    APPROVALS_GATEWAY_METHOD_SCOPE,
    PAIRING_GATEWAY_METHOD_SCOPE,
    READ_GATEWAY_METHOD_SCOPE,
    TALK_SECRETS_GATEWAY_METHOD_SCOPE,
    WRITE_GATEWAY_METHOD_SCOPE,
)

ROLE_RANK = {"viewer": 0, "operator": 1, "admin": 2, "owner": 3}
PERMISSION_MIN_ROLE = {
    "dashboard.read": "viewer",
    "remote.task.trigger": "operator",
    "remote.mission.create": "operator",
    "team.manage": "admin",
    "operator.manage": "admin",
    "api_key.issue": "admin",
}
_OPERATOR_GATEWAY_METHOD_SCOPES = (
    READ_GATEWAY_METHOD_SCOPE,
    WRITE_GATEWAY_METHOD_SCOPE,
    APPROVALS_GATEWAY_METHOD_SCOPE,
    PAIRING_GATEWAY_METHOD_SCOPE,
)
_ADMIN_GATEWAY_METHOD_SCOPES = (
    ADMIN_GATEWAY_METHOD_SCOPE,
    *_OPERATOR_GATEWAY_METHOD_SCOPES,
    TALK_SECRETS_GATEWAY_METHOD_SCOPE,
)


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "team"


def _api_key_preview(api_key: str) -> str:
    if len(api_key) <= 12:
        return api_key
    return f"{api_key[:8]}...{api_key[-4:]}"


def _hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def _role_allows(role: str, permission: str) -> bool:
    required_role = PERMISSION_MIN_ROLE.get(permission)
    if required_role is None:
        return False
    return ROLE_RANK.get(role, -1) >= ROLE_RANK[required_role]


def resolve_gateway_method_scopes_for_role(role: str) -> tuple[str, ...]:
    normalized_role = str(role).strip().lower()
    if normalized_role in {"owner", "admin"}:
        return _ADMIN_GATEWAY_METHOD_SCOPES
    if normalized_role == "operator":
        return _OPERATOR_GATEWAY_METHOD_SCOPES
    if normalized_role == "viewer":
        return (READ_GATEWAY_METHOD_SCOPE,)
    return ()


def build_access_posture(
    teams: list[TeamView],
    operators: list[OperatorView],
    remote_requests: list[RemoteRequestView],
) -> DashboardAccessPostureView:
    api_key_count = sum(operator.has_api_key for operator in operators if operator.enabled)
    recent_cutoff = datetime.now(UTC) - timedelta(hours=24)
    recent_requests = [
        request for request in remote_requests if request.requested_at >= recent_cutoff
    ]
    failed_recent = [request for request in recent_requests if request.status == "failed"]

    if not api_key_count:
        headline = "Remote ingress is local-only"
        summary = (
            "No operator API keys are active yet. The browser workflow stays available, "
            "but external control is still closed."
        )
    elif failed_recent:
        headline = "Remote ingress needs attention"
        summary = (
            f"{len(failed_recent)} authenticated remote request(s) failed in the last 24 hours."
        )
    elif recent_requests:
        headline = "Remote ingress is active"
        summary = (
            f"{len(recent_requests)} authenticated remote request(s) landed in the last 24 hours."
        )
    else:
        headline = "Remote ingress is ready"
        summary = (
            "Operator API keys are issued and the gateway is ready for authenticated "
            "external task or mission control."
        )

    return DashboardAccessPostureView(
        headline=headline,
        summary=summary,
        team_count=len(teams),
        operator_count=len(operators),
        api_key_count=api_key_count,
        recent_remote_request_count=len(recent_requests),
    )


@dataclass(slots=True)
class AuthenticatedOperator:
    operator: OperatorView
    team: TeamView


class AccessService:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def initialize(self) -> None:
        await self._bootstrap_defaults()

    async def list_team_views(self) -> list[TeamView]:
        teams = await self.database.list_teams()
        operators = await self.database.list_operators()
        member_counts: dict[int, int] = {}
        for operator in operators:
            team_id = int(operator["team_id"])
            member_counts[team_id] = member_counts.get(team_id, 0) + 1
        return [
            TeamView.model_validate(
                {
                    **team,
                    "member_count": member_counts.get(int(team["id"]), 0),
                }
            )
            for team in teams
        ]

    async def create_team(self, payload: TeamCreate) -> TeamView:
        slug = _slugify(payload.slug or payload.name)
        if any(str(team["slug"]) == slug for team in await self.database.list_teams()):
            raise ValueError(f"Team slug '{slug}' is already in use.")
        team_id = await self.database.create_team(
            name=payload.name,
            slug=slug,
            description=payload.description,
        )
        team = await self.database.get_team(team_id)
        assert team is not None
        return TeamView.model_validate({**team, "member_count": 0})

    async def list_operator_views(self) -> list[OperatorView]:
        teams = {team.id: team for team in await self.list_team_views()}
        rows = await self.database.list_operators()
        operators = [
            self._serialize_operator(row, team=teams.get(int(row["team_id"]))) for row in rows
        ]
        return sorted(
            operators,
            key=lambda operator: (-ROLE_RANK[operator.role], operator.name.lower(), operator.id),
        )

    async def create_operator(self, payload: OperatorCreate) -> OperatorCredentialView:
        teams = await self.list_team_views()
        if not teams:
            await self._bootstrap_defaults()
            teams = await self.list_team_views()

        team_id = payload.team_id
        if team_id is None:
            if len(teams) != 1:
                raise ValueError("Select a team before creating an operator.")
            team_id = teams[0].id
        if not any(team.id == team_id for team in teams):
            raise ValueError(f"Unknown team {team_id}")

        api_key: str | None = None
        api_key_hash: str | None = None
        api_key_preview: str | None = None
        api_key_issued_at: str | None = None
        if payload.issue_api_key:
            api_key, api_key_hash, api_key_preview = self._issue_api_key_material()
            api_key_issued_at = utcnow()

        operator_id = await self.database.create_operator(
            team_id=team_id,
            name=payload.name,
            email=payload.email,
            role=payload.role,
            enabled=payload.enabled,
            api_key_hash=api_key_hash,
            api_key_preview=api_key_preview,
            api_key_issued_at=api_key_issued_at,
        )
        operator_row = await self.database.get_operator(operator_id)
        assert operator_row is not None
        team = next(team for team in teams if team.id == team_id)
        return OperatorCredentialView(
            operator=self._serialize_operator(operator_row, team=team),
            api_key=api_key,
        )

    async def issue_api_key(self, operator_id: int) -> OperatorCredentialView:
        operator = await self.database.get_operator(operator_id)
        if operator is None:
            raise ValueError(f"Unknown operator {operator_id}")
        team = await self.database.get_team(int(operator["team_id"]))
        if team is None:
            raise ValueError(f"Operator {operator_id} is attached to a missing team.")
        api_key, api_key_hash, api_key_preview = self._issue_api_key_material()
        issued_at = utcnow()
        await self.database.update_operator(
            operator_id,
            api_key_hash=api_key_hash,
            api_key_preview=api_key_preview,
            api_key_issued_at=issued_at,
            api_key_last_used_at=None,
        )
        updated = await self.database.get_operator(operator_id)
        assert updated is not None
        return OperatorCredentialView(
            operator=self._serialize_operator(
                updated,
                team=TeamView.model_validate({**team, "member_count": 0}),
            ),
            api_key=api_key,
        )

    async def revoke_api_key(self, operator_id: int) -> OperatorView:
        operator = await self.database.get_operator(operator_id)
        if operator is None:
            raise ValueError(f"Unknown operator {operator_id}")
        team = await self.database.get_team(int(operator["team_id"]))
        if team is None:
            raise ValueError(f"Operator {operator_id} is attached to a missing team.")
        await self.database.update_operator(
            operator_id,
            api_key_hash=None,
            api_key_preview=None,
            api_key_issued_at=None,
            api_key_last_used_at=None,
        )
        updated = await self.database.get_operator(operator_id)
        assert updated is not None
        return self._serialize_operator(
            updated,
            team=TeamView.model_validate({**team, "member_count": 0}),
        )

    async def authenticate_api_key(
        self,
        api_key: str,
        *,
        permission: str,
    ) -> AuthenticatedOperator:
        operator = await self.database.get_operator_by_api_key_hash(_hash_api_key(api_key))
        if operator is None:
            raise ValueError("Unknown API key.")
        if not bool(operator["enabled"]):
            raise ValueError("Operator is disabled.")
        team_row = await self.database.get_team(int(operator["team_id"]))
        if team_row is None:
            raise ValueError("Operator team is missing.")

        await self.database.update_operator(
            int(operator["id"]),
            api_key_last_used_at=utcnow(),
        )
        refreshed = await self.database.get_operator(int(operator["id"]))
        assert refreshed is not None
        team = TeamView.model_validate({**team_row, "member_count": 0})
        operator_view = self._serialize_operator(refreshed, team=team)
        if not _role_allows(operator_view.role, permission):
            raise PermissionError(f"{operator_view.role} cannot perform {permission}.")
        return AuthenticatedOperator(operator=operator_view, team=team)

    def extract_api_key(self, headers: dict[str, str]) -> str | None:
        authorization = headers.get("authorization") or headers.get("Authorization")
        if authorization:
            prefix = "bearer "
            if authorization.lower().startswith(prefix):
                candidate = authorization[len(prefix) :].strip()
                if candidate:
                    return candidate
        return (
            headers.get("x-openzues-key")
            or headers.get("X-OpenZues-Key")
            or headers.get("x-api-key")
            or headers.get("X-API-Key")
        )

    async def _bootstrap_defaults(self) -> None:
        teams = await self.database.list_teams()
        if not teams:
            await self.database.create_team(
                name="Local Control",
                slug="local-control",
                description="Default local-first operator team.",
            )
            teams = await self.database.list_teams()

        operators = await self.database.list_operators()
        if operators:
            return

        default_team = teams[0]
        await self.database.create_operator(
            team_id=int(default_team["id"]),
            name="Local Owner",
            email=None,
            role="owner",
            enabled=True,
            api_key_hash=None,
            api_key_preview=None,
            api_key_issued_at=None,
        )

    def _serialize_operator(
        self,
        row: dict[str, Any],
        *,
        team: TeamView | None,
    ) -> OperatorView:
        return OperatorView.model_validate(
            {
                **row,
                "team_name": team.name if team is not None else None,
                "has_api_key": bool(row.get("api_key_hash")),
            }
        )

    def _issue_api_key_material(self) -> tuple[str, str, str]:
        api_key = f"ozk_{secrets.token_urlsafe(24)}"
        return api_key, _hash_api_key(api_key), _api_key_preview(api_key)
