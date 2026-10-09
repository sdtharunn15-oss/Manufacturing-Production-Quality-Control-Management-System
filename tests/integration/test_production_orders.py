import uuid
from datetime import datetime, timedelta


def unique(value):
    return f"{value}-{uuid.uuid4().hex[:8]}"


def get_manager_token(client):
    email = unique("order_manager") + "@example.com"

    register = client.post(
        "/auth/register",
        json={
            "full_name": "Order Manager",
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


def setup_product(client, token):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Create plant
    plant = client.post(
        "/plants",
        headers=headers,
        json={
            "name": unique("Production Order Plant"),
            "code": unique("POP"),
            "location": "Chennai",
            "description": "Plant for production order tests",
        },
    )
    assert plant.status_code == 201

    plant_id = plant.json()["id"]

    # Create production line
    line = client.post(
        "/production-lines",
        headers=headers,
        json={
            "name": unique("Production Order Line"),
            "code": unique("POL"),
            "plant_id": plant_id,
            "description": "Line for production order tests",
        },
    )
    assert line.status_code == 201

    line_id = line.json()["id"]

    # Create product
    product = client.post(
        "/products",
        headers=headers,
        json={
            "name": unique("Production Order Product"),
            "code": unique("POP"),
            "product_type": "Finished Product",
            "unit": "pcs",
            "production_line_id": line_id,
            "description": "Product for production order tests",
        },
    )
    assert product.status_code == 201

    product_id = product.json()["id"]

    return plant_id, line_id, product_id


def create_order(client, token, product_id, line_id):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = client.post(
        "/production-orders",
        headers=headers,
        json={
            "order_number": unique("PO"),
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
            "notes": "Production order integration test",
        },
    )

    assert response.status_code == 201

    return response.json()


def test_create_production_order(client):
    token = get_manager_token(client)

    _, line_id, product_id = setup_product(
        client,
        token,
    )

    order = create_order(
        client,
        token,
        product_id,
        line_id,
    )

    assert order["product_id"] == product_id
    assert order["production_line_id"] == line_id
    assert order["quantity"] == 100
    assert order["status"] == "Draft"


def test_list_production_orders(client):
    token = get_manager_token(client)

    _, line_id, product_id = setup_product(
        client,
        token,
    )

    create_order(
        client,
        token,
        product_id,
        line_id,
    )

    response = client.get(
        "/production-orders",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


def test_get_production_order(client):
    token = get_manager_token(client)

    _, line_id, product_id = setup_product(
        client,
        token,
    )

    order = create_order(
        client,
        token,
        product_id,
        line_id,
    )

    order_id = order["id"]

    response = client.get(
        f"/production-orders/{order_id}",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == order_id


def test_update_draft_production_order(client):
    token = get_manager_token(client)

    _, line_id, product_id = setup_product(
        client,
        token,
    )

    order = create_order(
        client,
        token,
        product_id,
        line_id,
    )

    order_id = order["id"]

    response = client.patch(
        f"/production-orders/{order_id}",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "quantity": 150,
            "priority": "High",
            "notes": "Updated production quantity",
        },
    )

    assert response.status_code == 200
    assert response.json()["quantity"] == 150
    assert response.json()["priority"] == "High"


def test_production_order_status_transitions(client):
    token = get_manager_token(client)

    _, line_id, product_id = setup_product(
        client,
        token,
    )

    order = create_order(
        client,
        token,
        product_id,
        line_id,
    )

    order_id = order["id"]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Draft -> Planned
    response = client.patch(
        f"/production-orders/{order_id}/status",
        headers=headers,
        json={
            "status": "Planned"
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Planned"

    # Planned -> Released
    response = client.patch(
        f"/production-orders/{order_id}/status",
        headers=headers,
        json={
            "status": "Released"
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Released"

    # Released -> In Progress
    response = client.patch(
        f"/production-orders/{order_id}/status",
        headers=headers,
        json={
            "status": "In Progress"
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "In Progress"


def test_invalid_production_order_status_transition(client):
    token = get_manager_token(client)

    _, line_id, product_id = setup_product(
        client,
        token,
    )

    order = create_order(
        client,
        token,
        product_id,
        line_id,
    )

    order_id = order["id"]

    response = client.patch(
        f"/production-orders/{order_id}/status",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "status": "Completed"
        },
    )

    assert response.status_code == 400


def test_duplicate_order_number_rejected(client):
    token = get_manager_token(client)

    _, line_id, product_id = setup_product(
        client,
        token,
    )

    order_number = unique("DUPLICATE-PO")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    payload = {
        "order_number": order_number,
        "product_id": product_id,
        "production_line_id": line_id,
        "quantity": 100,
        "priority": "Normal",
    }

    first = client.post(
        "/production-orders",
        headers=headers,
        json=payload,
    )

    second = client.post(
        "/production-orders",
        headers=headers,
        json=payload,
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_invalid_planned_dates_rejected(client):
    token = get_manager_token(client)

    _, line_id, product_id = setup_product(
        client,
        token,
    )

    start_date = datetime.now() + timedelta(days=2)
    end_date = datetime.now() + timedelta(days=1)

    response = client.post(
        "/production-orders",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "order_number": unique("DATE-PO"),
            "product_id": product_id,
            "production_line_id": line_id,
            "quantity": 100,
            "priority": "Normal",
            "planned_start_date": start_date.isoformat(),
            "planned_end_date": end_date.isoformat(),
        },
    )

    assert response.status_code == 400


def test_material_availability_without_bom_rejected(client):
    token = get_manager_token(client)

    _, line_id, product_id = setup_product(
        client,
        token,
    )

    order = create_order(
        client,
        token,
        product_id,
        line_id,
    )

    response = client.get(
        f"/production-orders/{order['id']}/material-availability",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No active BOM found for this product"