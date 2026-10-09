
import uuid

import pytest


REPORTS = {
    "/reports/production": {
        "integer_fields": [
            "total_orders",
            "completed_orders",
            "in_progress_orders",
            "cancelled_orders",
            "total_planned_quantity",
            "total_produced_quantity",
            "total_rejected_quantity",
        ],
        "float_fields": ["average_efficiency_percentage"],
    },
    "/reports/quality": {
        "integer_fields": [
            "total_inspections",
            "passed_inspections",
            "failed_inspections",
            "total_defects",
            "critical_defects",
        ],
        "float_fields": ["pass_rate_percentage"],
    },
    "/reports/inventory": {
        "integer_fields": [
            "total_materials",
            "active_materials",
            "low_stock_materials",
            "total_inventory_movements",
        ],
        "float_fields": [
            "total_stock_in_quantity",
            "total_stock_out_quantity",
        ],
    },
    "/reports/downtime": {
        "integer_fields": [
            "total_records",
            "open_records",
            "closed_records",
            "total_downtime_minutes",
        ],
        "float_fields": ["average_downtime_minutes"],
    },
    "/reports/maintenance": {
        "integer_fields": [
            "total_records",
            "scheduled",
            "in_progress",
            "completed",
            "cancelled",
        ],
        "float_fields": [],
    },
}


@pytest.fixture
def auth_headers(client):
    email = f"reports_{uuid.uuid4().hex[:10]}@example.com"
    password = "Test@12345"

    register_response = client.post(
        "/auth/register",
        json={
            "full_name": "Reports Test User",
            "email": email,
            "password": password,
            "role": "Super Admin",
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


@pytest.mark.parametrize("endpoint", REPORTS.keys())
def test_report_requires_authentication(client, endpoint):
    response = client.get(endpoint)

    assert response.status_code == 401, response.text


@pytest.mark.parametrize("endpoint", REPORTS.keys())
def test_report_returns_valid_summary(client, auth_headers, endpoint):
    response = client.get(endpoint, headers=auth_headers)

    assert response.status_code == 200, response.text

    data = response.json()
    expected_fields = (
        REPORTS[endpoint]["integer_fields"]
        + REPORTS[endpoint]["float_fields"]
    )

    for field in expected_fields:
        assert field in data, f"{endpoint}: missing field {field}"

        value = data[field]
        assert isinstance(value, (int, float)), (
            f"{endpoint}: {field} must be numeric"
        )
        assert value >= 0, (
            f"{endpoint}: {field} must not be negative"
        )

    for field in REPORTS[endpoint]["integer_fields"]:
        assert isinstance(data[field], int), (
            f"{endpoint}: {field} must be an integer"
        )

    for field in REPORTS[endpoint]["float_fields"]:
        assert isinstance(data[field], (int, float)), (
            f"{endpoint}: {field} must be numeric"
        )


def test_production_report_order_counts_are_consistent(
    client,
    auth_headers,
):
    response = client.get(
        "/reports/production",
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["completed_orders"] <= data["total_orders"]
    assert data["in_progress_orders"] <= data["total_orders"]
    assert data["cancelled_orders"] <= data["total_orders"]


def test_quality_report_counts_are_consistent(
    client,
    auth_headers,
):
    response = client.get(
        "/reports/quality",
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["passed_inspections"] <= data["total_inspections"]
    assert data["failed_inspections"] <= data["total_inspections"]
    assert data["critical_defects"] <= data["total_defects"]

    assert 0 <= data["pass_rate_percentage"] <= 100


def test_inventory_report_counts_are_consistent(
    client,
    auth_headers,
):
    response = client.get(
        "/reports/inventory",
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["active_materials"] <= data["total_materials"]
    assert data["low_stock_materials"] <= data["active_materials"]


def test_downtime_report_counts_are_consistent(
    client,
    auth_headers,
):
    response = client.get(
        "/reports/downtime",
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["open_records"] <= data["total_records"]
    assert data["closed_records"] <= data["total_records"]


def test_maintenance_report_counts_are_consistent(
    client,
    auth_headers,
):
    response = client.get(
        "/reports/maintenance",
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["scheduled"] <= data["total_records"]
    assert data["in_progress"] <= data["total_records"]
    assert data["completed"] <= data["total_records"]
    assert data["cancelled"] <= data["total_records"]