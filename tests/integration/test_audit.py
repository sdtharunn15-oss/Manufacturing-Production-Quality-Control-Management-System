
from uuid import uuid4

import pytest


PASSWORD = "Test@12345"


def register_and_login(
    client,
    email=None,
    role="Super Admin",
):
    if email is None:
        email = f"audit-{uuid4().hex}@example.com"

    register_response = client.post(
        "/auth/register",
        json={
            "full_name": "Audit Test User",
            "email": email,
            "password": PASSWORD,
            "role": role,
        },
    )

    assert register_response.status_code in (200, 201), (
        register_response.text
    )

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
    )

    assert login_response.status_code == 200, login_response.text

    access_token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {access_token}"
    }


def test_audit_logs_require_authentication(client):
    response = client.get("/audit-logs")

    assert response.status_code in (401, 403)


def test_list_audit_logs_as_super_admin(client):
    headers = register_and_login(client)

    response = client.get(
        "/audit-logs",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_get_audit_log_not_found(client):
    headers = register_and_login(client)

    response = client.get(
        "/audit-logs/999999",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Audit log not found"


def test_non_admin_cannot_list_audit_logs(client):
    headers = register_and_login(
        client,
        role="Production Manager",
    )

    response = client.get(
        "/audit-logs",
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You do not have permission to view audit logs"
    )


def test_non_admin_cannot_get_single_audit_log(client):
    headers = register_and_login(
        client,
        role="Quality Manager",
    )

    response = client.get(
        "/audit-logs/1",
        headers=headers,
    )

    assert response.status_code == 403


def test_non_admin_cannot_list_user_audit_logs(client):
    headers = register_and_login(
        client,
        role="Plant Manager",
    )

    response = client.get(
        "/audit-logs/user/1",
        headers=headers,
    )

    assert response.status_code == 403


def test_audit_log_response_fields(client):
    headers = register_and_login(client)

    response = client.get(
        "/audit-logs",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    audit_logs = response.json()

    assert isinstance(audit_logs, list)

    for log in audit_logs:
        assert "id" in log
        assert "user_id" in log
        assert "action" in log
        assert "entity_type" in log
        assert "entity_id" in log
        assert "description" in log
        assert "ip_address" in log
        assert "created_at" in log


def test_inactive_user_cannot_access_audit_logs(client):
    headers = register_and_login(client)

    me_response = client.get(
        "/auth/me",
        headers=headers,
    )

    assert me_response.status_code == 200, me_response.text

    user_id = me_response.json()["id"]

    deactivate_response = client.patch(
        f"/auth/users/{user_id}/deactivate",
        headers=headers,
    )

    if deactivate_response.status_code not in (200, 204):
        pytest.skip(
            "Self-deactivation is not supported by the current "
            "authentication implementation."
        )

    response = client.get(
        "/audit-logs",
        headers=headers,
    )

    assert response.status_code in (401, 403)