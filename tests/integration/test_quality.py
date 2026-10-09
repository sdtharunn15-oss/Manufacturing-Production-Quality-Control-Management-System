from uuid import uuid4


def unique(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def register_and_login(client, role="Plant Manager"):
    email = f"{unique('quality-user')}@example.com"
    password = "Test@12345"

    register = client.post(
        "/auth/register",
        json={
            "full_name": unique("Quality User"),
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


def setup_in_progress_batch(client):
    # Plant Manager is used for production setup.
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
            "name": unique("Quality Plant"),
            "code": unique("QP"),
            "location": "Chennai",
            "description": "Plant for quality inspection tests",
        },
    )

    assert plant.status_code == 201, plant.text
    plant_id = plant.json()["id"]

    # Create Production Line
    line = client.post(
        "/production-lines",
        headers=headers,
        json={
            "name": unique("Quality Line"),
            "code": unique("QL"),
            "plant_id": plant_id,
            "description": "Production line for quality tests",
        },
    )

    assert line.status_code == 201, line.text
    line_id = line.json()["id"]

    # Create Product
    product = client.post(
        "/products",
        headers=headers,
        json={
            "name": unique("Quality Product"),
            "code": unique("QPROD"),
            "product_type": "Finished Goods",
            "unit": "pcs",
            "production_line_id": line_id,
            "description": "Product for quality tests",
        },
    )

    assert product.status_code == 201, product.text
    product_id = product.json()["id"]

    # Create Production Order
    order = client.post(
        "/production-orders",
        headers=headers,
        json={
            "order_number": unique("QORDER"),
            "product_id": product_id,
            "production_line_id": line_id,
            "quantity": 100,
            "priority": "Normal",
            "notes": "Quality inspection test order",
        },
    )

    assert order.status_code == 201, order.text
    order_id = order.json()["id"]

    # Move order through valid workflow
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
            "batch_number": unique("QBATCH"),
            "production_order_id": order_id,
            "planned_quantity": 100,
            "notes": "Quality inspection test batch",
        },
    )

    assert batch.status_code == 201, batch.text
    batch_id = batch.json()["id"]

    # Start Production Batch
    start = client.post(
        f"/production-batches/{batch_id}/start",
        headers=headers,
    )

    assert start.status_code == 200, start.text

    # Record Production Output
    output = client.patch(
        f"/production-batches/{batch_id}/output",
        headers=headers,
        json={
            "produced_quantity": 95,
            "rejected_quantity": 5,
            "rejection_reason": "Initial production rejects",
        },
    )

    assert output.status_code == 200, output.text

    # Quality inspection requires a Quality Manager,
    # Production Manager, or Super Admin.
    quality_token = register_and_login(
        client,
        "Quality Manager",
    )

    return quality_token, batch_id


def create_inspection(
    client,
    token,
    batch_id,
    **overrides,
):
    payload = {
        "inspection_number": unique("QINS"),
        "batch_id": batch_id,
        "inspected_quantity": 95,
        "passed_quantity": 90,
        "failed_quantity": 5,
        "remarks": "Quality inspection completed",
    }

    payload.update(overrides)

    return client.post(
        "/quality-inspections",
        headers=auth_headers(token),
        json=payload,
    )


