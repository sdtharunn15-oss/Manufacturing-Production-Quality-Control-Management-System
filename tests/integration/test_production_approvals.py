
from uuid import uuid4

from app.models.production_order import ProductionOrder


def unique(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def register_and_login(client, role: str):
    email = (
        f"{role.lower().replace(' ', '_')}_"
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


def headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def create_plant(client, token: str):
    response = client.post(
        "/plants",
        json={
            "name": unique("Approval Plant"),
            "code": unique("PLANT"),
            "location": "Chennai",
            "description": "Approval workflow test plant",
        },
        headers=headers(token),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_line(client, token: str, plant_id: int):
    response = client.post(
        "/production-lines",
        json={
            "name": unique("Approval Line"),
            "code": unique("LINE"),
            "plant_id": plant_id,
            "description": "Approval workflow test line",
        },
        headers=headers(token),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_product(client, token: str, line_id: int):
    response = client.post(
        "/products",
        json={
            "name": unique("Approval Product"),
            "code": unique("PROD"),
            "product_type": "Manufactured",
            "unit": "pcs",
            "production_line_id": line_id,
            "description": "Approval workflow test product",
        },
        headers=headers(token),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_order(client, token: str, status: str = "Draft"):
    # Use a Plant Manager for master-data creation.
    setup_token = register_and_login(client, "Plant Manager")

    plant_id = create_plant(client, setup_token)
    line_id = create_line(client, setup_token, plant_id)
    product_id = create_product(client, setup_token, line_id)

    # Keep the requested user's token for production-order creation.
    response = client.post(
        "/production-orders",
        json={
            "order_number": unique("PO"),
            "product_id": product_id,
            "production_line_id": line_id,
            "quantity": 100,
            "priority": "Normal",
            "notes": "Approval workflow test order",
        },
        headers=headers(token),
    )
    assert response.status_code == 201, response.text

    order_id = response.json()["id"]

    if status == "Planned":
        response = client.patch(
            f"/production-orders/{order_id}/status",
            json={"status": "Planned"},
            headers=headers(token),
        )
        assert response.status_code == 200, response.text

    return order_id


def submit_approval(client, token: str, order_id: int, comments=None):
    return client.post(
        "/production-approvals",
        json={
            "production_order_id": order_id,
            "comments": comments,
        },
        headers=headers(token),
    )


# ---------------------------------------------------------
# SUBMIT APPROVAL
# ---------------------------------------------------------


def test_submit_approval_success(client):
    token = register_and_login(client, "Production Manager")
    order_id = create_order(client, token)

    response = submit_approval(
        client,
        token,
        order_id,
        "Please approve this production order",
    )

    assert response.status_code == 201, response.text

    data = response.json()
    assert data["production_order_id"] == order_id
    assert data["status"] == "Pending"
    assert data["comments"] == "Please approve this production order"


def test_submit_approval_updates_order_status(client):
    token = register_and_login(client, "Production Manager")
    order_id = create_order(client, token)

    response = submit_approval(client, token, order_id)
    assert response.status_code == 201, response.text

    order_response = client.get(
        f"/production-orders/{order_id}",
        headers=headers(token),
    )

    assert order_response.status_code == 200, order_response.text
    assert order_response.json()["status"] == "Pending Approval"


def test_submit_approval_for_planned_order(client):
    token = register_and_login(client, "Production Manager")
    order_id = create_order(client, token, status="Planned")

    response = submit_approval(client, token, order_id)

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "Pending"


def test_submit_approval_nonexistent_order(client):
    token = register_and_login(client, "Production Manager")

    response = submit_approval(client, token, 999999)

    assert response.status_code == 404
    assert response.json()["detail"] == "Production order not found"


def test_submit_approval_rejects_order_in_progress(client):
    token = register_and_login(client, "Production Manager")
    order_id = create_order(client, token)

    for next_status in ("Planned", "Released", "In Progress"):
        response = client.patch(
            f"/production-orders/{order_id}/status",
            json={"status": next_status},
            headers=headers(token),
        )
        assert response.status_code == 200, response.text

    response = submit_approval(client, token, order_id)

    assert response.status_code == 400
    assert "Only Draft or Planned" in response.json()["detail"]


def test_duplicate_pending_approval_rejected(client):
    token = register_and_login(client, "Production Manager")
    order_id = create_order(client, token)

    first = submit_approval(client, token, order_id)
    assert first.status_code == 201, first.text

    second = submit_approval(client, token, order_id)

    assert second.status_code == 409
    assert (
        second.json()["detail"]
        == "Production order already has a pending approval"
    )


def test_worker_cannot_submit_approval(client):
    manager_token = register_and_login(client, "Production Manager")
    order_id = create_order(client, manager_token)

    worker_token = register_and_login(client, "Worker")

    response = submit_approval(client, worker_token, order_id)

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "You do not have permission to perform this action"
    )


# ---------------------------------------------------------
# LIST APPROVALS
# ---------------------------------------------------------


def test_list_approvals(client):
    token = register_and_login(client, "Production Manager")
    order_id = create_order(client, token)

    submitted = submit_approval(client, token, order_id)
    assert submitted.status_code == 201, submitted.text

    response = client.get(
        "/production-approvals",
        headers=headers(token),
    )

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)
    assert any(
        item["production_order_id"] == order_id
        for item in response.json()
    )


# ---------------------------------------------------------
# APPROVE APPROVAL
# ---------------------------------------------------------


def test_approve_pending_approval(client):
    manager_token = register_and_login(client, "Production Manager")
    approver_token = register_and_login(client, "Plant Manager")
    order_id = create_order(client, manager_token)

    submitted = submit_approval(client, manager_token, order_id)
    assert submitted.status_code == 201, submitted.text

    approval_id = submitted.json()["id"]

    response = client.patch(
        f"/production-approvals/{approval_id}/approve",
        json={"comments": "Approved for production"},
        headers=headers(approver_token),
    )

    assert response.status_code == 200, response.text

    data = response.json()
    assert data["status"] == "Approved"
    assert data["comments"] == "Approved for production"
    assert data["approved_by"] is not None
    assert data["approved_at"] is not None

    order_response = client.get(
        f"/production-orders/{order_id}",
        headers=headers(approver_token),
    )
    assert order_response.status_code == 200, order_response.text
    assert order_response.json()["status"] == "Released"


def test_approve_nonexistent_approval(client):
    token = register_and_login(client, "Plant Manager")

    response = client.patch(
        "/production-approvals/999999/approve",
        json={"comments": "Approved"},
        headers=headers(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Approval request not found"


def test_worker_cannot_approve(client):
    manager_token = register_and_login(client, "Production Manager")
    order_id = create_order(client, manager_token)

    submitted = submit_approval(client, manager_token, order_id)
    assert submitted.status_code == 201, submitted.text

    worker_token = register_and_login(client, "Worker")

    response = client.patch(
        f"/production-approvals/{submitted.json()['id']}/approve",
        json={"comments": "Trying to approve"},
        headers=headers(worker_token),
    )

    assert response.status_code == 403


def test_approved_request_cannot_be_approved_again(client):
    manager_token = register_and_login(client, "Production Manager")
    approver_token = register_and_login(client, "Plant Manager")
    order_id = create_order(client, manager_token)

    submitted = submit_approval(client, manager_token, order_id)
    assert submitted.status_code == 201, submitted.text
    approval_id = submitted.json()["id"]

    first = client.patch(
        f"/production-approvals/{approval_id}/approve",
        json={"comments": "Approved"},
        headers=headers(approver_token),
    )
    assert first.status_code == 200, first.text

    second = client.patch(
        f"/production-approvals/{approval_id}/approve",
        json={"comments": "Approve again"},
        headers=headers(approver_token),
    )

    assert second.status_code == 400
    assert (
        second.json()["detail"]
        == "Only pending approvals can be approved"
    )


# ---------------------------------------------------------
# REJECT APPROVAL
# ---------------------------------------------------------


def test_reject_pending_approval(client):
    manager_token = register_and_login(client, "Production Manager")
    approver_token = register_and_login(client, "Plant Manager")
    order_id = create_order(client, manager_token)

    submitted = submit_approval(client, manager_token, order_id)
    assert submitted.status_code == 201, submitted.text
    approval_id = submitted.json()["id"]

    response = client.patch(
        f"/production-approvals/{approval_id}/reject",
        json={"comments": "Materials are not ready"},
        headers=headers(approver_token),
    )

    assert response.status_code == 200, response.text

    data = response.json()
    assert data["status"] == "Rejected"
    assert data["comments"] == "Materials are not ready"
    assert data["approved_by"] is not None
    assert data["approved_at"] is not None

    order_response = client.get(
        f"/production-orders/{order_id}",
        headers=headers(approver_token),
    )
    assert order_response.status_code == 200, order_response.text
    assert order_response.json()["status"] == "Draft"


def test_reject_requires_comments(client):
    manager_token = register_and_login(client, "Production Manager")
    approver_token = register_and_login(client, "Plant Manager")
    order_id = create_order(client, manager_token)

    submitted = submit_approval(client, manager_token, order_id)
    assert submitted.status_code == 201, submitted.text

    response = client.patch(
        f"/production-approvals/{submitted.json()['id']}/reject",
        json={"comments": None},
        headers=headers(approver_token),
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Comments are required when rejecting an approval"
    )


def test_reject_nonexistent_approval(client):
    token = register_and_login(client, "Plant Manager")

    response = client.patch(
        "/production-approvals/999999/reject",
        json={"comments": "Rejected"},
        headers=headers(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Approval request not found"


def test_worker_cannot_reject(client):
    manager_token = register_and_login(client, "Production Manager")
    order_id = create_order(client, manager_token)

    submitted = submit_approval(client, manager_token, order_id)
    assert submitted.status_code == 201, submitted.text

    worker_token = register_and_login(client, "Worker")

    response = client.patch(
        f"/production-approvals/{submitted.json()['id']}/reject",
        json={"comments": "Trying to reject"},
        headers=headers(worker_token),
    )

    assert response.status_code == 403


def test_rejected_request_cannot_be_rejected_again(client):
    manager_token = register_and_login(client, "Production Manager")
    approver_token = register_and_login(client, "Plant Manager")
    order_id = create_order(client, manager_token)

    submitted = submit_approval(client, manager_token, order_id)
    assert submitted.status_code == 201, submitted.text
    approval_id = submitted.json()["id"]

    first = client.patch(
        f"/production-approvals/{approval_id}/reject",
        json={"comments": "Rejected"},
        headers=headers(approver_token),
    )
    assert first.status_code == 200, first.text

    second = client.patch(
        f"/production-approvals/{approval_id}/reject",
        json={"comments": "Reject again"},
        headers=headers(approver_token),
    )

    assert second.status_code == 400
    assert (
        second.json()["detail"]
        == "Only pending approvals can be rejected"
    )


# ---------------------------------------------------------
# ADDITIONAL APPROVER ROLES
# ---------------------------------------------------------


def test_super_admin_can_approve(client):
    manager_token = register_and_login(client, "Production Manager")
    admin_token = register_and_login(client, "Super Admin")
    order_id = create_order(client, manager_token)

    submitted = submit_approval(client, manager_token, order_id)
    assert submitted.status_code == 201, submitted.text

    response = client.patch(
        f"/production-approvals/{submitted.json()['id']}/approve",
        json={"comments": "Admin approved"},
        headers=headers(admin_token),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "Approved"


def test_production_supervisor_can_submit_approval(client):
    # Plant Manager creates master data because Store Manager
    # is not permitted to create plants.
    setup_token = register_and_login(client, "Plant Manager")

    plant_id = create_plant(client, setup_token)
    line_id = create_line(client, setup_token, plant_id)
    product_id = create_product(client, setup_token, line_id)

    # Production Manager creates the order.
    manager_token = register_and_login(client, "Production Manager")

    order_response = client.post(
        "/production-orders",
        json={
            "order_number": unique("PO"),
            "product_id": product_id,
            "production_line_id": line_id,
            "quantity": 100,
            "priority": "Normal",
        },
        headers=headers(manager_token),
    )
    assert order_response.status_code == 201, order_response.text

    # Production Supervisor submits the approval.
    supervisor_token = register_and_login(
        client,
        "Production Supervisor",
    )

    response = submit_approval(
        client,
        supervisor_token,
        order_response.json()["id"],
    )

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "Pending"