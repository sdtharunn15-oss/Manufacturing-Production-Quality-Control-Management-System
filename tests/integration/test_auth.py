def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Test Admin",
            "email": "testadmin@example.com",
            "password": "Test@12345",
            "role": "Worker",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "testadmin@example.com"
    assert data["full_name"] == "Test Admin"
    assert data["role"] == "Worker"
    assert data["is_active"] is True


def test_login_invalid_credentials(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "doesnotexist@example.com",
            "password": "WrongPassword@123",
        },
    )

    assert response.status_code == 401


def test_duplicate_registration(client):
    payload = {
        "full_name": "Duplicate User",
        "email": "duplicate@example.com",
        "password": "Test@12345",
        "role": "Worker",
    }

    first = client.post("/auth/register", json=payload)
    second = client.post("/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 400
