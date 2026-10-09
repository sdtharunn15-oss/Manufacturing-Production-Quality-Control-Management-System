import uuid


def unique_code(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def register_and_login(client, role):
    email = f"{uuid.uuid4().hex[:8]}@example.com"

    register_response = client.post(
        "/auth/register",
        json={
            "full_name": f"Shift {role}",
            "email": email,
            "password": "Test@12345",
            "role": role,
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "Test@12345",
        },
    )

    assert login_response.status_code == 200

    return login_response.json()["access_token"]


def create_plant(client, token):
    response = client.post(
        "/plants",
        json={
            "name": f"Shift Plant {uuid.uuid4().hex[:8]}",
            "code": unique_code("SP"),
            "location": "Chennai",
            "description": "Shift test plant",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_shift(client, token, plant_id):
    response = client.post(
        "/shifts",
        json={
            "name": f"Morning Shift {uuid.uuid4().hex[:8]}",
            "code": unique_code("SH"),
            "plant_id": plant_id,
            "start_time": "08:00:00",
            "end_time": "16:00:00",
            "description": "Morning production shift",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    return response.json()


def test_create_shift(client):
    token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, token)

    shift = create_shift(client, token, plant_id)

    assert shift["name"].startswith("Morning Shift")
    assert shift["code"].startswith("SH-")
    assert shift["plant_id"] == plant_id
    assert shift["start_time"] == "08:00:00"
    assert shift["end_time"] == "16:00:00"
    assert shift["is_active"] is True


def test_duplicate_shift_code(client):
    token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, token)

    code = unique_code("DUPSH")

    payload = {
        "name": "Duplicate Shift",
        "code": code,
        "plant_id": plant_id,
        "start_time": "08:00:00",
        "end_time": "16:00:00",
        "description": "Duplicate code test",
    }

    first = client.post(
        "/shifts",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    second = client.post(
        "/shifts",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Shift code already exists"


def test_create_shift_requires_management_role(client):
    token = register_and_login(client, "Worker")

    response = client.post(
        "/shifts",
        json={
            "name": "Unauthorized Shift",
            "code": unique_code("DENY"),
            "plant_id": 1,
            "start_time": "08:00:00",
            "end_time": "16:00:00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_create_shift_with_nonexistent_plant(client):
    token = register_and_login(client, "Plant Manager")

    response = client.post(
        "/shifts",
        json={
            "name": "Invalid Plant Shift",
            "code": unique_code("BAD"),
            "plant_id": 999999,
            "start_time": "08:00:00",
            "end_time": "16:00:00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Plant not found"


def test_create_shift_with_same_start_and_end_time(client):
    token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, token)

    response = client.post(
        "/shifts",
        json={
            "name": "Invalid Time Shift",
            "code": unique_code("TIME"),
            "plant_id": plant_id,
            "start_time": "08:00:00",
            "end_time": "08:00:00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Shift start time and end time cannot be the same"
    )


def test_list_shifts(client):
    token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, token)

    shift = create_shift(client, token, plant_id)

    response = client.get(
        "/shifts",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert any(item["id"] == shift["id"] for item in response.json())


def test_list_shifts_by_plant(client):
    token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, token)

    shift = create_shift(client, token, plant_id)

    response = client.get(
        f"/shifts/plant/{plant_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    shifts = response.json()

    assert any(item["id"] == shift["id"] for item in shifts)


def test_list_shifts_by_nonexistent_plant(client):
    token = register_and_login(client, "Plant Manager")

    response = client.get(
        "/shifts/plant/999999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Plant not found"


def test_get_shift(client):
    token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, token)

    shift = create_shift(client, token, plant_id)

    response = client.get(
        f"/shifts/{shift['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == shift["id"]


def test_get_nonexistent_shift(client):
    token = register_and_login(client, "Plant Manager")

    response = client.get(
        "/shifts/999999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Shift not found"


def test_update_shift(client):
    token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, token)

    shift = create_shift(client, token, plant_id)

    response = client.patch(
        f"/shifts/{shift['id']}",
        json={
            "name": "Updated Morning Shift",
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "description": "Updated shift",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    updated = response.json()

    assert updated["name"] == "Updated Morning Shift"
    assert updated["start_time"] == "09:00:00"
    assert updated["end_time"] == "17:00:00"
    assert updated["description"] == "Updated shift"


def test_update_shift_with_same_times_rejected(client):
    token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, token)

    shift = create_shift(client, token, plant_id)

    response = client.patch(
        f"/shifts/{shift['id']}",
        json={
            "start_time": "10:00:00",
            "end_time": "10:00:00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Shift start time and end time cannot be the same"
    )


def test_update_shift_requires_management_role(client):
    manager_token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, manager_token)
    shift = create_shift(client, manager_token, plant_id)

    worker_token = register_and_login(client, "Worker")

    response = client.patch(
        f"/shifts/{shift['id']}",
        json={
            "name": "Unauthorized Update",
        },
        headers={"Authorization": f"Bearer {worker_token}"},
    )

    assert response.status_code == 403


def test_deactivate_shift(client):
    token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, token)

    shift = create_shift(client, token, plant_id)

    response = client.patch(
        f"/shifts/{shift['id']}/status",
        json={
            "is_active": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_activate_shift(client):
    token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, token)

    shift = create_shift(client, token, plant_id)

    deactivate = client.patch(
        f"/shifts/{shift['id']}/status",
        json={
            "is_active": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert deactivate.status_code == 200

    activate = client.patch(
        f"/shifts/{shift['id']}/status",
        json={
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert activate.status_code == 200
    assert activate.json()["is_active"] is True


def test_update_shift_status_requires_management_role(client):
    manager_token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, manager_token)
    shift = create_shift(client, manager_token, plant_id)

    worker_token = register_and_login(client, "Worker")

    response = client.patch(
        f"/shifts/{shift['id']}/status",
        json={
            "is_active": False,
        },
        headers={"Authorization": f"Bearer {worker_token}"},
    )

    assert response.status_code == 403


def test_get_shifts_requires_authentication(client):
    response = client.get("/shifts")

    assert response.status_code in {401, 403}


def test_create_shift_on_inactive_plant_rejected(client, db):
    plant_manager_token = register_and_login(client, "Plant Manager")

    plant_id = create_plant(
        client,
        plant_manager_token,
    )

    # Mark the plant as inactive directly in the test database.
    # This allows us to test the shift service's inactive-plant rule
    # without deleting the plant completely.
    from app.models.plant import Plant

    plant = db.query(Plant).filter(Plant.id == plant_id).first()

    assert plant is not None

    plant.is_active = False
    db.commit()
    db.refresh(plant)

    assert plant.is_active is False

    response = client.post(
        "/shifts",
        json={
            "name": "Inactive Plant Shift",
            "code": unique_code("INACTIVE"),
            "plant_id": plant_id,
            "start_time": "08:00:00",
            "end_time": "16:00:00",
        },
        headers={
            "Authorization": f"Bearer {plant_manager_token}"
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Shift cannot be created for an inactive plant"
    )