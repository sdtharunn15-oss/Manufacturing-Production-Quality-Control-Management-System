from uuid import uuid4

from app.models.notification import Notification


def unique(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def register_and_login(client, role="Plant Manager"):
    email = f"{unique('defect-user')}@example.com"
    password = "Test@12345"

    register = client.post(
        "/auth/register",
        json={
            "full_name": unique("Defect User"),
            "email": email,
            "password": password,
            "role": role,
        },
    )

    assert register.status_code == 201, register.text

    login = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert login.status_code == 200, login.text

    return login.json()["access_token"]


def auth_headers(token):
    return {
        "Authorization": f"Bearer {token}"
    }


def setup_failed_inspection(client):
    # Plant Manager handles production setup.
    plant_token = register_and_login(
        client,
        "Plant Manager",
    )

    headers = auth_headers(plant_token)

    # Create Plant
    plant = client.post(
        "/plants",
        headers=headers,
        json={
            "name": unique("Defect Plant"),
            "code": unique("DP"),
            "location": "Chennai",
            "description": "Plant for defect tests",
        },
    )

    assert plant.status_code == 201, plant.text
    plant_id = plant.json()["id"]

    # Create Production Line
    line = client.post(
        "/production-lines",
        headers=headers,
        json={
            "name": unique("Defect Line"),
            "code": unique("DL"),
            "plant_id": plant_id,
            "description": "Production line for defect tests",
        },
    )

    assert line.status_code == 201, line.text
    line_id = line.json()["id"]

    # Create Product
    product = client.post(
        "/products",
        headers=headers,
        json={
            "name": unique("Defect Product"),
            "code": unique("DPROD"),
            "product_type": "Finished Goods",
            "unit": "pcs",
            "production_line_id": line_id,
            "description": "Product for defect tests",
        },
    )

    assert product.status_code == 201, product.text
    product_id = product.json()["id"]

    # Create Production Order
    order = client.post(
        "/production-orders",
        headers=headers,
        json={
            "order_number": unique("DORDER"),
            "product_id": product_id,
            "production_line_id": line_id,
            "quantity": 100,
            "priority": "Normal",
            "notes": "Defect test order",
        },
    )

    assert order.status_code == 201, order.text
    order_id = order.json()["id"]

    # Valid order workflow
    for status in ["Planned", "Released", "In Progress"]:
        response = client.patch(
            f"/production-orders/{order_id}/status",
            headers=headers,
            json={
                "status": status
            },
        )

        assert response.status_code == 200, response.text

    # Create Production Batch
    batch = client.post(
        "/production-batches",
        headers=headers,
        json={
            "batch_number": unique("DBATCH"),
            "production_order_id": order_id,
            "planned_quantity": 100,
            "notes": "Defect test batch",
        },
    )

    assert batch.status_code == 201, batch.text
    batch_id = batch.json()["id"]

    # Start batch
    start = client.post(
        f"/production-batches/{batch_id}/start",
        headers=headers,
    )

    assert start.status_code == 200, start.text

    # Record output
    output = client.patch(
        f"/production-batches/{batch_id}/output",
        headers=headers,
        json={
            "produced_quantity": 95,
            "rejected_quantity": 5,
            "rejection_reason": "Production rejects",
        },
    )

    assert output.status_code == 200, output.text

    # Quality Manager creates failed inspection.
    quality_token = register_and_login(
        client,
        "Quality Manager",
    )

    inspection = client.post(
        "/quality-inspections",
        headers=auth_headers(quality_token),
        json={
            "inspection_number": unique("DINS"),
            "batch_id": batch_id,
            "inspected_quantity": 95,
            "passed_quantity": 90,
            "failed_quantity": 5,
            "remarks": "Failed quality inspection",
        },
    )

    assert inspection.status_code == 201, inspection.text

    return quality_token, batch_id, inspection.json()["id"]


def create_defect(
    client,
    token,
    batch_id,
    inspection_id,
    **overrides,
):
    payload = {
        "defect_number": unique("DEFECT"),
        "batch_id": batch_id,
        "inspection_id": inspection_id,
        "defect_type": "Surface Damage",
        "severity": "High",
        "quantity": 5,
        "description": "Surface damage found during inspection",
    }

    payload.update(overrides)

    return client.post(
        "/defects",
        headers=auth_headers(token),
        json=payload,
    )


def test_create_defect(client):
    token, batch_id, inspection_id = setup_failed_inspection(client)

    response = create_defect(
        client,
        token,
        batch_id,
        inspection_id,
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["batch_id"] == batch_id
    assert data["inspection_id"] == inspection_id
    assert data["defect_type"] == "Surface Damage"
    assert data["severity"] == "High"
    assert data["quantity"] == 5
    assert data["status"] == "Open"
    assert data["reported_by"] > 0


def test_list_defects(client):
    token, batch_id, inspection_id = setup_failed_inspection(client)

    create = create_defect(
        client,
        token,
        batch_id,
        inspection_id,
    )

    assert create.status_code == 201, create.text

    response = client.get(
        "/defects",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text

    assert any(
        item["id"] == create.json()["id"]
        for item in response.json()
    )


def test_get_defect(client):
    token, batch_id, inspection_id = setup_failed_inspection(client)

    create = create_defect(
        client,
        token,
        batch_id,
        inspection_id,
    )

    assert create.status_code == 201, create.text

    defect_id = create.json()["id"]

    response = client.get(
        f"/defects/{defect_id}",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == defect_id


def test_get_batch_defects(client):
    token, batch_id, inspection_id = setup_failed_inspection(client)

    create = create_defect(
        client,
        token,
        batch_id,
        inspection_id,
    )

    assert create.status_code == 201, create.text

    response = client.get(
        f"/defects/batch/{batch_id}",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert any(
        item["id"] == create.json()["id"]
        for item in data
    )

    assert all(
        item["batch_id"] == batch_id
        for item in data
    )


def test_worker_cannot_create_defect(client):
    _, batch_id, inspection_id = setup_failed_inspection(client)

    worker_token = register_and_login(
        client,
        "Worker",
    )

    response = create_defect(
        client,
        worker_token,
        batch_id,
        inspection_id,
    )

    assert response.status_code == 403

    assert response.json()["detail"] == (
        "You do not have permission to manage defects"
    )


def test_duplicate_defect_number_rejected(client):
    token, batch_id, inspection_id = setup_failed_inspection(client)

    defect_number = unique("DUP")

    first = create_defect(
        client,
        token,
        batch_id,
        inspection_id,
        defect_number=defect_number,
    )

    assert first.status_code == 201, first.text

    second = create_defect(
        client,
        token,
        batch_id,
        inspection_id,
        defect_number=defect_number,
    )

    assert second.status_code == 409

    assert second.json()["detail"] == (
        "Defect number already exists"
    )


def test_invalid_severity_rejected(client):
    token, batch_id, inspection_id = setup_failed_inspection(client)

    response = create_defect(
        client,
        token,
        batch_id,
        inspection_id,
        severity="Invalid",
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Invalid defect severity"
    )


def test_nonexistent_batch_rejected(client):
    token = register_and_login(
        client,
        "Quality Manager",
    )

    response = create_defect(
        client,
        token,
        999999,
        999999,
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Production batch not found"
    )


def test_nonexistent_inspection_rejected(client):
    token, batch_id, _ = setup_failed_inspection(client)

    response = create_defect(
        client,
        token,
        batch_id,
        999999,
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Quality inspection not found"
    )


def test_inspection_from_different_batch_rejected(client):
    token, batch_id, inspection_id = setup_failed_inspection(client)

    _, other_batch_id, _ = setup_failed_inspection(client)

    response = create_defect(
        client,
        token,
        other_batch_id,
        inspection_id,
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Inspection does not belong to the specified batch"
    )


def test_defect_quantity_cannot_exceed_failed_quantity(client):
    token, batch_id, inspection_id = setup_failed_inspection(client)

    response = create_defect(
        client,
        token,
        batch_id,
        inspection_id,
        quantity=6,
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Defect quantity cannot exceed failed inspection quantity"
    )


def test_critical_defect_creates_notifications(client, db):
    token, batch_id, inspection_id = setup_failed_inspection(client)

    response = create_defect(
        client,
        token,
        batch_id,
        inspection_id,
        severity="Critical",
    )

    assert response.status_code == 201, response.text

    defect_id = response.json()["id"]

    notifications = (
        db.query(Notification)
        .filter(
            Notification.related_entity_type == "Defect",
            Notification.related_entity_id == defect_id,
            Notification.notification_type == "CRITICAL_DEFECT",
        )
        .all()
    )

    assert len(notifications) >= 1

    assert all(
        notification.priority == "Critical"
        for notification in notifications
    )

    assert all(
        notification.title == "Critical Defect Detected"
        for notification in notifications
    )


def test_update_defect(client):
    token, batch_id, inspection_id = setup_failed_inspection(client)

    create = create_defect(
        client,
        token,
        batch_id,
        inspection_id,
    )

    assert create.status_code == 201, create.text

    defect_id = create.json()["id"]

    response = client.patch(
        f"/defects/{defect_id}",
        headers=auth_headers(token),
        json={
            "severity": "Critical",
            "status": "Under Review",
            "description": "Updated defect description",
            "corrective_action": "Replace damaged component",
        },
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["severity"] == "Critical"
    assert data["status"] == "Under Review"
    assert data["description"] == "Updated defect description"
    assert data["corrective_action"] == "Replace damaged component"


def test_update_invalid_severity_rejected(client):
    token, batch_id, inspection_id = setup_failed_inspection(client)

    create = create_defect(
        client,
        token,
        batch_id,
        inspection_id,
    )

    assert create.status_code == 201, create.text

    defect_id = create.json()["id"]

    response = client.patch(
        f"/defects/{defect_id}",
        headers=auth_headers(token),
        json={
            "severity": "Invalid",
        },
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Invalid defect severity"
    )


def test_update_invalid_status_rejected(client):
    token, batch_id, inspection_id = setup_failed_inspection(client)

    create = create_defect(
        client,
        token,
        batch_id,
        inspection_id,
    )

    assert create.status_code == 201, create.text

    defect_id = create.json()["id"]

    response = client.patch(
        f"/defects/{defect_id}",
        headers=auth_headers(token),
        json={
            "status": "Invalid",
        },
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Invalid defect status"
    )


def test_worker_cannot_update_defect(client):
    token, batch_id, inspection_id = setup_failed_inspection(client)

    create = create_defect(
        client,
        token,
        batch_id,
        inspection_id,
    )

    assert create.status_code == 201, create.text

    defect_id = create.json()["id"]

    worker_token = register_and_login(
        client,
        "Worker",
    )

    response = client.patch(
        f"/defects/{defect_id}",
        headers=auth_headers(worker_token),
        json={
            "status": "Resolved",
        },
    )

    assert response.status_code == 403

    assert response.json()["detail"] == (
        "You do not have permission to manage defects"
    )


def test_update_missing_defect(client):
    token = register_and_login(
        client,
        "Quality Manager",
    )

    response = client.patch(
        "/defects/999999",
        headers=auth_headers(token),
        json={
            "status": "Resolved",
        },
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Defect not found"
    )


def test_get_missing_defect(client):
    token = register_and_login(
        client,
        "Quality Manager",
    )

    response = client.get(
        "/defects/999999",
        headers=auth_headers(token),
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Defect not found"
    )


def test_get_batch_defects_for_missing_batch(client):
    token = register_and_login(
        client,
        "Quality Manager",
    )

    response = client.get(
        "/defects/batch/999999",
        headers=auth_headers(token),
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Production batch not found"
    )