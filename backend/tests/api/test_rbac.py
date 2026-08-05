def test_employee_cannot_list_users(client, user_headers):
    res = client.get("/v1/users", headers=user_headers)
    assert res.status_code == 403


def test_admin_can_list_and_invite(client, auth_headers):
    listed = client.get("/v1/users", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) >= 2

    created = client.post(
        "/v1/users",
        headers=auth_headers,
        json={
            "email": "newbie@example.com",
            "password": "secret12",
            "full_name": "Newbie",
            "role": "employee",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["email"] == "newbie@example.com"
