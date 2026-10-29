from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import ConnectorAccount, Document, DocumentChunk, LegalHold, RetentionPolicy, TenantCryptoKey
from app.services.audit import write_audit

logger = logging.getLogger(__name__)

_WRAP_PREFIX_LOCAL = "aesgcm:"
_WRAP_PREFIX_VAULT = "vault-transit:"
_LEGACY_XOR_NOTE = "legacy-xor-blobs-require-reconnect"


def _master_key_bytes(settings: Settings) -> bytes:
    raw = (settings.kms_master_key or settings.secret_key or "").encode("utf-8")
    return hashlib.sha256(raw).digest()


def _vault_master(settings: Settings) -> bytes:
    token = settings.vault_token or settings.kms_master_key or settings.secret_key
    return hashlib.sha256(token.encode("utf-8")).digest()


def wrap_dek(plaintext_dek: bytes, master_secret: str | bytes) -> str:
    """AES-256-GCM wrap DEK. Returns aesgcm:<b64(nonce||ciphertext||tag)>."""
    if isinstance(master_secret, str):
        key = hashlib.sha256(master_secret.encode("utf-8")).digest()
    else:
        key = master_secret if len(master_secret) == 32 else hashlib.sha256(master_secret).digest()
    nonce = secrets.token_bytes(12)
    ct = AESGCM(key).encrypt(nonce, plaintext_dek, b"eb-dek-v1")
    return _WRAP_PREFIX_LOCAL + base64.urlsafe_b64encode(nonce + ct).decode("ascii")


def unwrap_dek(wrapped: str, master_secret: str | bytes) -> bytes:
    if isinstance(master_secret, str):
        key = hashlib.sha256(master_secret.encode("utf-8")).digest()
    else:
        key = master_secret if len(master_secret) == 32 else hashlib.sha256(master_secret).digest()

    if wrapped.startswith(_WRAP_PREFIX_VAULT):
        payload = wrapped[len(_WRAP_PREFIX_VAULT) :]
        # Local stand-in for Vault Transit: same AES-GCM, separate key material namespace
        return unwrap_dek(_WRAP_PREFIX_LOCAL + payload, key)

    if wrapped.startswith(_WRAP_PREFIX_LOCAL):
        raw = base64.urlsafe_b64decode(wrapped[len(_WRAP_PREFIX_LOCAL) :].encode("ascii"))
        nonce, ct = raw[:12], raw[12:]
        return AESGCM(key).decrypt(nonce, ct, b"eb-dek-v1")

    # Legacy HMAC hex wrap (pre-hardening): plaintext DEK + digest — reject in favor of rotation
    if ":" in wrapped and not wrapped.startswith("vault:"):
        hex_part, digest = wrapped.split(":", 1)
        try:
            raw = bytes.fromhex(hex_part)
        except ValueError as exc:
            raise ValueError("Unsupported DEK wrap format") from exc
        import hmac as _hmac

        expected = _hmac.new(
            master_secret.encode("utf-8") if isinstance(master_secret, str) else master_secret,
            raw,
            hashlib.sha256,
        ).hexdigest()
        if not _hmac.compare_digest(expected, digest):
            raise ValueError("DEK integrity check failed")
        return raw

    if wrapped.startswith("vault:"):
        return unwrap_dek(wrapped.replace("vault:", "", 1), master_secret)

    raise ValueError("Unsupported DEK wrap format")


def _resolve_wrap_secret(settings: Settings, wrapped: str) -> bytes:
    if wrapped.startswith(_WRAP_PREFIX_VAULT) or (
        settings.kms_backend == "vault" and settings.vault_token
    ):
        return _vault_master(settings)
    return _master_key_bytes(settings)


