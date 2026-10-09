import uuid


def get_machine_manager_token(client):
    unique = uuid.uuid4().hex[:8]
    email = f"machine-manager-{unique}@test.com"

    register = client.post(
        "/auth/register",
        json={
            "full_name": "Machine Manager",
            "email": email,
            "password": "Test@12345",
            "role": "Plant Manager",
        },
    )

    assert register.status_code == 201

    login = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "Test@12345",
        },
    )

    assert login.status_code == 200

    return login.json()["access_token"]


def create_plant(client, token):
    unique = uuid.uuid4().hex[:8]

    response = client.post(
        "/plants",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": f"Machine Test Plant {unique}",
            "code": f"MP-{unique}",
            "location": "Chennai",
            "description": "Plant for machine testing",
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_production_line(client, token, plant_id):
    unique = uuid.uuid4().hex[:8]

    response = client.post(
        "/production-lines",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": f"Machine Test Line {unique}",
            "code": f"ML-{unique}",
            "plant_id": plant_id,
            "description": "Production line for machine testing",
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_machine_setup(client, token):
    plant_id = create_plant(client, token)

    line_id = create_production_line(
        client,
        token,
        plant_id,
    )

    return plant_id, line_id


def create_machine(client, token, plant_id, line_id):
    unique = uuid.uuid4().hex[:8]

    response = client.post(
        "/machines",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": f"CNC Machine {unique}",
            "code": f"MC-{unique}",
            "machine_type": "CNC",
            "plant_id": plant_id,
            "production_line_id": line_id,
            "status": "Available",
            "installation_date": "2026-01-15",
            "description": "Machine for integration testing",
        },
    )

    assert response.status_code == 201, (
        f"Machine creation failed: "
        f"{response.status_code} - {response.text}"
    )

    return response.json()


def test_create_machine(client):
    token = get_machine_manager_token(client)

    plant_id, line_id = create_machine_setup(
        client,
        token,
    )

    data = create_machine(
        client,
        token,
        plant_id,
        line_id,
    )

    assert data["name"].startswith("CNC Machine")
    assert data["machine_type"] == "CNC"
    assert data["plant_id"] == plant_id
    assert data["production_line_id"] == line_id
    assert data["status"] == "Available"
    assert data["is_active"] is True


def test_list_machines(client):
    token = get_machine_manager_token(client)

    plant_id, line_id = create_machine_setup(
        client,
        token,
    )

    create_machine(
        client,
        token,
        plant_id,
        line_id,
    )

    response = client.get(
        "/machines",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) >= 1


def test_get_machine(client):
    token = get_machine_manager_token(client)

    plant_id, line_id = create_machine_setup(
        client,
        token,
    )

    machine = create_machine(
        client,
        token,
        plant_id,
        line_id,
    )

    machine_id = machine["id"]

    response = client.get(
        f"/machines/{machine_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == machine_id


def test_list_line_machines(client):
    token = get_machine_manager_token(client)

    plant_id, line_id = create_machine_setup(
        client,
        token,
    )

    machine = create_machine(
        client,
        token,
        plant_id,
        line_id,
    )

    response = client.get(
        f"/machines/line/{line_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert any(
        item["id"] == machine["id"]
        for item in data
    )


def test_update_machine(client):
    token = get_machine_manager_token(client)

    plant_id, line_id = create_machine_setup(
        client,
        token,
    )

    machine = create_machine(
        client,
        token,
        plant_id,
        line_id,
    )

    machine_id = machine["id"]

    response = client.patch(
        f"/machines/{machine_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Updated CNC Machine",
            "description": "Updated machine",
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated CNC Machine"
    assert response.json()["description"] == "Updated machine"


def test_change_machine_status(client):
    token = get_machine_manager_token(client)

    plant_id, line_id = create_machine_setup(
        client,
        token,
    )

    machine = create_machine(
        client,
        token,
        plant_id,
        line_id,
    )

    machine_id = machine["id"]

    response = client.patch(
        f"/machines/{machine_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "status_value": "Under Maintenance",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Under Maintenance"


def test_available_machine_check(client):
    token = get_machine_manager_token(client)

    plant_id, line_id = create_machine_setup(
        client,
        token,
    )

    machine = create_machine(
        client,
        token,
        plant_id,
        line_id,
    )

    machine_id = machine["id"]

    response = client.post(
        f"/machines/{machine_id}/check-availability",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == machine_id
    assert response.json()["status"] == "Available"


def test_unavailable_machine_check_fails(client):
    token = get_machine_manager_token(client)

    plant_id, line_id = create_machine_setup(
        client,
        token,
    )

    machine = create_machine(
        client,
        token,
        plant_id,
        line_id,
    )

    machine_id = machine["id"]

    status_response = client.patch(
        f"/machines/{machine_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "status_value": "Under Maintenance",
        },
    )

    assert status_response.status_code == 200

    response = client.post(
        f"/machines/{machine_id}/check-availability",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "not available" in response.json()["detail"].lower()
def test_soft_delete_machine(client):
    # Create Plant Manager to create the required plant and line
    register_response = client.post(
        "/auth/register",
        json={
            "full_name": "Machine Setup Manager",
            "email": "machine_setup_manager@example.com",
            "password": "Test@12345",
            "role": "Plant Manager",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": "machine_setup_manager@example.com",
            "password": "Test@12345",
        },
    )
    assert login_response.status_code == 200

    manager_token = login_response.json()["access_token"]
    manager_headers = {
        "Authorization": f"Bearer {manager_token}"
    }

    # Create plant
    plant_response = client.post(
        "/plants",
        headers=manager_headers,
        json={
            "name": "Delete Test Plant",
            "code": "DEL-PLANT-01",
            "location": "Chennai",
            "description": "Plant for machine delete test",
        },
    )
    assert plant_response.status_code == 201
    plant_id = plant_response.json()["id"]

    # Create production line
    line_response = client.post(
        "/production-lines",
        headers=manager_headers,
        json={
            "name": "Delete Test Line",
            "code": "DEL-LINE-01",
            "plant_id": plant_id,
            "description": "Line for machine delete test",
        },
    )
    assert line_response.status_code == 201
    line_id = line_response.json()["id"]

    # Create machine
    machine_response = client.post(
        "/machines",
        headers=manager_headers,
        json={
            "name": "Delete Test Machine",
            "code": "DEL-MACHINE-01",
            "machine_type": "CNC",
            "plant_id": plant_id,
            "production_line_id": line_id,
            "status": "Available",
        },
    )
    assert machine_response.status_code == 201
    machine_id = machine_response.json()["id"]

    # Create Super Admin
    register_admin = client.post(
        "/auth/register",
        json={
            "full_name": "Machine Delete Admin",
            "email": "machine_delete_admin@example.com",
            "password": "Test@12345",
            "role": "Super Admin",
        },
    )
    assert register_admin.status_code == 201

    login_admin = client.post(
        "/auth/login",
        json={
            "email": "machine_delete_admin@example.com",
            "password": "Test@12345",
        },
    )
    assert login_admin.status_code == 200

    admin_token = login_admin.json()["access_token"]

    # Delete machine as Super Admin
    response = client.delete(
        f"/machines/{machine_id}",
        headers={
            "Authorization": f"Bearer {admin_token}"
        },
    )

    assert response.status_code == 204