def test_create_quality_inspection(client):
    token, batch_id = setup_in_progress_batch(client)

    response = create_inspection(
        client,
        token,
        batch_id,
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["batch_id"] == batch_id
    assert data["inspected_quantity"] == 95
    assert data["passed_quantity"] == 90
    assert data["failed_quantity"] == 5
    assert data["result"] == "FAIL"
    assert data["quality_score"] == 94.73684210526315
    assert data["inspected_by"] > 0


def test_list_quality_inspections(client):
    token, batch_id = setup_in_progress_batch(client)

    create = create_inspection(
        client,
        token,
        batch_id,
    )

    assert create.status_code == 201, create.text

    response = client.get(
        "/quality-inspections",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text

    assert any(
        item["id"] == create.json()["id"]
        for item in response.json()
    )


def test_get_quality_inspection(client):
    token, batch_id = setup_in_progress_batch(client)

    create = create_inspection(
        client,
        token,
        batch_id,
    )

    assert create.status_code == 201, create.text

    inspection_id = create.json()["id"]

    response = client.get(
        f"/quality-inspections/{inspection_id}",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == inspection_id


def test_list_quality_inspections_by_batch(client):
    token, batch_id = setup_in_progress_batch(client)

    create = create_inspection(
        client,
        token,
        batch_id,
    )

    assert create.status_code == 201, create.text

    response = client.get(
        f"/quality-inspections/batch/{batch_id}",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert all(
        item["batch_id"] == batch_id
        for item in data
    )

    assert any(
        item["id"] == create.json()["id"]
        for item in data
    )


def test_quality_inspection_requires_quality_role(client):
    _, batch_id = setup_in_progress_batch(client)

    worker_token = register_and_login(
        client,
        "Worker",
    )

    response = create_inspection(
        client,
        worker_token,
        batch_id,
    )

    assert response.status_code == 403

    assert response.json()["detail"] == (
        "You do not have permission to perform quality inspections"
    )


def test_quality_manager_can_create_inspection(client):
    _, batch_id = setup_in_progress_batch(client)

    token = register_and_login(
        client,
        "Quality Manager",
    )

    response = create_inspection(
        client,
        token,
        batch_id,
    )

    assert response.status_code == 201, response.text


def test_duplicate_inspection_number_rejected(client):
    token, batch_id = setup_in_progress_batch(client)

    inspection_number = unique("DUP-QINS")

    first = create_inspection(
        client,
        token,
        batch_id,
        inspection_number=inspection_number,
    )

    assert first.status_code == 201, first.text

    second = create_inspection(
        client,
        token,
        batch_id,
        inspection_number=inspection_number,
    )

    assert second.status_code == 409

    assert second.json()["detail"] == (
        "Inspection number already exists"
    )


def test_nonexistent_batch_rejected(client):
    token = register_and_login(
        client,
        "Quality Manager",
    )

    response = create_inspection(
        client,
        token,
        999999,
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Production batch not found"
    )


def test_inspection_requires_in_progress_batch(client):
    token = register_and_login(
        client,
        "Plant Manager",
    )

    headers = auth_headers(token)

    plant = client.post(
        "/plants",
        headers=headers,
        json={
            "name": unique("Planned Quality Plant"),
            "code": unique("PQP"),
            "location": "Chennai",
            "description": "Plant for batch status test",
        },
    )

    assert plant.status_code == 201, plant.text

    plant_id = plant.json()["id"]

    line = client.post(
        "/production-lines",
        headers=headers,
        json={
            "name": unique("Planned Quality Line"),
            "code": unique("PQL"),
            "plant_id": plant_id,
            "description": "Line for batch status test",
        },
    )

    assert line.status_code == 201, line.text

    line_id = line.json()["id"]

    product = client.post(
        "/products",
        headers=headers,
        json={
            "name": unique("Planned Quality Product"),
            "code": unique("PQPDT"),
            "product_type": "Finished Goods",
            "unit": "pcs",
            "production_line_id": line_id,
            "description": "Product for batch status test",
        },
    )

    assert product.status_code == 201, product.text

    product_id = product.json()["id"]

    order = client.post(
        "/production-orders",
        headers=headers,
        json={
            "order_number": unique("PLANNED-QORDER"),
            "product_id": product_id,
            "production_line_id": line_id,
            "quantity": 100,
            "priority": "Normal",
        },
    )

    assert order.status_code == 201, order.text

    order_id = order.json()["id"]

    for status in ["Planned", "Released", "In Progress"]:
        response = client.patch(
            f"/production-orders/{order_id}/status",
            headers=headers,
            json={
                "status": status
            },
        )

        assert response.status_code == 200, response.text

    batch = client.post(
        "/production-batches",
        headers=headers,
        json={
            "batch_number": unique("NO-OUTPUT-QBATCH"),
            "production_order_id": order_id,
            "planned_quantity": 100,
        },
    )

    assert batch.status_code == 201, batch.text

    quality_token = register_and_login(
        client,
        "Quality Manager",
    )

    response = create_inspection(
        client,
        quality_token,
        batch.json()["id"],
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Quality inspection can only be performed on an In Progress batch"
    )


def test_passed_plus_failed_cannot_exceed_inspected(client):
    token, batch_id = setup_in_progress_batch(client)

    response = create_inspection(
        client,
        token,
        batch_id,
        inspected_quantity=90,
        passed_quantity=90,
        failed_quantity=5,
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Passed quantity plus failed quantity cannot exceed inspected quantity"
    )


def test_inspected_quantity_cannot_exceed_produced(client):
    token, batch_id = setup_in_progress_batch(client)

    response = create_inspection(
        client,
        token,
        batch_id,
        inspected_quantity=96,
        passed_quantity=91,
        failed_quantity=5,
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Inspected quantity cannot exceed produced quantity"
    )


def test_passed_plus_failed_must_equal_inspected(client):
    token, batch_id = setup_in_progress_batch(client)

    response = create_inspection(
        client,
        token,
        batch_id,
        inspected_quantity=95,
        passed_quantity=89,
        failed_quantity=5,
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Passed quantity plus failed quantity must equal inspected quantity"
    )


def test_zero_failed_quantity_gives_pass_result(client):
    token, batch_id = setup_in_progress_batch(client)

    response = create_inspection(
        client,
        token,
        batch_id,
        inspected_quantity=90,
        passed_quantity=90,
        failed_quantity=0,
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["result"] == "PASS"
    assert data["quality_score"] == 100.0


def test_get_missing_quality_inspection(client):
    token = register_and_login(
        client,
        "Quality Manager",
    )

    response = client.get(
        "/quality-inspections/999999",
        headers=auth_headers(token),
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Quality inspection not found"
    )


def test_get_batch_inspections_for_missing_batch(client):
    token = register_and_login(
        client,
        "Quality Manager",
    )

    response = client.get(
        "/quality-inspections/batch/999999",
        headers=auth_headers(token),
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Production batch not found"
    )