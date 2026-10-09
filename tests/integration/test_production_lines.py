def get_plant_manager_token(client):
    register = client.post(
        "/auth/register",
        json={
            "full_name": "Line Manager Test",
            "email": "linemanager@test.com",
            "password": "Test@12345",
            "role": "Plant Manager",
        },
    )

    assert register.status_code == 201

    login = client.post(
        "/auth/login",
        json={
            "email": "linemanager@test.com",
            "password": "Test@12345",
        },
    )

    assert login.status_code == 200

    return login.json()["access_token"]


def create_test_plant(client, token):
    response = client.post(
        "/plants",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Line Test Plant",
            "code": "LTP-001",
            "location": "Chennai",
            "description": "Plant for production line tests",
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


def test_create_production_line(client):
    token = get_plant_manager_token(client)
    plant_id = create_test_plant(client, token)

    response = client.post(
        "/production-lines",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Test Assembly Line",
            "code": "TAL-001",
            "plant_id": plant_id,
            "description": "Test production line",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Test Assembly Line"
    assert data["code"] == "TAL-001"
    assert data["plant_id"] == plant_id
    assert data["is_active"] is True


def test_list_production_lines_requires_authentication(client):
    response = client.get("/production-lines")

    assert response.status_code in (401, 403)
