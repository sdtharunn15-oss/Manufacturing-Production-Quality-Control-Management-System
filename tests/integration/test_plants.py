def test_create_plant(client):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Plant Manager Test",
            "email": "plantmanager@test.com",
            "password": "Test@12345",
            "role": "Plant Manager",
        },
    )

    assert response.status_code == 201

    login = client.post(
        "/auth/login",
        json={
            "email": "plantmanager@test.com",
            "password": "Test@12345",
        },
    )

    assert login.status_code == 200

    token = login.json()["access_token"]

    response = client.post(
        "/plants",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Test Manufacturing Plant",
            "code": "TMP-001",
            "location": "Chennai",
            "description": "Test production plant",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Test Manufacturing Plant"
    assert data["code"] == "TMP-001"
    assert data["location"] == "Chennai"
    assert data["is_active"] is True


def test_list_plants_requires_authentication(client):
    response = client.get("/plants")

    assert response.status_code in (401, 403)
