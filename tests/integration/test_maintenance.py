from datetime import datetime, timedelta
from uuid import uuid4

from app.models.machine import Machine


def unique(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def register_and_login(client, role: str):
    email = f"{role.lower().replace(' ', '_').replace('-', '_')}_{uuid4().hex[:8]}@example.com"

    response = client.post(
        "/auth/register",
        json={
            "full_name": f"Test {role}",
            "email": email,
            "password": "Test@12345",
            "role": role,
        },
    )

    assert response.status_code == 201, response.text

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "Test@12345",
        },
    )

    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def create_plant(client, token: str):
    response = client.post(
        "/plants",
        json={
            "name": unique("Maintenance Plant"),
            "code": unique("MPL"),
            "location": "Chennai",
            "description": "Maintenance test plant",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_production_line(client, token: str, plant_id: int):
    response = client.post(
        "/production-lines",
        json={
            "name": unique("Maintenance Line"),
            "code": unique("MLN"),
            "plant_id": plant_id,
            "description": "Maintenance test line",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_machine(client, token: str, plant_id: int, line_id: int):
    response = client.post(
        "/machines",
        json={
            "name": unique("Maintenance Machine"),
            "code": unique("MCH"),
            "machine_type": "CNC",
            "plant_id": plant_id,
            "production_line_id": line_id,
            "status": "Available",
            "description": "Maintenance test machine",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text
    return response.json()["id"]


def setup_machine(client):
    plant_manager_token = register_and_login(client, "Plant Manager")

    plant_id = create_plant(client, plant_manager_token)

    line_id = create_production_line(
        client,
        plant_manager_token,
        plant_id,
    )

    machine_id = create_machine(
        client,
        plant_manager_token,
        plant_id,
        line_id,
    )

    return plant_manager_token, plant_id, line_id, machine_id


def create_maintenance(
    client,
    token: str,
    machine_id: int,
    maintenance_type: str = "Preventive",
    priority: str = "Medium",
):
    response = client.post(
        "/maintenance",
        json={
            "maintenance_number": unique("MNT"),
            "machine_id": machine_id,
            "maintenance_type": maintenance_type,
            "priority": priority,
            "scheduled_date": (
                datetime.utcnow() + timedelta(days=1)
            ).isoformat(),
            "description": "Routine maintenance",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------
# CREATE
# ---------------------------------------------------------


def test_create_maintenance_success(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    data = create_maintenance(client, token, machine_id)

    assert data["machine_id"] == machine_id
    assert data["maintenance_type"] == "Preventive"
    assert data["priority"] == "Medium"
    assert data["status"] == "Scheduled"
    assert data["created_by"] is not None


def test_create_maintenance_with_all_valid_types(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    for maintenance_type in [
        "Preventive",
        "Corrective",
        "Emergency",
        "Inspection",
    ]:
        data = create_maintenance(
            client,
            token,
            machine_id,
            maintenance_type=maintenance_type,
        )

        assert data["maintenance_type"] == maintenance_type
        assert data["status"] == "Scheduled"


def test_create_maintenance_with_all_valid_priorities(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    for priority in [
        "Low",
        "Medium",
        "High",
        "Critical",
    ]:
        data = create_maintenance(
            client,
            token,
            machine_id,
            priority=priority,
        )

        assert data["priority"] == priority


def test_create_maintenance_invalid_type_rejected(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    response = client.post(
        "/maintenance",
        json={
            "maintenance_number": unique("INVALIDTYPE"),
            "machine_id": machine_id,
            "maintenance_type": "Random",
            "priority": "Medium",
            "scheduled_date": (
                datetime.utcnow() + timedelta(days=1)
            ).isoformat(),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid maintenance type"


def test_create_maintenance_invalid_priority_rejected(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    response = client.post(
        "/maintenance",
        json={
            "maintenance_number": unique("INVALIDPRIORITY"),
            "machine_id": machine_id,
            "maintenance_type": "Preventive",
            "priority": "Urgent",
            "scheduled_date": (
                datetime.utcnow() + timedelta(days=1)
            ).isoformat(),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid maintenance priority"


def test_create_maintenance_duplicate_number_rejected(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    maintenance_number = unique("DUPLICATE")

    payload = {
        "maintenance_number": maintenance_number,
        "machine_id": machine_id,
        "maintenance_type": "Preventive",
        "priority": "Medium",
        "scheduled_date": (
            datetime.utcnow() + timedelta(days=1)
        ).isoformat(),
    }

    first = client.post(
        "/maintenance",
        json=payload,
        headers=auth_headers(token),
    )

    assert first.status_code == 201, first.text

    second = client.post(
        "/maintenance",
        json=payload,
        headers=auth_headers(token),
    )

    assert second.status_code == 409
    assert (
        second.json()["detail"]
        == "Maintenance number already exists"
    )


def test_create_maintenance_machine_not_found(client):
    token = register_and_login(client, "Maintenance Engineer")

    response = client.post(
        "/maintenance",
        json={
            "maintenance_number": unique("NOMACHINE"),
            "machine_id": 999999,
            "maintenance_type": "Preventive",
            "priority": "Medium",
            "scheduled_date": (
                datetime.utcnow() + timedelta(days=1)
            ).isoformat(),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Machine not found"


def test_create_maintenance_inactive_machine_rejected(client, db):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    machine = db.query(Machine).filter(
        Machine.id == machine_id
    ).first()

    assert machine is not None

    machine.is_active = False
    db.commit()
    db.refresh(machine)

    response = client.post(
        "/maintenance",
        json={
            "maintenance_number": unique("INACTIVE"),
            "machine_id": machine_id,
            "maintenance_type": "Preventive",
            "priority": "Medium",
            "scheduled_date": (
                datetime.utcnow() + timedelta(days=1)
            ).isoformat(),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Cannot schedule maintenance for an inactive machine"
    )


# ---------------------------------------------------------
# ROLE PROTECTION
# ---------------------------------------------------------


def test_worker_cannot_create_maintenance(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Worker")

    response = client.post(
        "/maintenance",
        json={
            "maintenance_number": unique("WORKER"),
            "machine_id": machine_id,
            "maintenance_type": "Preventive",
            "priority": "Medium",
            "scheduled_date": (
                datetime.utcnow() + timedelta(days=1)
            ).isoformat(),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "You do not have permission to manage maintenance"
    )


def test_production_manager_cannot_create_maintenance(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Production Manager")

    response = client.post(
        "/maintenance",
        json={
            "maintenance_number": unique("PM"),
            "machine_id": machine_id,
            "maintenance_type": "Preventive",
            "priority": "Medium",
            "scheduled_date": (
                datetime.utcnow() + timedelta(days=1)
            ).isoformat(),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 403


# ---------------------------------------------------------
# LIST / GET
# ---------------------------------------------------------


def test_list_maintenance(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    create_maintenance(client, token, machine_id)

    response = client.get(
        "/maintenance",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


def test_get_one_maintenance(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    created = create_maintenance(
        client,
        token,
        machine_id,
    )

    maintenance_id = created["id"]

    response = client.get(
        f"/maintenance/{maintenance_id}",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["id"] == maintenance_id


def test_get_maintenance_not_found(client):
    token = register_and_login(client, "Maintenance Engineer")

    response = client.get(
        "/maintenance/999999",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "Maintenance record not found"
    )


def test_get_machine_maintenance(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    create_maintenance(client, token, machine_id)
    create_maintenance(client, token, machine_id)

    response = client.get(
        f"/maintenance/machine/{machine_id}",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 2


def test_get_machine_maintenance_machine_not_found(client):
    token = register_and_login(client, "Maintenance Engineer")

    response = client.get(
        "/maintenance/machine/999999",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Machine not found"


# ---------------------------------------------------------
# UPDATE DETAILS
# ---------------------------------------------------------


def test_update_maintenance_details(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    created = create_maintenance(
        client,
        token,
        machine_id,
    )

    maintenance_id = created["id"]

    response = client.patch(
        f"/maintenance/{maintenance_id}",
        json={
            "priority": "High",
            "description": "Updated maintenance description",
            "findings": "Minor wear found",
            "action_taken": "Parts replaced",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["priority"] == "High"
    assert data["description"] == "Updated maintenance description"
    assert data["findings"] == "Minor wear found"
    assert data["action_taken"] == "Parts replaced"


def test_update_maintenance_invalid_priority(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    created = create_maintenance(
        client,
        token,
        machine_id,
    )

    response = client.patch(
        f"/maintenance/{created['id']}",
        json={
            "priority": "Urgent",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Invalid maintenance priority"
    )


def test_update_maintenance_not_found(client):
    token = register_and_login(client, "Maintenance Engineer")

    response = client.patch(
        "/maintenance/999999",
        json={
            "priority": "High",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "Maintenance record not found"
    )


def test_worker_cannot_update_maintenance(client):
    _, _, _, machine_id = setup_machine(client)

    maintenance_token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    created = create_maintenance(
        client,
        maintenance_token,
        machine_id,
    )

    worker_token = register_and_login(
        client,
        "Worker",
    )

    response = client.patch(
        f"/maintenance/{created['id']}",
        json={
            "priority": "High",
        },
        headers=auth_headers(worker_token),
    )

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "You do not have permission to manage maintenance"
    )


# ---------------------------------------------------------
# STATUS TRANSITIONS
# ---------------------------------------------------------


def test_start_maintenance(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    created = create_maintenance(
        client,
        token,
        machine_id,
    )

    maintenance_id = created["id"]

    response = client.patch(
        f"/maintenance/{maintenance_id}/status",
        json={
            "status": "In Progress",
            "findings": "Maintenance started",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "In Progress"
    assert data["started_at"] is not None
    assert data["findings"] == "Maintenance started"


def test_start_maintenance_updates_machine_status(client, db):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    created = create_maintenance(
        client,
        token,
        machine_id,
    )

    response = client.patch(
        f"/maintenance/{created['id']}/status",
        json={
            "status": "In Progress",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    db.expire_all()

    machine = db.query(Machine).filter(
        Machine.id == machine_id
    ).first()

    assert machine is not None
    assert machine.status == "Under Maintenance"


def test_complete_maintenance(client, db):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    created = create_maintenance(
        client,
        token,
        machine_id,
    )

    maintenance_id = created["id"]

    start_response = client.patch(
        f"/maintenance/{maintenance_id}/status",
        json={
            "status": "In Progress",
        },
        headers=auth_headers(token),
    )

    assert start_response.status_code == 200

    response = client.patch(
        f"/maintenance/{maintenance_id}/status",
        json={
            "status": "Completed",
            "findings": "Maintenance completed successfully",
            "action_taken": "Replaced worn component",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "Completed"
    assert data["completed_at"] is not None
    assert data["findings"] == "Maintenance completed successfully"
    assert data["action_taken"] == "Replaced worn component"

    db.expire_all()

    machine = db.query(Machine).filter(
        Machine.id == machine_id
    ).first()

    assert machine is not None
    assert machine.status == "Available"


def test_cannot_complete_scheduled_maintenance(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    created = create_maintenance(
        client,
        token,
        machine_id,
    )

    response = client.patch(
        f"/maintenance/{created['id']}/status",
        json={
            "status": "Completed",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Only in-progress maintenance can be completed"
    )


def test_cannot_start_completed_maintenance(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    created = create_maintenance(
        client,
        token,
        machine_id,
    )

    maintenance_id = created["id"]

    response = client.patch(
        f"/maintenance/{maintenance_id}/status",
        json={
            "status": "In Progress",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    response = client.patch(
        f"/maintenance/{maintenance_id}/status",
        json={
            "status": "Completed",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    response = client.patch(
        f"/maintenance/{maintenance_id}/status",
        json={
            "status": "In Progress",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Only scheduled maintenance can be started"
    )


def test_cancel_scheduled_maintenance(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    created = create_maintenance(
        client,
        token,
        machine_id,
    )

    response = client.patch(
        f"/maintenance/{created['id']}/status",
        json={
            "status": "Cancelled",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Cancelled"


def test_cancel_in_progress_maintenance(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    created = create_maintenance(
        client,
        token,
        machine_id,
    )

    maintenance_id = created["id"]

    response = client.patch(
        f"/maintenance/{maintenance_id}/status",
        json={
            "status": "In Progress",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    response = client.patch(
        f"/maintenance/{maintenance_id}/status",
        json={
            "status": "Cancelled",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Cancelled"


def test_completed_maintenance_cannot_be_cancelled(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    created = create_maintenance(
        client,
        token,
        machine_id,
    )

    maintenance_id = created["id"]

    response = client.patch(
        f"/maintenance/{maintenance_id}/status",
        json={
            "status": "In Progress",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    response = client.patch(
        f"/maintenance/{maintenance_id}/status",
        json={
            "status": "Completed",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    response = client.patch(
        f"/maintenance/{maintenance_id}/status",
        json={
            "status": "Cancelled",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Completed maintenance cannot be cancelled"
    )


def test_invalid_maintenance_status_rejected(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    created = create_maintenance(
        client,
        token,
        machine_id,
    )

    response = client.patch(
        f"/maintenance/{created['id']}/status",
        json={
            "status": "Random",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Invalid maintenance status"
    )


def test_status_update_not_found(client):
    token = register_and_login(client, "Maintenance Engineer")

    response = client.patch(
        "/maintenance/999999/status",
        json={
            "status": "In Progress",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "Maintenance record not found"
    )


def test_worker_cannot_update_maintenance_status(client):
    _, _, _, machine_id = setup_machine(client)

    maintenance_token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    created = create_maintenance(
        client,
        maintenance_token,
        machine_id,
    )

    worker_token = register_and_login(
        client,
        "Worker",
    )

    response = client.patch(
        f"/maintenance/{created['id']}/status",
        json={
            "status": "In Progress",
        },
        headers=auth_headers(worker_token),
    )

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "You do not have permission to manage maintenance"
    )


# ---------------------------------------------------------
# COMPLETED RECORD PROTECTION
# ---------------------------------------------------------


def test_completed_maintenance_cannot_be_modified(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(client, "Maintenance Engineer")

    created = create_maintenance(
        client,
        token,
        machine_id,
    )

    maintenance_id = created["id"]

    response = client.patch(
        f"/maintenance/{maintenance_id}/status",
        json={
            "status": "In Progress",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    response = client.patch(
        f"/maintenance/{maintenance_id}/status",
        json={
            "status": "Completed",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    response = client.patch(
        f"/maintenance/{maintenance_id}",
        json={
            "priority": "Critical",
            "description": "Trying to modify completed record",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Completed maintenance cannot be modified"
    )