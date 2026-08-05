def test_login_and_me(client, test_settings, auth_headers):
    bad = client.post(
        "/v1/auth/login",
        json={"email": test_settings.dev_admin_email, "password": "wrong"},
    )
    assert bad.status_code == 401

    me = client.get("/v1/auth/me", headers=auth_headers)
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == test_settings.dev_admin_email
    assert body["role"] == "admin"


def test_me_unauthorized(client):
    res = client.get("/v1/auth/me")
    assert res.status_code == 401