def ensure_tenant_key(db: Session, settings: Settings, tenant_id: str) -> TenantCryptoKey:
    existing = db.query(TenantCryptoKey).filter(TenantCryptoKey.tenant_id == tenant_id).first()
    if existing:
        return existing
    dek = secrets.token_bytes(32)
    if settings.kms_backend == "vault" and settings.vault_token:
        # Vault Transit-shaped: AES-GCM under vault token-derived key (adapter; swap for HTTP Transit later)
        inner = wrap_dek(dek, _vault_master(settings)).removeprefix(_WRAP_PREFIX_LOCAL)
        wrapped = _WRAP_PREFIX_VAULT + inner
    else:
        wrapped = wrap_dek(dek, _master_key_bytes(settings))
    row = TenantCryptoKey(tenant_id=tenant_id, wrapped_dek=wrapped, algorithm="aes-256-gcm")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def rotate_tenant_key(db: Session, settings: Settings, tenant_id: str) -> TenantCryptoKey:
    row = ensure_tenant_key(db, settings, tenant_id)
    dek = secrets.token_bytes(32)
    if settings.kms_backend == "vault" and settings.vault_token:
        inner = wrap_dek(dek, _vault_master(settings)).removeprefix(_WRAP_PREFIX_LOCAL)
        row.wrapped_dek = _WRAP_PREFIX_VAULT + inner
    else:
        row.wrapped_dek = wrap_dek(dek, _master_key_bytes(settings))
    row.algorithm = "aes-256-gcm"
    row.rotated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def encrypt_credentials(settings: Settings, tenant_id: str, credentials: dict, wrapped_dek: str) -> str:
    dek = unwrap_dek(wrapped_dek, _resolve_wrap_secret(settings, wrapped_dek))
    payload = json.dumps(credentials, separators=(",", ":"), sort_keys=True).encode("utf-8")
    nonce = secrets.token_bytes(12)
    aad = f"tenant:{tenant_id}".encode("utf-8")
    ct = AESGCM(dek).encrypt(nonce, payload, aad)
    return base64.urlsafe_b64encode(nonce + ct).decode("ascii")


def decrypt_credentials(settings: Settings, tenant_id: str, blob: str, wrapped_dek: str) -> dict:
    dek = unwrap_dek(wrapped_dek, _resolve_wrap_secret(settings, wrapped_dek))
    raw = base64.urlsafe_b64decode(blob.encode("ascii"))
    if len(raw) < 13:
        raise ValueError("ciphertext too short")
    nonce, ct = raw[:12], raw[12:]
    aad = f"tenant:{tenant_id}".encode("utf-8")
    try:
        payload = AESGCM(dek).decrypt(nonce, ct, aad)
    except Exception as exc:
        raise ValueError("credential decrypt failed") from exc
    return json.loads(payload.decode("utf-8"))


def security_posture(settings: Settings) -> dict:
    return {
        "require_tls": settings.require_tls,
        "encryption_at_rest_verified": settings.encryption_at_rest_verified,
        "kms_backend": settings.kms_backend,
        "crypto_algorithm": "aes-256-gcm",
        "llm_mode": settings.llm_mode,
        "llm_no_train": settings.llm_no_train,
        "auth_provider": settings.auth_provider,
        "legacy_note": _LEGACY_XOR_NOTE,
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
                    logger.exception("vector delete failed for chunk %s", chunk.id)
            db.delete(chunk)
            removed["chunks"] += 1
        if object_storage and doc.object_key:
            try:
                object_storage.delete(doc.object_key)
                removed["objects"] += 1
            except Exception:
                logger.exception("object delete failed for %s", doc.object_key)
        if graph:
            try:
                graph.delete_node(str(doc.id), tenant_id=tenant_id)
                removed["graph"] += 1
            except TypeError:
                try:
                    graph.delete_node(str(doc.id))
                    removed["graph"] += 1
                except Exception:
                    logger.exception("graph delete failed for %s", doc.id)
            except Exception:
                logger.exception("graph delete failed for %s", doc.id)
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
        # If already envelope-encrypted, re-wrap plaintext when nested under encrypted key
        if "encrypted" in creds and len(creds) == 1 or (set(creds.keys()) <= {"encrypted", "rotated_at"}):
            try:
                plain = decrypt_credentials(settings, tenant_id, creds["encrypted"], key.wrapped_dek)
            except Exception:
                plain = {k: v for k, v in creds.items() if k not in {"encrypted", "rotated_at"}}
                if not plain:
                    continue
        else:
            plain = {k: v for k, v in creds.items() if k not in {"encrypted", "rotated_at"}}
        blob = encrypt_credentials(settings, tenant_id, plain, key.wrapped_dek)
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
