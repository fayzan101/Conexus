from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.connectors.registry import list_connectors
from app.db.models import ConnectorAccount, Role, User
from app.deps import CurrentUser, DbSession, require_roles
from app.schemas import (
    ConnectorAccountOut,
    ConnectorConnectRequest,
    ConnectorSyncResponse,
    WebhookIngestRequest,
)
from app.services.connectors import connect_account, run_sync, webhook_ingest

router = APIRouter(prefix="/v1/connectors", tags=["connectors"])


@router.get("")
def list_available(_: CurrentUser):
    return {"providers": list_connectors()}


@router.get("/accounts", response_model=list[ConnectorAccountOut])
def list_accounts(db: DbSession, _: CurrentUser):
    return db.query(ConnectorAccount).order_by(ConnectorAccount.created_at.desc()).all()


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


@router.post("/accounts/{account_id}/sync", response_model=ConnectorSyncResponse)
def sync_account(
    account_id: UUID,
    db: DbSession,
    _: Annotated[User, Depends(require_roles(Role.admin))],
    limit: int = 50,
):
    account = db.get(ConnectorAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Connector account not found")
    try:
        result = run_sync(db, account, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ConnectorSyncResponse(**result)


@router.post("/webhooks/{provider}")
def webhook(provider: str, payload: WebhookIngestRequest, db: DbSession):
    try:
        art = webhook_ingest(db, provider, payload.data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not art:
        raise HTTPException(status_code=400, detail="Unsupported webhook payload")
    return {"ok": True, "source_id": art.source_id, "title": art.title}
