def get_store_manager_token(client, email):
    register = client.post(
        "/auth/register",
        json={
            "full_name": "Store Manager Test",
            "email": email,
            "password": "Test@12345",
            "role": "Store Manager",
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


def create_material(client, token, code, quantity=100):
    response = client.post(
        "/raw-materials",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Test Mild Steel",
            "code": code,
            "category": "Metal",
            "unit": "kg",
            "available_quantity": quantity,
            "minimum_stock": 20,
            "reorder_level": 30,
            "supplier_reference": "SUP-001",
            "description": "Test raw material",
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


def test_create_raw_material(client):
    token = get_store_manager_token(
        client,
        "storemanager-create@test.com",
    )

    material_id = create_material(
        client,
        token,
        "TMS-001",
        100,
    )

    response = client.get(
        f"/raw-materials/{material_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["available_quantity"] == 100


def test_stock_in_and_stock_out(client):
    token = get_store_manager_token(
        client,
        "storemanager-stock@test.com",
    )

    material_id = create_material(
        client,
        token,
        "STM-001",
        100,
    )

    stock_in = client.post(
        f"/raw-materials/{material_id}/stock-in",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "quantity": 50,
            "reference": "PO-TEST-001",
            "notes": "Additional stock",
        },
    )

    assert stock_in.status_code == 200
    assert stock_in.json()["available_quantity"] == 150

    stock_out = client.post(
        f"/raw-materials/{material_id}/stock-out",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "quantity": 30,
            "reference": "PROD-TEST-001",
            "notes": "Production usage",
        },
    )

    assert stock_out.status_code == 200
    assert stock_out.json()["available_quantity"] == 120


def test_stock_out_cannot_create_negative_inventory(client):
    token = get_store_manager_token(
        client,
        "storemanager-negative@test.com",
    )

    material_id = create_material(
        client,
        token,
        "NST-001",
        10,
    )

    response = client.post(
        f"/raw-materials/{material_id}/stock-out",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "quantity": 20,
            "reference": "NEG-TEST-001",
            "notes": "Should fail",
        },
    )

    assert response.status_code == 400
    assert "Negative inventory" in response.json()["detail"]
