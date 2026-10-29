import base64

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.services.saml_auth import expected_saml_hmac, exchange_saml_for_session, verify_saml_response
from app.services.security import (
    decrypt_credentials,
    encrypt_credentials,
    ensure_tenant_key,
    wrap_dek,
    unwrap_dek,
)


def _saml_b64(email: str = "saml.user@example.com") -> str:
    xml = f"""<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">
  <saml:Assertion>
    <saml:NameID>{email}</saml:NameID>
    <saml:Attribute Name="email"><saml:AttributeValue>{email}</saml:AttributeValue></saml:Attribute>
  </saml:Assertion>
</samlp:Response>"""
    return base64.b64encode(xml.encode("utf-8")).decode("ascii")


def test_aes_gcm_wrap_roundtrip_and_tamper():
    secret = "master-key-for-tests"
    dek = b"\x01" * 32
    wrapped = wrap_dek(dek, secret)
    assert wrapped.startswith("aesgcm:")
    assert unwrap_dek(wrapped, secret) == dek

    # Tamper ciphertext
    raw = wrapped.split(":", 1)[1]
    blob = bytearray(base64.urlsafe_b64decode(raw.encode("ascii")))
    blob[-1] ^= 0xFF
    tampered = "aesgcm:" + base64.urlsafe_b64encode(bytes(blob)).decode("ascii")
    with pytest.raises(Exception):
        unwrap_dek(tampered, secret)

    with pytest.raises(Exception):
        unwrap_dek(wrapped, "other-master")


def test_credential_encrypt_wrong_tenant_aad(db, test_settings):
    key = ensure_tenant_key(db, test_settings, "tenant-a")
    blob = encrypt_credentials(test_settings, "tenant-a", {"token": "abc"}, key.wrapped_dek)
    assert decrypt_credentials(test_settings, "tenant-a", blob, key.wrapped_dek)["token"] == "abc"
    with pytest.raises(ValueError):
        decrypt_credentials(test_settings, "tenant-b", blob, key.wrapped_dek)


def test_prod_boot_guards_demo_secret():
    with pytest.raises(ValidationError):
        Settings(
            environment="prod",
            secret_key="dev-secret-change-me-in-production",
            require_tls=True,
            auth_provider="oidc",
            auth_issuer="https://idp.example",
            auth_audience="eb",
            embedding_provider="openai",
            llm_api_key="sk-test",
        )


def test_prod_refuses_hash_embeddings_and_unsigned_saml():
    with pytest.raises(ValidationError):
        Settings(
            environment="staging",
            secret_key="prod-secret-not-demo",
            require_tls=True,
            auth_provider="oidc",
            auth_issuer="https://idp.example",
            auth_audience="eb",
            embedding_provider="hash",
            llm_api_key="sk-test",
        )
    with pytest.raises(ValidationError):
        Settings(
            environment="prod",
            secret_key="prod-secret-not-demo",
            require_tls=True,
            auth_provider="saml",
            saml_pilot_unsigned=True,
            saml_idp_x509_cert="cert",
            embedding_provider="openai",
            llm_api_key="sk-test",
        )


def test_prod_refuses_dev_auth():
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            secret_key="prod-secret-not-demo",
            require_tls=True,
            auth_provider="dev",
            embedding_provider="openai",
            llm_api_key="sk-test",
        )


def test_saml_unsigned_forbidden_in_prod_like_and_sig_required(db, test_settings):
    resp = _saml_b64()
    local = Settings(
        environment="local",
        auth_provider="saml",
        saml_pilot_unsigned=True,
        secret_key="test-secret",
        default_tenant_id="acme",
    )
    tokens = exchange_saml_for_session(db, local, saml_response=resp, tenant_id="acme")
    assert tokens["access_token"]

    signed = Settings(
        environment="test",
        auth_provider="saml",
        saml_pilot_unsigned=False,
        saml_idp_x509_cert="idp-shared-secret",
        secret_key="test-secret",
        default_tenant_id="acme",
    )
    with pytest.raises(ValueError, match="integrity"):
        verify_saml_response(signed, resp, relay_state="")
    sig = expected_saml_hmac(signed, resp)
    assert verify_saml_response(signed, resp, relay_state=f"sig={sig}") is True
    with pytest.raises(ValueError):
        verify_saml_response(signed, resp, relay_state="sig=deadbeef")
