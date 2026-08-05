import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.connectors.github import github_oauth_authorize_url, github_oauth_exchange
from app.connectors.registry import list_connectors
from app.connectors.security import verify_github_signature, verify_slack_signature
from app.connectors.slack import slack_oauth_authorize_url, slack_oauth_exchange
from app.db.models import ConnectorAccount, Role, User
from app.deps import AppSettings, CurrentUser, DbSession, require_roles
from app.schemas import (
    ConnectorAccountOut,
    ConnectorConnectRequest,
    ConnectorHealthOut,
    ConnectorSyncResponse,
    WebhookIngestRequest,
)
from app.services.connectors import check_account_health, connect_account, run_sync, webhook_ingest

router = APIRouter(prefix="/v1/connectors", tags=["connectors"])


@router.get("")
def list_available(_: CurrentUser):
    return {"providers": list_connectors()}


@router.get("/accounts", response_model=list[ConnectorAccountOut])
def list_accounts(db: DbSession, _: CurrentUser):
    return db.query(ConnectorAccount).order_by(ConnectorAccount.created_at.desc()).all()


@router.get("/health", response_model=list[ConnectorHealthOut])
def connectors_health(db: DbSession, _: CurrentUser):
    accounts = db.query(ConnectorAccount).order_by(ConnectorAccount.created_at.desc()).all()
    return [ConnectorHealthOut(**check_account_health(db, a)) for a in accounts]


@router.post("/{provider}/connect", response_model=ConnectorAccountOut, status_code=status.HTTP_201_CREATED)
def connect(
    provider: str,
    payload: ConnectorConnectRequest,
    db: DbSession,
    user: Annotated[User, Depends(require_roles(Role.admin))],
):
    try:
        return connect_account(
            db,
            provider=provider,
            credentials=payload.credentials,
            display_name=payload.display_name,
            external_account_id=payload.external_account_id or "default",
            user_id=user.id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{provider}/oauth/start")
def oauth_start(
    provider: str,
    settings: AppSettings,
    _: Annotated[User, Depends(require_roles(Role.admin))],
):
    state = secrets.token_urlsafe(16)
    if provider == "slack":
        if not settings.slack_client_id:
            raise HTTPException(status_code=400, detail="SLACK_CLIENT_ID not configured")
        url = slack_oauth_authorize_url(settings, state=state)
    elif provider == "github":
        if not settings.github_client_id:
            raise HTTPException(status_code=400, detail="GITHUB_CLIENT_ID not configured")
        url = github_oauth_authorize_url(settings, state=state)
    else:
        raise HTTPException(status_code=400, detail=f"OAuth not implemented for {provider}")
    return {"authorize_url": url, "state": state}


@router.get("/{provider}/oauth/callback")
def oauth_callback(
    provider: str,
    db: DbSession,
    settings: AppSettings,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not code:
        raise HTTPException(status_code=400, detail="Missing OAuth code")
    try:
        if provider == "slack":
            data = slack_oauth_exchange(settings, code=code)
            credentials = {
                "access_token": data.get("access_token"),
                "team_id": (data.get("team") or {}).get("id"),
                "bot_user_id": data.get("bot_user_id"),
            }
            external_id = credentials.get("team_id") or "default"
            display = (data.get("team") or {}).get("name") or "Slack"
        elif provider == "github":
            data = github_oauth_exchange(settings, code=code)
            credentials = {"access_token": data.get("access_token"), "token_type": data.get("token_type")}
            external_id = "default"
            display = "GitHub"
        else:
            raise HTTPException(status_code=400, detail=f"OAuth not implemented for {provider}")
        connect_account(
            db,
            provider=provider,
            credentials=credentials,
            display_name=display,
            external_account_id=str(external_id),
            user_id=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(f"{settings.app_base_url}/connectors?connected={provider}")


@router.post("/accounts/{account_id}/sync", response_model=ConnectorSyncResponse)
def sync_account(
    account_id: UUID,
    db: DbSession,
    settings: AppSettings,
    _: Annotated[User, Depends(require_roles(Role.admin))],
    limit: int = 50,
):
    account = db.get(ConnectorAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Connector account not found")
    try:
        result = run_sync(db, account, settings, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ConnectorSyncResponse(**result)


@router.post("/accounts/{account_id}/health", response_model=ConnectorHealthOut)
def account_health(
    account_id: UUID,
    db: DbSession,
    _: Annotated[User, Depends(require_roles(Role.admin))],
):
    account = db.get(ConnectorAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Connector account not found")
    return ConnectorHealthOut(**check_account_health(db, account))


@router.post("/webhooks/{provider}")
async def webhook(
    provider: str,
    request: Request,
    db: DbSession,
    settings: AppSettings,
    x_slack_signature: Annotated[str | None, Header()] = None,
    x_slack_request_timestamp: Annotated[str | None, Header()] = None,
    x_hub_signature_256: Annotated[str | None, Header()] = None,
):
    body = await request.body()
    if provider == "slack":
        if settings.slack_signing_secret:
            ok = verify_slack_signature(
                signing_secret=settings.slack_signing_secret,
                timestamp=x_slack_request_timestamp or "",
                body=body,
                signature=x_slack_signature or "",
            )
            if not ok:
                raise HTTPException(status_code=401, detail="Invalid Slack signature")
    elif provider == "github":
        if settings.github_webhook_secret:
            ok = verify_github_signature(
                secret=settings.github_webhook_secret,
                body=body,
                signature_header=x_hub_signature_256 or "",
            )
            if not ok:
                raise HTTPException(status_code=401, detail="Invalid GitHub signature")

    import json

    try:
        payload_json = json.loads(body.decode("utf-8") or "{}")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from None

    # Slack URL verification challenge
    if provider == "slack" and payload_json.get("type") == "url_verification":
        return {"challenge": payload_json.get("challenge")}

    data = payload_json.get("data") if isinstance(payload_json.get("data"), dict) else payload_json
    if provider == "slack" and "event" in payload_json:
        data = payload_json["event"]
    if provider == "github" and "issue" in payload_json:
        data = payload_json["issue"]
        if payload_json.get("pull_request"):
            data = {**data, "pull_request": payload_json["pull_request"], "type": "pull_request"}

    try:
        art = webhook_ingest(db, provider, data, settings)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not art:
        raise HTTPException(status_code=400, detail="Unsupported webhook payload")
    return {"ok": True, "source_id": art.source_id, "title": art.title}


@router.post("/webhooks/{provider}/json")
def webhook_json(provider: str, payload: WebhookIngestRequest, db: DbSession, settings: AppSettings):
    """Unauthenticated JSON path retained for local fixture tests only."""
    if settings.environment.lower() not in {"local", "test", "development"}:
        raise HTTPException(status_code=403, detail="JSON webhook helper disabled outside local")
    try:
        art = webhook_ingest(db, provider, payload.data, settings)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not art:
        raise HTTPException(status_code=400, detail="Unsupported webhook payload")
    return {"ok": True, "source_id": art.source_id, "title": art.title}
