import uuid


def unique_code(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def register_and_login(client, role, email=None, full_name=None):
    email = email or f"{uuid.uuid4().hex[:8]}@example.com"
    full_name = full_name or f"Test {role}"

    register_response = client.post(
        "/auth/register",
        json={
            "full_name": full_name,
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
            "name": f"Worker Plant {uuid.uuid4().hex[:8]}",
            "code": unique_code("WP"),
            "location": "Chennai",
            "description": "Worker test plant",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_production_line(client, token, plant_id):
    response = client.post(
        "/production-lines",
        json={
            "name": f"Worker Line {uuid.uuid4().hex[:8]}",
            "code": unique_code("WL"),
            "plant_id": plant_id,
            "description": "Worker test production line",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_product(client, token, production_line_id):
    response = client.post(
        "/products",
        json={
            "name": f"Worker Product {uuid.uuid4().hex[:8]}",
            "code": unique_code("WPR"),
            "product_type": "Finished Product",
            "unit": "pcs",
            "production_line_id": production_line_id,
            "description": "Worker test product",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_production_order(
    client,
    token,
    product_id,
    production_line_id,
):
    order_number = unique_code("WO")

    response = client.post(
        "/production-orders",
        json={
            "order_number": order_number,
            "product_id": product_id,
            "production_line_id": production_line_id,
            "quantity": 100,
            "priority": "Normal",
            "notes": "Worker assignment test order",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201

    order_id = response.json()["id"]

    for next_status in ["Planned", "Released", "In Progress"]:
        status_response = client.patch(
            f"/production-orders/{order_id}/status",
            json={
                "status": next_status,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert status_response.status_code == 200

    return order_id


def create_batch(client, token, order_id):
    response = client.post(
        "/production-batches",
        json={
            "batch_number": unique_code("WB"),
            "production_order_id": order_id,
            "planned_quantity": 50,
            "notes": "Worker assignment test batch",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_worker(client, token, plant_id):
    response = client.post(
        "/workers",
        json={
            "employee_code": unique_code("EMP"),
            "full_name": "Arun Worker",
            "phone": "9876543210",
            "department": "Production",
            "designation": "Machine Operator",
            "plant_id": plant_id,
            "notes": "Worker test employee",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    return response.json()


def test_create_worker(client):
    token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, token)

    worker = create_worker(client, token, plant_id)

    assert worker["employee_code"].startswith("EMP-")
    assert worker["full_name"] == "Arun Worker"
    assert worker["department"] == "Production"
    assert worker["designation"] == "Machine Operator"
    assert worker["plant_id"] == plant_id
    assert worker["is_active"] is True


def test_duplicate_employee_code(client):
    token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, token)

    employee_code = unique_code("DUP")

    payload = {
        "employee_code": employee_code,
        "full_name": "Duplicate Worker",
        "phone": "9876543210",
        "department": "Production",
        "designation": "Operator",
        "plant_id": plant_id,
    }

    first = client.post(
        "/workers",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    second = client.post(
        "/workers",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Employee code already exists"


def test_create_worker_requires_management_role(client):
    token = register_and_login(client, "Worker")

    response = client.post(
        "/workers",
        json={
            "employee_code": unique_code("DENY"),
            "full_name": "Unauthorized Worker",
            "department": "Production",
            "designation": "Operator",
            "plant_id": 1,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_list_workers(client):
    token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, token)

    create_worker(client, token, plant_id)

    response = client.get(
        "/workers",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


def test_list_workers_by_plant(client):
    token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, token)

    worker = create_worker(client, token, plant_id)

    response = client.get(
        f"/workers/plant/{plant_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    workers = response.json()

    assert any(item["id"] == worker["id"] for item in workers)


def test_get_worker(client):
    token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, token)

    worker = create_worker(client, token, plant_id)

    response = client.get(
        f"/workers/{worker['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == worker["id"]


def test_get_nonexistent_worker(client):
    token = register_and_login(client, "Plant Manager")

    response = client.get(
        "/workers/999999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_update_worker(client):
    token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, token)

    worker = create_worker(client, token, plant_id)

    response = client.patch(
        f"/workers/{worker['id']}",
        json={
            "full_name": "Updated Worker Name",
            "department": "Quality",
            "designation": "Quality Operator",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    updated = response.json()

    assert updated["full_name"] == "Updated Worker Name"
    assert updated["department"] == "Quality"
    assert updated["designation"] == "Quality Operator"


def test_update_worker_requires_management_role(client):
    manager_token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, manager_token)
    worker = create_worker(client, manager_token, plant_id)

    worker_token = register_and_login(client, "Worker")

    response = client.patch(
        f"/workers/{worker['id']}",
        json={
            "full_name": "Unauthorized Update",
        },
        headers={"Authorization": f"Bearer {worker_token}"},
    )

    assert response.status_code == 403


def test_deactivate_worker(client):
    token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, token)

    worker = create_worker(client, token, plant_id)

    response = client.patch(
        f"/workers/{worker['id']}/status",
        json={
            "is_active": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_activate_worker(client):
    token = register_and_login(client, "Plant Manager")
    plant_id = create_plant(client, token)

    worker = create_worker(client, token, plant_id)

    deactivate = client.patch(
        f"/workers/{worker['id']}/status",
        json={
            "is_active": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert deactivate.status_code == 200

    activate = client.patch(
        f"/workers/{worker['id']}/status",
        json={
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert activate.status_code == 200
    assert activate.json()["is_active"] is True


def test_get_worker_requires_authentication(client):
    response = client.get("/workers")

    assert response.status_code in {401, 403}


def test_assign_worker_to_batch(client):
    token = register_and_login(client, "Plant Manager")

    plant_id = create_plant(client, token)
    production_line_id = create_production_line(
        client,
        token,
        plant_id,
    )
    product_id = create_product(
        client,
        token,
        production_line_id,
    )

    order_id = create_production_order(
        client,
        token,
        product_id,
        production_line_id,
    )

    batch_id = create_batch(
        client,
        token,
        order_id,
    )

    worker = create_worker(
        client,
        token,
        plant_id,
    )

    response = client.post(
        f"/workers/{worker['id']}/assign/{batch_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201

    assignment = response.json()

    assert assignment["batch_id"] == batch_id
    assert assignment["worker_id"] == worker["id"]
    assert assignment["assigned_by"] > 0


def test_duplicate_worker_assignment(client):
    token = register_and_login(client, "Plant Manager")

    plant_id = create_plant(client, token)
    production_line_id = create_production_line(
        client,
        token,
        plant_id,
    )
    product_id = create_product(
        client,
        token,
        production_line_id,
    )

    order_id = create_production_order(
        client,
        token,
        product_id,
        production_line_id,
    )

    batch_id = create_batch(
        client,
        token,
        order_id,
    )

    worker = create_worker(
        client,
        token,
        plant_id,
    )

    first = client.post(
        f"/workers/{worker['id']}/assign/{batch_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    second = client.post(
        f"/workers/{worker['id']}/assign/{batch_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Worker is already assigned to this batch"


def test_list_batch_worker_assignments(client):
    token = register_and_login(client, "Plant Manager")

    plant_id = create_plant(client, token)
    production_line_id = create_production_line(
        client,
        token,
        plant_id,
    )
    product_id = create_product(
        client,
        token,
        production_line_id,
    )

    order_id = create_production_order(
        client,
        token,
        product_id,
        production_line_id,
    )

    batch_id = create_batch(
        client,
        token,
        order_id,
    )

    worker = create_worker(
        client,
        token,
        plant_id,
    )

    assign = client.post(
        f"/workers/{worker['id']}/assign/{batch_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert assign.status_code == 201

    response = client.get(
        f"/workers/batch/{batch_id}/assignments",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    assignments = response.json()

    assert len(assignments) >= 1
    assert any(
        item["worker_id"] == worker["id"]
        for item in assignments
    )


def test_remove_worker_assignment(client):
    token = register_and_login(client, "Plant Manager")

    plant_id = create_plant(client, token)
    production_line_id = create_production_line(
        client,
        token,
        plant_id,
    )
    product_id = create_product(
        client,
        token,
        production_line_id,
    )

    order_id = create_production_order(
        client,
        token,
        product_id,
        production_line_id,
    )

    batch_id = create_batch(
        client,
        token,
        order_id,
    )

    worker = create_worker(
        client,
        token,
        plant_id,
    )

    assign = client.post(
        f"/workers/{worker['id']}/assign/{batch_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert assign.status_code == 201

    response = client.delete(
        f"/workers/{worker['id']}/assign/{batch_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204

    assignments = client.get(
        f"/workers/batch/{batch_id}/assignments",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert assignments.status_code == 200
    assert not any(
        item["worker_id"] == worker["id"]
        for item in assignments.json()
    )


def test_assign_worker_requires_assignment_role(client):
    manager_token = register_and_login(client, "Plant Manager")

    plant_id = create_plant(client, manager_token)
    production_line_id = create_production_line(
        client,
        manager_token,
        plant_id,
    )
    product_id = create_product(
        client,
        manager_token,
        production_line_id,
    )

    order_id = create_production_order(
        client,
        manager_token,
        product_id,
        production_line_id,
    )

    batch_id = create_batch(
        client,
        manager_token,
        order_id,
    )

    worker = create_worker(
        client,
        manager_token,
        plant_id,
    )

    worker_token = register_and_login(
        client,
        "Worker",
    )

    response = client.post(
        f"/workers/{worker['id']}/assign/{batch_id}",
        headers={"Authorization": f"Bearer {worker_token}"},
    )

    assert response.status_code == 403


def test_assign_inactive_worker_rejected(client):
    token = register_and_login(client, "Plant Manager")

    plant_id = create_plant(client, token)
    production_line_id = create_production_line(
        client,
        token,
        plant_id,
    )
    product_id = create_product(
        client,
        token,
        production_line_id,
    )

    order_id = create_production_order(
        client,
        token,
        product_id,
        production_line_id,
    )

    batch_id = create_batch(
        client,
        token,
        order_id,
    )

    worker = create_worker(
        client,
        token,
        plant_id,
    )

    deactivate = client.patch(
        f"/workers/{worker['id']}/status",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert deactivate.status_code == 200

    response = client.post(
        f"/workers/{worker['id']}/assign/{batch_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive worker cannot be assigned"


def test_assign_nonexistent_worker(client):
    token = register_and_login(client, "Plant Manager")

    plant_id = create_plant(client, token)
    production_line_id = create_production_line(
        client,
        token,
        plant_id,
    )
    product_id = create_product(
        client,
        token,
        production_line_id,
    )

    order_id = create_production_order(
        client,
        token,
        product_id,
        production_line_id,
    )

    batch_id = create_batch(
        client,
        token,
        order_id,
    )

    response = client.post(
        f"/workers/999999/assign/{batch_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_assign_worker_to_completed_batch_rejected(client):
    token = register_and_login(client, "Plant Manager")

    plant_id = create_plant(client, token)
    production_line_id = create_production_line(
        client,
        token,
        plant_id,
    )
    product_id = create_product(
        client,
        token,
        production_line_id,
    )

    order_id = create_production_order(
        client,
        token,
        product_id,
        production_line_id,
    )

    batch_id = create_batch(
        client,
        token,
        order_id,
    )

    # Start the batch.
    start_response = client.post(
        f"/production-batches/{batch_id}/start",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert start_response.status_code == 200

    # Record output so the batch can be completed.
    output_response = client.patch(
        f"/production-batches/{batch_id}/output",
        json={
            "produced_quantity": 50,
            "rejected_quantity": 0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert output_response.status_code == 200

    complete_response = client.post(
        f"/production-batches/{batch_id}/complete",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert complete_response.status_code == 200

    worker = create_worker(
        client,
        token,
        plant_id,
    )

    response = client.post(
        f"/workers/{worker['id']}/assign/{batch_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Workers can only be assigned to Planned or In Progress batches"
    )


def test_assign_worker_wrong_plant_rejected(client):
    token = register_and_login(client, "Plant Manager")

    plant_one = create_plant(client, token)
    plant_two = create_plant(client, token)

    production_line_id = create_production_line(
        client,
        token,
        plant_one,
    )

    product_id = create_product(
        client,
        token,
        production_line_id,
    )

    order_id = create_production_order(
        client,
        token,
        product_id,
        production_line_id,
    )

    batch_id = create_batch(
        client,
        token,
        order_id,
    )

    worker = create_worker(
        client,
        token,
        plant_two,
    )

    response = client.post(
        f"/workers/{worker['id']}/assign/{batch_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Worker and production batch must belong to the same plant"
    )