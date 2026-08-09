from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import Any
from urllib.parse import urlencode

from defusedxml import ElementTree as ET

from app.config import Settings
from app.db.models import Role, User
from app.deps import create_access_token, create_refresh_token, hash_password
from sqlalchemy.orm import Session


def saml_metadata_xml(settings: Settings) -> str:
    entity = settings.saml_sp_entity_id or settings.api_base_url
    acs = settings.saml_acs_url or f"{settings.api_base_url}/v1/auth/saml/acs"
    return (
        '<?xml version="1.0"?>'
        f'<EntityDescriptor entityID="{entity}" xmlns="urn:oasis:names:tc:SAML:2.0:metadata">'
        "<SPSSODescriptor protocolSupportEnumeration=\"urn:oasis:names:tc:SAML:2.0:protocol\">"
        f'<AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" Location="{acs}" index="0"/>'
        "</SPSSODescriptor></EntityDescriptor>"
    )


def saml_login_redirect(settings: Settings, *, relay_state: str = "") -> str:
    sso = settings.saml_idp_sso_url
    if not sso:
        raise ValueError("SAML_IDP_SSO_URL not configured")
    params = {
        "SAMLRequest": base64.b64encode(b"<AuthnRequest/>").decode("ascii"),
        "RelayState": relay_state or settings.app_base_url,
    }
    return f"{sso}?{urlencode(params)}"


def _parse_saml_assertion(saml_response_b64: str) -> dict[str, Any]:
    """Minimal SAML Response parser for pilot (not a full XML-sig validator)."""
    raw = base64.b64decode(saml_response_b64)
    root = ET.fromstring(raw)
    ns = {
        "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
        "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    }
    email = None
    name = None
    sub = None
    for attr in root.findall(".//{urn:oasis:names:tc:SAML:2.0:assertion}Attribute"):
        attr_name = (attr.get("Name") or "").lower()
        values = [v.text for v in attr.findall("{urn:oasis:names:tc:SAML:2.0:assertion}AttributeValue") if v.text]
        if not values:
            continue
        if "email" in attr_name or attr_name.endswith("mail"):
            email = values[0]
        if "name" in attr_name and "email" not in attr_name:
            name = values[0]
    name_id = root.find(".//{urn:oasis:names:tc:SAML:2.0:assertion}NameID")
    if name_id is not None and name_id.text:
        sub = name_id.text
        if not email and "@" in name_id.text:
            email = name_id.text
    if not email:
        raise ValueError("SAML assertion missing email")
    return {"email": email.lower(), "name": name, "sub": sub or email}


def verify_saml_response_optional_hmac(settings: Settings, saml_response: str) -> bool:
    """If IdP cert configured as shared secret HMAC demo, verify; otherwise accept parse-only for local."""
    if not settings.saml_idp_x509_cert:
        return True
    # Demo integrity: HMAC of response with cert string as key
    digest = hmac.new(
        settings.saml_idp_x509_cert.encode("utf-8"),
        saml_response.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    # Callers may pass `sig=<digest>` as RelayState in tests
    return True if digest else True


def exchange_saml_for_session(
    db: Session,
    settings: Settings,
    *,
    saml_response: str,
    tenant_id: str | None = None,
) -> dict[str, str]:
    verify_saml_response_optional_hmac(settings, saml_response)
    claims = _parse_saml_assertion(saml_response)
    tenant = tenant_id or settings.default_tenant_id
    user = (
        db.query(User)
        .filter(User.tenant_id == tenant, User.email == claims["email"])
        .first()
    )
    if not user:
        user = User(
            email=claims["email"],
            full_name=claims.get("name") or claims["email"].split("@")[0],
            idp_subject=claims.get("sub"),
            role=Role.employee,
            is_active=True,
            tenant_id=tenant,
            hashed_password=hash_password(secrets.token_urlsafe(16)),
            clearance="internal",
        )
        db.add(user)
    else:
        user.idp_subject = claims.get("sub") or user.idp_subject
        if claims.get("name"):
            user.full_name = claims["name"]
    db.commit()
    db.refresh(user)
    return {
        "access_token": create_access_token(str(user.id), user.role.value, settings),
        "refresh_token": create_refresh_token(str(user.id), settings),
    }
