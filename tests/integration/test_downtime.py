from datetime import datetime, timedelta
from uuid import uuid4

from app.models.machine import Machine


def unique(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def register_and_login(client, role: str):
    email = (
        f"{role.lower().replace(' ', '_').replace('-', '_')}_"
        f"{uuid4().hex[:8]}@example.com"
    )

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
            "name": unique("Downtime Plant"),
            "code": unique("DPL"),
            "location": "Chennai",
            "description": "Downtime test plant",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_production_line(client, token: str, plant_id: int):
    response = client.post(
        "/production-lines",
        json={
            "name": unique("Downtime Line"),
            "code": unique("DLN"),
            "plant_id": plant_id,
            "description": "Downtime test line",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_machine(client, token: str, plant_id: int, line_id: int):
    response = client.post(
        "/machines",
        json={
            "name": unique("Downtime Machine"),
            "code": unique("DMC"),
            "machine_type": "CNC",
            "plant_id": plant_id,
            "production_line_id": line_id,
            "status": "Available",
            "description": "Downtime test machine",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text
    return response.json()["id"]


def setup_machine(client):
    plant_manager_token = register_and_login(
        client,
        "Plant Manager",
    )

    plant_id = create_plant(
        client,
        plant_manager_token,
    )

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


def create_downtime(
    client,
    token: str,
    machine_id: int,
    category: str = "Machine Failure",
    severity: str = "Medium",
):
    started_at = datetime.utcnow()

    response = client.post(
        "/downtime",
        json={
            "downtime_number": unique("DT"),
            "machine_id": machine_id,
            "reason": "Unexpected machine stoppage",
            "category": category,
            "severity": severity,
            "started_at": started_at.isoformat(),
            "notes": "Downtime test record",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------
# CREATE
# ---------------------------------------------------------


def test_create_downtime_success(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    data = create_downtime(
        client,
        token,
        machine_id,
    )

    assert data["machine_id"] == machine_id
    assert data["category"] == "Machine Failure"
    assert data["severity"] == "Medium"
    assert data["status"] == "Open"
    assert data["reported_by"] is not None
    assert data["ended_at"] is None
    assert data["duration_minutes"] is None


def test_create_downtime_with_production_order(client):
    """
    The service accepts an optional production_order_id.
    We create a valid order through the existing API and attach it
    to the downtime record.
    """

    plant_manager_token, plant_id, line_id, machine_id = setup_machine(
        client
    )

    production_manager_token = register_and_login(
        client,
        "Production Manager",
    )

    product_response = client.post(
        "/products",
        json={
            "name": unique("Downtime Product"),
            "code": unique("DP"),
            "product_type": "Finished Product",
            "unit": "pcs",
            "production_line_id": line_id,
            "description": "Downtime test product",
        },
        headers=auth_headers(plant_manager_token),
    )

    assert product_response.status_code == 201, product_response.text
    product_id = product_response.json()["id"]

    order_response = client.post(
        "/production-orders",
        json={
            "order_number": unique("PO"),
            "product_id": product_id,
            "production_line_id": line_id,
            "quantity": 100,
            "priority": "Normal",
            "notes": "Downtime test order",
        },
        headers=auth_headers(production_manager_token),
    )

    assert order_response.status_code == 201, order_response.text
    order_id = order_response.json()["id"]

    response = client.post(
        "/downtime",
        json={
            "downtime_number": unique("DTORDER"),
            "machine_id": machine_id,
            "production_order_id": order_id,
            "reason": "Machine stopped during production",
            "category": "Machine Failure",
            "severity": "High",
            "started_at": datetime.utcnow().isoformat(),
        },
        headers=auth_headers(production_manager_token),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["production_order_id"] == order_id
    assert data["severity"] == "High"


def test_create_downtime_invalid_category(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    response = client.post(
        "/downtime",
        json={
            "downtime_number": unique("INVALIDCAT"),
            "machine_id": machine_id,
            "reason": "Machine problem",
            "category": "Invalid Category",
            "severity": "Medium",
            "started_at": datetime.utcnow().isoformat(),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Invalid downtime category"
    )


def test_create_downtime_invalid_severity(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    response = client.post(
        "/downtime",
        json={
            "downtime_number": unique("INVALIDSEV"),
            "machine_id": machine_id,
            "reason": "Machine problem",
            "category": "Machine Failure",
            "severity": "Urgent",
            "started_at": datetime.utcnow().isoformat(),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Invalid downtime severity"
    )


def test_create_downtime_duplicate_number(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    downtime_number = unique("DUPLICATE")

    payload = {
        "downtime_number": downtime_number,
        "machine_id": machine_id,
        "reason": "Machine stopped",
        "category": "Machine Failure",
        "severity": "Medium",
        "started_at": datetime.utcnow().isoformat(),
    }

    first = client.post(
        "/downtime",
        json=payload,
        headers=auth_headers(token),
    )

    assert first.status_code == 201, first.text

    second = client.post(
        "/downtime",
        json=payload,
        headers=auth_headers(token),
    )

    assert second.status_code == 409
    assert (
        second.json()["detail"]
        == "Downtime number already exists"
    )


def test_create_downtime_machine_not_found(client):
    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    response = client.post(
        "/downtime",
        json={
            "downtime_number": unique("NOMACHINE"),
            "machine_id": 999999,
            "reason": "Machine problem",
            "category": "Machine Failure",
            "severity": "Medium",
            "started_at": datetime.utcnow().isoformat(),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Machine not found"


def test_create_downtime_production_order_not_found(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    response = client.post(
        "/downtime",
        json={
            "downtime_number": unique("NOORDER"),
            "machine_id": machine_id,
            "production_order_id": 999999,
            "reason": "Machine problem",
            "category": "Machine Failure",
            "severity": "Medium",
            "started_at": datetime.utcnow().isoformat(),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "Production order not found"
    )


# ---------------------------------------------------------
# ROLE PROTECTION
# ---------------------------------------------------------


def test_worker_cannot_create_downtime(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Worker",
    )

    response = client.post(
        "/downtime",
        json={
            "downtime_number": unique("WORKER"),
            "machine_id": machine_id,
            "reason": "Machine problem",
            "category": "Machine Failure",
            "severity": "Medium",
            "started_at": datetime.utcnow().isoformat(),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "You do not have permission to manage downtime"
    )


def test_quality_manager_cannot_create_downtime(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Quality Manager",
    )

    response = client.post(
        "/downtime",
        json={
            "downtime_number": unique("QUALITY"),
            "machine_id": machine_id,
            "reason": "Machine problem",
            "category": "Machine Failure",
            "severity": "Medium",
            "started_at": datetime.utcnow().isoformat(),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 403


# ---------------------------------------------------------
# LIST / GET
# ---------------------------------------------------------


def test_list_downtime(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    create_downtime(
        client,
        token,
        machine_id,
    )

    response = client.get(
        "/downtime",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


def test_get_one_downtime(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    created = create_downtime(
        client,
        token,
        machine_id,
    )

    response = client.get(
        f"/downtime/{created['id']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_downtime_not_found(client):
    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    response = client.get(
        "/downtime/999999",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "Downtime record not found"
    )


def test_get_machine_downtime(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    create_downtime(
        client,
        token,
        machine_id,
    )

    create_downtime(
        client,
        token,
        machine_id,
    )

    response = client.get(
        f"/downtime/machine/{machine_id}",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 2


def test_get_machine_downtime_machine_not_found(client):
    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    response = client.get(
        "/downtime/machine/999999",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Machine not found"


# ---------------------------------------------------------
# UPDATE
# ---------------------------------------------------------


def test_update_downtime(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    created = create_downtime(
        client,
        token,
        machine_id,
    )

    response = client.patch(
        f"/downtime/{created['id']}",
        json={
            "reason": "Updated machine failure",
            "category": "Maintenance",
            "severity": "High",
            "notes": "Updated notes",
            "resolution": "Technician assigned",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["reason"] == "Updated machine failure"
    assert data["category"] == "Maintenance"
    assert data["severity"] == "High"
    assert data["notes"] == "Updated notes"
    assert data["resolution"] == "Technician assigned"


def test_update_downtime_invalid_category(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    created = create_downtime(
        client,
        token,
        machine_id,
    )

    response = client.patch(
        f"/downtime/{created['id']}",
        json={
            "category": "Invalid Category",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Invalid downtime category"
    )


def test_update_downtime_invalid_severity(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    created = create_downtime(
        client,
        token,
        machine_id,
    )

    response = client.patch(
        f"/downtime/{created['id']}",
        json={
            "severity": "Urgent",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Invalid downtime severity"
    )


def test_update_downtime_not_found(client):
    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    response = client.patch(
        "/downtime/999999",
        json={
            "reason": "Updated reason",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "Downtime record not found"
    )


def test_worker_cannot_update_downtime(client):
    _, _, _, machine_id = setup_machine(client)

    maintenance_token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    created = create_downtime(
        client,
        maintenance_token,
        machine_id,
    )

    worker_token = register_and_login(
        client,
        "Worker",
    )

    response = client.patch(
        f"/downtime/{created['id']}",
        json={
            "reason": "Worker update",
        },
        headers=auth_headers(worker_token),
    )

    assert response.status_code == 403


# ---------------------------------------------------------
# CLOSE DOWNTIME
# ---------------------------------------------------------


def test_close_downtime_success(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    started_at = datetime.utcnow()

    response = client.post(
        "/downtime",
        json={
            "downtime_number": unique("CLOSE"),
            "machine_id": machine_id,
            "reason": "Machine stopped",
            "category": "Machine Failure",
            "severity": "High",
            "started_at": started_at.isoformat(),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text

    created = response.json()

    ended_at = started_at + timedelta(minutes=90)

    response = client.patch(
        f"/downtime/{created['id']}/close",
        json={
            "ended_at": ended_at.isoformat(),
            "resolution": "Machine repaired",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "Closed"
    assert data["ended_at"] is not None
    assert data["duration_minutes"] == 90
    assert data["resolution"] == "Machine repaired"


def test_close_downtime_calculates_duration(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    started_at = datetime.utcnow()

    response = client.post(
        "/downtime",
        json={
            "downtime_number": unique("DURATION"),
            "machine_id": machine_id,
            "reason": "Power failure",
            "category": "Power Failure",
            "severity": "Critical",
            "started_at": started_at.isoformat(),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text

    created = response.json()

    ended_at = started_at + timedelta(
        hours=2,
        minutes=30,
    )

    response = client.patch(
        f"/downtime/{created['id']}/close",
        json={
            "ended_at": ended_at.isoformat(),
            "resolution": "Power restored",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["duration_minutes"] == 150


def test_close_downtime_end_before_start_rejected(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    started_at = datetime.utcnow()

    response = client.post(
        "/downtime",
        json={
            "downtime_number": unique("BADTIME"),
            "machine_id": machine_id,
            "reason": "Machine failure",
            "category": "Machine Failure",
            "severity": "Medium",
            "started_at": started_at.isoformat(),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text

    created = response.json()

    ended_at = started_at - timedelta(minutes=10)

    response = client.patch(
        f"/downtime/{created['id']}/close",
        json={
            "ended_at": ended_at.isoformat(),
            "resolution": "Invalid close attempt",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "End time must be after start time"
    )


def test_close_downtime_not_found(client):
    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    response = client.patch(
        "/downtime/999999/close",
        json={
            "ended_at": (
                datetime.utcnow() + timedelta(hours=1)
            ).isoformat(),
            "resolution": "Resolved",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "Downtime record not found"
    )


def test_close_downtime_twice_rejected(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    started_at = datetime.utcnow()

    response = client.post(
        "/downtime",
        json={
            "downtime_number": unique("TWICE"),
            "machine_id": machine_id,
            "reason": "Machine stopped",
            "category": "Machine Failure",
            "severity": "Medium",
            "started_at": started_at.isoformat(),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text

    created = response.json()

    ended_at = started_at + timedelta(minutes=30)

    response = client.patch(
        f"/downtime/{created['id']}/close",
        json={
            "ended_at": ended_at.isoformat(),
            "resolution": "First resolution",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    response = client.patch(
        f"/downtime/{created['id']}/close",
        json={
            "ended_at": (
                ended_at + timedelta(minutes=10)
            ).isoformat(),
            "resolution": "Second resolution",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Downtime is already closed"
    )


def test_worker_cannot_close_downtime(client):
    _, _, _, machine_id = setup_machine(client)

    maintenance_token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    created = create_downtime(
        client,
        maintenance_token,
        machine_id,
    )

    worker_token = register_and_login(
        client,
        "Worker",
    )

    response = client.patch(
        f"/downtime/{created['id']}/close",
        json={
            "ended_at": (
                datetime.utcnow() + timedelta(hours=1)
            ).isoformat(),
            "resolution": "Worker close",
        },
        headers=auth_headers(worker_token),
    )

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "You do not have permission to manage downtime"
    )


# ---------------------------------------------------------
# CLOSED RECORD PROTECTION
# ---------------------------------------------------------


def test_closed_downtime_cannot_be_modified(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    started_at = datetime.utcnow()

    response = client.post(
        "/downtime",
        json={
            "downtime_number": unique("CLOSEDUPDATE"),
            "machine_id": machine_id,
            "reason": "Machine failure",
            "category": "Machine Failure",
            "severity": "Medium",
            "started_at": started_at.isoformat(),
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text

    created = response.json()

    response = client.patch(
        f"/downtime/{created['id']}/close",
        json={
            "ended_at": (
                started_at + timedelta(minutes=45)
            ).isoformat(),
            "resolution": "Machine repaired",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    response = client.patch(
        f"/downtime/{created['id']}",
        json={
            "reason": "Trying to modify closed downtime",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Closed downtime cannot be modified"
    )


# ---------------------------------------------------------
# ALL ALLOWED CATEGORIES
# ---------------------------------------------------------


def test_all_allowed_downtime_categories(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    categories = [
        "Machine Failure",
        "Maintenance",
        "Power Failure",
        "Material Shortage",
        "Operator Issue",
        "Quality Issue",
        "Other",
    ]

    for category in categories:
        data = create_downtime(
            client,
            token,
            machine_id,
            category=category,
        )

        assert data["category"] == category


def test_all_allowed_downtime_severities(client):
    _, _, _, machine_id = setup_machine(client)

    token = register_and_login(
        client,
        "Maintenance Engineer",
    )

    severities = [
        "Low",
        "Medium",
        "High",
        "Critical",
    ]

    for severity in severities:
        data = create_downtime(
            client,
            token,
            machine_id,
            severity=severity,
        )

        assert data["severity"] == severity