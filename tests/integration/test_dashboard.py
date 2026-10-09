
import uuid


def register_and_login(client, role="Super Admin"):
    email = f"dashboard_{uuid.uuid4().hex[:10]}@example.com"
    password = "Test@12345"

    register_response = client.post(
        "/auth/register",
        json={
            "full_name": "Dashboard Test User",
            "email": email,
            "password": password,
            "role": role,
        },
    )
    assert register_response.status_code == 201, register_response.text

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200, login_response.text

    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_returns_summary(client):
    headers = register_and_login(client)

    response = client.get("/dashboard", headers=headers)

    assert response.status_code == 200, response.text

    data = response.json()

    expected_fields = [
        "total_plants",
        "active_plants",
        "total_production_lines",
        "active_production_lines",
        "total_products",
        "active_products",
        "total_production_orders",
        "draft_orders",
        "planned_orders",
        "pending_approval_orders",
        "released_orders",
        "in_progress_orders",
        "completed_orders",
        "cancelled_orders",
        "total_batches",
        "planned_batches",
        "in_progress_batches",
        "completed_batches",
        "rejected_batches",
        "total_machines",
        "available_machines",
        "machines_in_use",
        "machines_under_maintenance",
        "machines_in_breakdown",
        "inactive_machines",
        "total_workers",
        "active_workers",
        "total_raw_materials",
        "low_stock_materials",
        "total_quality_inspections",
        "passed_inspections",
        "failed_inspections",
        "total_defects",
        "open_defects",
        "critical_defects",
        "total_maintenance_records",
        "scheduled_maintenance",
        "ongoing_maintenance",
        "completed_maintenance",
        "total_downtime_records",
        "open_downtime_records",
        "total_inventory_movements",
    ]

    for field in expected_fields:
        assert field in data, f"Missing dashboard field: {field}"
        assert isinstance(data[field], int), (
            f"Dashboard field {field} should be an integer"
        )
        assert data[field] >= 0, (
            f"Dashboard field {field} should not be negative"
        )


def test_dashboard_requires_authentication(client):
    response = client.get("/dashboard")

    assert response.status_code == 401


def test_dashboard_counts_are_consistent(client):
    headers = register_and_login(client)

    response = client.get("/dashboard", headers=headers)

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["active_plants"] <= data["total_plants"]
    assert (
        data["active_production_lines"]
        <= data["total_production_lines"]
    )
    assert data["active_products"] <= data["total_products"]
    assert data["active_workers"] <= data["total_workers"]
    assert data["low_stock_materials"] <= data["total_raw_materials"]
    assert (
        data["passed_inspections"] + data["failed_inspections"]
        <= data["total_quality_inspections"]
    )