from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import ConnectorAccount, Document, DocumentChunk, LegalHold, RetentionPolicy, TenantCryptoKey
from app.services.audit import write_audit


def wrap_dek(plaintext_dek: bytes, master_secret: str) -> str:
    digest = hmac.new(master_secret.encode("utf-8"), plaintext_dek, hashlib.sha256).hexdigest()
    return f"{plaintext_dek.hex()}:{digest}"


def unwrap_dek(wrapped: str, master_secret: str) -> bytes:
    hex_part, digest = wrapped.split(":", 1)
    raw = bytes.fromhex(hex_part)
    expected = hmac.new(master_secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, digest):
        raise ValueError("DEK integrity check failed")
    return raw


def ensure_tenant_key(db: Session, settings: Settings, tenant_id: str) -> TenantCryptoKey:
    existing = db.query(TenantCryptoKey).filter(TenantCryptoKey.tenant_id == tenant_id).first()
    if existing:
        return existing
    dek = secrets.token_bytes(32)
    if settings.kms_backend == "vault" and settings.vault_addr and settings.vault_token:
        # Vault-shaped placeholder: store HMAC-wrapped DEK labeled vault
        wrapped = "vault:" + wrap_dek(dek, settings.vault_token or settings.secret_key)
    else:
        wrapped = wrap_dek(dek, settings.secret_key)
    row = TenantCryptoKey(tenant_id=tenant_id, wrapped_dek=wrapped, algorithm="aes-256-gcm")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def rotate_tenant_key(db: Session, settings: Settings, tenant_id: str) -> TenantCryptoKey:
    row = ensure_tenant_key(db, settings, tenant_id)
    dek = secrets.token_bytes(32)
    row.wrapped_dek = wrap_dek(dek, settings.secret_key)
    row.rotated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def encrypt_credentials(settings: Settings, tenant_id: str, credentials: dict, wrapped_dek: str) -> str:
    dek = unwrap_dek(wrapped_dek.replace("vault:", ""), settings.secret_key if "vault:" not in wrapped_dek else (settings.vault_token or settings.secret_key))
    payload = json.dumps(credentials).encode("utf-8")
    # Simple XOR stream for local/dev envelope (not a substitute for AES-GCM in prod KMS)
    keystream = hashlib.sha256(dek + tenant_id.encode()).digest()
    out = bytes(b ^ keystream[i % len(keystream)] for i, b in enumerate(payload))
    return base64.urlsafe_b64encode(out).decode("ascii")


def decrypt_credentials(settings: Settings, tenant_id: str, blob: str, wrapped_dek: str) -> dict:
    dek = unwrap_dek(wrapped_dek.replace("vault:", ""), settings.secret_key if "vault:" not in wrapped_dek else (settings.vault_token or settings.secret_key))
    raw = base64.urlsafe_b64decode(blob.encode("ascii"))
    keystream = hashlib.sha256(dek + tenant_id.encode()).digest()
    payload = bytes(b ^ keystream[i % len(keystream)] for i, b in enumerate(raw))
    return json.loads(payload.decode("utf-8"))


def security_posture(settings: Settings) -> dict:
    return {
        "require_tls": settings.require_tls,
        "encryption_at_rest_verified": settings.encryption_at_rest_verified,
        "kms_backend": settings.kms_backend,
        "llm_mode": settings.llm_mode,
        "llm_no_train": settings.llm_no_train,
        "auth_provider": settings.auth_provider,
    }


def run_retention_job(db: Session, settings: Settings, *, tenant_id: str) -> dict:
    policy = (
        db.query(RetentionPolicy)
        .filter(RetentionPolicy.tenant_id == tenant_id, RetentionPolicy.resource_type == "document")
        .first()
    )
    days = policy.retain_days if policy else settings.retention_days_default
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    active_hold = (
        db.query(LegalHold).filter(LegalHold.tenant_id == tenant_id, LegalHold.active.is_(True)).first()
    )
    if active_hold:
        return {"deleted": 0, "skipped_legal_hold": True, "hold": active_hold.name}

    docs = (
        db.query(Document)
        .filter(
            Document.tenant_id == tenant_id,
            Document.legal_hold.is_(False),
            Document.created_at < cutoff,
        )
        .all()
    )
    deleted = 0
    for doc in docs:
        if doc.retain_until and doc.retain_until.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
            continue
        db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
        db.delete(doc)
        deleted += 1
    db.commit()
    write_audit(
        db,
        tenant_id=tenant_id,
        action="retention.purge",
        resource_type="document",
        detail={"deleted": deleted, "cutoff": cutoff.isoformat()},
    )
    return {"deleted": deleted, "cutoff": cutoff.isoformat()}


def dsr_delete_user_data(
    db: Session,
    settings: Settings,
    *,
    tenant_id: str,
    user_id: UUID,
    vector_store=None,
    graph=None,
    object_storage=None,
) -> dict:
    """Cascade delete user-owned documents across postgres (+ best-effort vector/graph/object)."""
    docs = db.query(Document).filter(Document.tenant_id == tenant_id, Document.uploaded_by == user_id).all()
    removed = {"documents": 0, "chunks": 0, "vectors": 0, "objects": 0, "graph": 0}
    for doc in docs:
        if doc.legal_hold:
            continue
        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
        for chunk in chunks:
            if vector_store and chunk.vector_id:
                try:
                    vector_store.delete(point_id=chunk.vector_id)
                    removed["vectors"] += 1
                except Exception:
                    pass
            db.delete(chunk)
            removed["chunks"] += 1
        if object_storage and doc.object_key:
            try:
                object_storage.delete(doc.object_key)
                removed["objects"] += 1
            except Exception:
                pass
        if graph:
            try:
                graph.delete_node(str(doc.id))
                removed["graph"] += 1
            except Exception:
                pass
        db.delete(doc)
        removed["documents"] += 1
    db.commit()
    write_audit(
        db,
        tenant_id=tenant_id,
        action="dsr.delete",
        resource_type="user",
        resource_id=str(user_id),
        detail=removed,
    )
    return removed


def rotate_connector_tokens(db: Session, settings: Settings, *, tenant_id: str) -> dict:
    key = ensure_tenant_key(db, settings, tenant_id)
    accounts = db.query(ConnectorAccount).filter(ConnectorAccount.tenant_id == tenant_id).all()
    rotated = 0
    for account in accounts:
        creds = account.credentials or {}
        if not creds:
            continue
        # Re-encrypt marker for rotation audit trail
        blob = encrypt_credentials(settings, tenant_id, creds, key.wrapped_dek)
        account.credentials = {"encrypted": blob, "rotated_at": datetime.now(timezone.utc).isoformat()}
        rotated += 1
    db.commit()
    write_audit(
        db,
        tenant_id=tenant_id,
        action="secrets.rotate_connectors",
        resource_type="connector_account",
        detail={"rotated": rotated},
    )
    return {"rotated": rotated}
