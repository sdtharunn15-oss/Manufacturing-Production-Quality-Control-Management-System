import uuid
from datetime import datetime, timedelta


def unique(value):
    return f"{value}-{uuid.uuid4().hex[:8]}"


def get_manager_token(client):
    email = unique("batch_manager") + "@example.com"

    register = client.post(
        "/auth/register",
        json={
            "full_name": "Batch Manager",
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


def setup_product_and_order(client, token):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Create plant
    plant = client.post(
        "/plants",
        headers=headers,
        json={
            "name": unique("Batch Plant"),
            "code": unique("BP"),
            "location": "Chennai",
            "description": "Plant for production batch tests",
        },
    )

    assert plant.status_code == 201

    plant_id = plant.json()["id"]

    # Create production line
    line = client.post(
        "/production-lines",
        headers=headers,
        json={
            "name": unique("Batch Line"),
            "code": unique("BL"),
            "plant_id": plant_id,
            "description": "Production line for batch tests",
        },
    )

    assert line.status_code == 201

    line_id = line.json()["id"]

    # Create product
    product = client.post(
        "/products",
        headers=headers,
        json={
            "name": unique("Batch Product"),
            "code": unique("BPR"),
            "product_type": "Finished Product",
            "unit": "pcs",
            "production_line_id": line_id,
            "description": "Product for production batch tests",
        },
    )

    assert product.status_code == 201

    product_id = product.json()["id"]

    # Create production order
    order = client.post(
        "/production-orders",
        headers=headers,
        json={
            "order_number": unique("BATCH-PO"),
            "product_id": product_id,
            "production_line_id": line_id,
            "quantity": 100,
            "priority": "Normal",
            "planned_start_date": (
                datetime.now() + timedelta(days=1)
            ).isoformat(),
            "planned_end_date": (
                datetime.now() + timedelta(days=2)
            ).isoformat(),
            "notes": "Order for production batch tests",
        },
    )

    assert order.status_code == 201

    order_id = order.json()["id"]

    # Draft -> Planned
    response = client.patch(
        f"/production-orders/{order_id}/status",
        headers=headers,
        json={
            "status": "Planned"
        },
    )

    assert response.status_code == 200

    # Planned -> Released
    response = client.patch(
        f"/production-orders/{order_id}/status",
        headers=headers,
        json={
            "status": "Released"
        },
    )

    assert response.status_code == 200

    # Released -> In Progress
    response = client.patch(
        f"/production-orders/{order_id}/status",
        headers=headers,
        json={
            "status": "In Progress"
        },
    )

    assert response.status_code == 200

    return order_id, product_id, line_id


def create_batch(client, token, order_id, planned_quantity=100):
    response = client.post(
        "/production-batches",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "batch_number": unique("BATCH"),
            "production_order_id": order_id,
            "planned_quantity": planned_quantity,
            "notes": "Production batch integration test",
        },
    )

    assert response.status_code == 201

    return response.json()


def test_create_production_batch(client):
    token = get_manager_token(client)

    order_id, _, _ = setup_product_and_order(
        client,
        token,
    )

    batch = create_batch(
        client,
        token,
        order_id,
    )

    assert batch["production_order_id"] == order_id
    assert batch["planned_quantity"] == 100
    assert batch["produced_quantity"] == 0
    assert batch["rejected_quantity"] == 0
    assert batch["status"] == "Planned"
    assert batch["efficiency_percentage"] == 0


def test_list_production_batches(client):
    token = get_manager_token(client)

    order_id, _, _ = setup_product_and_order(
        client,
        token,
    )

    create_batch(
        client,
        token,
        order_id,
    )

    response = client.get(
        "/production-batches",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


def test_get_production_batch(client):
    token = get_manager_token(client)

    order_id, _, _ = setup_product_and_order(
        client,
        token,
    )

    batch = create_batch(
        client,
        token,
        order_id,
    )

    batch_id = batch["id"]

    response = client.get(
        f"/production-batches/{batch_id}",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == batch_id


def test_start_production_batch(client):
    token = get_manager_token(client)

    order_id, _, _ = setup_product_and_order(
        client,
        token,
    )

    batch = create_batch(
        client,
        token,
        order_id,
    )

    batch_id = batch["id"]

    response = client.post(
        f"/production-batches/{batch_id}/start",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "In Progress"
    assert response.json()["started_at"] is not None


def test_record_production_output(client):
    token = get_manager_token(client)

    order_id, _, _ = setup_product_and_order(
        client,
        token,
    )

    batch = create_batch(
        client,
        token,
        order_id,
    )

    batch_id = batch["id"]

    start_response = client.post(
        f"/production-batches/{batch_id}/start",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert start_response.status_code == 200

    response = client.patch(
        f"/production-batches/{batch_id}/output",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "produced_quantity": 90,
            "rejected_quantity": 10,
            "rejection_reason": "Minor dimensional defects",
            "notes": "Output recorded successfully",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["produced_quantity"] == 90
    assert data["rejected_quantity"] == 10
    assert data["rejection_reason"] == "Minor dimensional defects"
    assert data["efficiency_percentage"] == 90.0


def test_output_cannot_exceed_planned_quantity(client):
    token = get_manager_token(client)

    order_id, _, _ = setup_product_and_order(
        client,
        token,
    )

    batch = create_batch(
        client,
        token,
        order_id,
    )

    batch_id = batch["id"]

    start_response = client.post(
        f"/production-batches/{batch_id}/start",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert start_response.status_code == 200

    response = client.patch(
        f"/production-batches/{batch_id}/output",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "produced_quantity": 90,
            "rejected_quantity": 20,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Produced quantity plus rejected quantity "
        "cannot exceed planned quantity"
    )


def test_start_batch_requires_in_progress_order(client):
    token = get_manager_token(client)

    headers = {
        "Authorization": f"Bearer {token}"
    }

    plant = client.post(
        "/plants",
        headers=headers,
        json={
            "name": unique("Planned Batch Plant"),
            "code": unique("PBP"),
            "location": "Chennai",
            "description": "Plant for planned batch test",
        },
    )

    assert plant.status_code == 201

    plant_id = plant.json()["id"]

    line = client.post(
        "/production-lines",
        headers=headers,
        json={
            "name": unique("Planned Batch Line"),
            "code": unique("PBL"),
            "plant_id": plant_id,
            "description": "Line for planned batch test",
        },
    )

    assert line.status_code == 201

    line_id = line.json()["id"]

    product = client.post(
        "/products",
        headers=headers,
        json={
            "name": unique("Planned Batch Product"),
            "code": unique("PBP"),
            "product_type": "Finished Product",
            "unit": "pcs",
            "production_line_id": line_id,
        },
    )

    assert product.status_code == 201

    product_id = product.json()["id"]

    order = client.post(
        "/production-orders",
        headers=headers,
        json={
            "order_number": unique("PLANNED-PO"),
            "product_id": product_id,
            "production_line_id": line_id,
            "quantity": 100,
            "priority": "Normal",
        },
    )

    assert order.status_code == 201

    order_id = order.json()["id"]

    # Move only to Planned.
    response = client.patch(
        f"/production-orders/{order_id}/status",
        headers=headers,
        json={
            "status": "Planned"
        },
    )

    assert response.status_code == 200

    # Batch creation should fail because order is not In Progress.
    batch = client.post(
        "/production-batches",
        headers=headers,
        json={
            "batch_number": unique("PLANNED-BATCH"),
            "production_order_id": order_id,
            "planned_quantity": 100,
        },
    )

    assert batch.status_code == 400
    assert batch.json()["detail"] == (
        "Production order must be In Progress before creating a batch"
    )


def test_batch_quantity_cannot_exceed_order_quantity(client):
    token = get_manager_token(client)

    order_id, _, _ = setup_product_and_order(
        client,
        token,
    )

    response = client.post(
        "/production-batches",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "batch_number": unique("LARGE-BATCH"),
            "production_order_id": order_id,
            "planned_quantity": 101,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Batch planned quantity cannot exceed production order quantity"
    )


def test_duplicate_batch_number_rejected(client):
    token = get_manager_token(client)

    order_id, _, _ = setup_product_and_order(
        client,
        token,
    )

    batch_number = unique("DUPLICATE-BATCH")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    payload = {
        "batch_number": batch_number,
        "production_order_id": order_id,
        "planned_quantity": 100,
    }

    first = client.post(
        "/production-batches",
        headers=headers,
        json=payload,
    )

    second = client.post(
        "/production-batches",
        headers=headers,
        json=payload,
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_complete_batch_requires_output(client):
    token = get_manager_token(client)

    order_id, _, _ = setup_product_and_order(
        client,
        token,
    )

    batch = create_batch(
        client,
        token,
        order_id,
    )

    batch_id = batch["id"]

    start_response = client.post(
        f"/production-batches/{batch_id}/start",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert start_response.status_code == 200

    response = client.post(
        f"/production-batches/{batch_id}/complete",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Production output must be recorded before completion"
    )


def test_complete_batch_requires_rejection_reason(client):
    token = get_manager_token(client)

    order_id, _, _ = setup_product_and_order(
        client,
        token,
    )

    batch = create_batch(
        client,
        token,
        order_id,
    )

    batch_id = batch["id"]

    start_response = client.post(
        f"/production-batches/{batch_id}/start",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert start_response.status_code == 200

    output_response = client.patch(
        f"/production-batches/{batch_id}/output",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "produced_quantity": 90,
            "rejected_quantity": 10,
        },
    )

    assert output_response.status_code == 200

    response = client.post(
        f"/production-batches/{batch_id}/complete",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Rejection reason is required when rejected quantity is greater than zero"
    )


def test_complete_production_batch(client):
    token = get_manager_token(client)

    order_id, _, _ = setup_product_and_order(
        client,
        token,
    )

    batch = create_batch(
        client,
        token,
        order_id,
    )

    batch_id = batch["id"]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    start_response = client.post(
        f"/production-batches/{batch_id}/start",
        headers=headers,
    )

    assert start_response.status_code == 200

    output_response = client.patch(
        f"/production-batches/{batch_id}/output",
        headers=headers,
        json={
            "produced_quantity": 100,
            "rejected_quantity": 0,
        },
    )

    assert output_response.status_code == 200

    response = client.post(
        f"/production-batches/{batch_id}/complete",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "Completed"
    assert data["produced_quantity"] == 100
    assert data["rejected_quantity"] == 0
    assert data["efficiency_percentage"] == 100.0
    assert data["completed_at"] is not None


def test_reject_planned_batch(client):
    token = get_manager_token(client)

    order_id, _, _ = setup_product_and_order(
        client,
        token,
    )

    batch = create_batch(
        client,
        token,
        order_id,
    )

    batch_id = batch["id"]

    response = client.post(
        f"/production-batches/{batch_id}/reject",
        headers={
            "Authorization": f"Bearer {token}"
        },
        params={
            "rejection_reason": "Machine unavailable",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "Rejected"
    assert data["rejection_reason"] == "Machine unavailable"
    assert data["completed_at"] is not None


def test_reject_batch_requires_reason(client):
    token = get_manager_token(client)

    order_id, _, _ = setup_product_and_order(
        client,
        token,
    )

    batch = create_batch(
        client,
        token,
        order_id,
    )

    batch_id = batch["id"]

    response = client.post(
        f"/production-batches/{batch_id}/reject",
        headers={
            "Authorization": f"Bearer {token}"
        },
        params={
            "rejection_reason": "   ",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Rejection reason is required"


def test_invalid_batch_output_before_start_rejected(client):
    token = get_manager_token(client)

    order_id, _, _ = setup_product_and_order(
        client,
        token,
    )

    batch = create_batch(
        client,
        token,
        order_id,
    )

    batch_id = batch["id"]

    response = client.patch(
        f"/production-batches/{batch_id}/output",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "produced_quantity": 50,
            "rejected_quantity": 0,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Production output can only be recorded for In Progress batches"
    )