from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import Any
from urllib.parse import urlencode

from defusedxml import ElementTree as ET
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import Role, User
from app.deps import create_access_token, create_refresh_token, hash_password


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
    raw = base64.b64decode(saml_response_b64)
    root = ET.fromstring(raw)
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


def expected_saml_hmac(settings: Settings, saml_response: str) -> str:
    secret = (settings.saml_idp_x509_cert or settings.secret_key).encode("utf-8")
    return hmac.new(secret, saml_response.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_saml_response(
    settings: Settings,
    saml_response: str,
    *,
    relay_state: str | None = None,
) -> bool:
    """
    Integrity check for SAML responses.

    - Production/staging: unsigned pilot mode is forbidden; require HMAC in RelayState `sig=<hex>`
      (stand-in until full XML-DSig is wired) using IdP cert/shared secret.
    - Local/test with SAML_PILOT_UNSIGNED=true: parse-only allowed.
    """
    env = (settings.environment or "local").lower()
    prod_like = env in {"prod", "production", "staging"}

    if settings.saml_pilot_unsigned:
        if prod_like:
            raise ValueError("SAML_PILOT_UNSIGNED is forbidden when ENVIRONMENT is staging/production")
        return True

    if not settings.saml_idp_x509_cert and prod_like:
        raise ValueError("SAML_IDP_X509_CERT (or shared secret) required for signed SAML verification")

    expected = expected_saml_hmac(settings, saml_response)
    provided = None
    if relay_state and "sig=" in relay_state:
        for part in relay_state.split("&"):
            if part.startswith("sig="):
                provided = part.split("=", 1)[1]
                break
    if not provided:
        raise ValueError("SAML response missing integrity signature (RelayState sig=...)")
    if not hmac.compare_digest(expected, provided):
        raise ValueError("SAML response integrity check failed")
    return True


# Back-compat name used by older callers/tests
def verify_saml_response_optional_hmac(
    settings: Settings,
    saml_response: str,
    relay_state: str | None = None,
) -> bool:
    return verify_saml_response(settings, saml_response, relay_state=relay_state)


def exchange_saml_for_session(
    db: Session,
    settings: Settings,
    *,
    saml_response: str,
    tenant_id: str | None = None,
    relay_state: str | None = None,
) -> dict[str, str]:
    verify_saml_response(settings, saml_response, relay_state=relay_state)
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
