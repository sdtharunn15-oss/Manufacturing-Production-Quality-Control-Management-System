import uuid


def get_bom_manager_token(client):
    unique = uuid.uuid4().hex[:8]
    email = f"bommanager-{unique}@test.com"

    register = client.post(
        "/auth/register",
        json={
            "full_name": "BOM Manager",
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


def create_plant(client, token):
    unique = uuid.uuid4().hex[:8]

    response = client.post(
        "/plants",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": f"BOM Test Plant {unique}",
            "code": f"BP-{unique}",
            "location": "Chennai",
            "description": "Plant for BOM testing",
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_production_line(client, token, plant_id):
    unique = uuid.uuid4().hex[:8]

    response = client.post(
        "/production-lines",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": f"BOM Test Line {unique}",
            "code": f"BL-{unique}",
            "plant_id": plant_id,
            "description": "Production line for BOM testing",
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_product(client, token, production_line_id):
    unique = uuid.uuid4().hex[:8]

    response = client.post(
        "/products",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": f"BOM Test Product {unique}",
            "code": f"BP-{unique}",
            "product_type": "Finished Goods",
            "unit": "pcs",
            "production_line_id": production_line_id,
            "description": "Product for BOM testing",
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_raw_material(client, token):
    unique = uuid.uuid4().hex[:8]

    response = client.post(
        "/raw-materials",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": f"BOM Test Steel {unique}",
            "code": f"BM-{unique}",
            "category": "Metal",
            "unit": "kg",
            "available_quantity": 100,
            "minimum_stock": 10,
            "reorder_level": 20,
            "description": "Material for BOM testing",
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_bom_setup(client, token):
    plant_id = create_plant(client, token)

    line_id = create_production_line(
        client,
        token,
        plant_id,
    )

    product_id = create_product(
        client,
        token,
        line_id,
    )

    material_id = create_raw_material(
        client,
        token,
    )

    return product_id, material_id


def create_bom(client, token, product_id, material_id, quantity):
    response = client.post(
        "/bom",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "product_id": product_id,
            "raw_material_id": material_id,
            "quantity_required": quantity,
        },
    )

    assert response.status_code == 201, (
        f"BOM creation failed: "
        f"{response.status_code} - {response.text}"
    )

    return response.json()


def test_create_bom(client):
    token = get_bom_manager_token(client)

    product_id, material_id = create_bom_setup(
        client,
        token,
    )

    data = create_bom(
        client,
        token,
        product_id,
        material_id,
        2.5,
    )

    assert data["product_id"] == product_id
    assert data["raw_material_id"] == material_id
    assert data["quantity_required"] == 2.5
    assert data["is_active"] is True


def test_get_product_bom(client):
    token = get_bom_manager_token(client)

    product_id, material_id = create_bom_setup(
        client,
        token,
    )

    create_bom(
        client,
        token,
        product_id,
        material_id,
        3,
    )

    response = client.get(
        f"/bom/product/{product_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["product_id"] == product_id
    assert data[0]["raw_material_id"] == material_id
    assert data[0]["quantity_required"] == 3


def test_calculate_bom_requirements(client):
    token = get_bom_manager_token(client)

    product_id, material_id = create_bom_setup(
        client,
        token,
    )

    create_bom(
        client,
        token,
        product_id,
        material_id,
        2,
    )

    response = client.get(
        f"/bom/product/{product_id}/requirements",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "production_quantity": 10,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["raw_material_id"] == material_id
    assert data[0]["quantity_per_unit"] == 2
    assert data[0]["required_quantity"] == 20
    assert data[0]["available_quantity"] == 100
    assert data[0]["sufficient_stock"] is True


def test_update_bom(client):
    token = get_bom_manager_token(client)

    product_id, material_id = create_bom_setup(
        client,
        token,
    )

    data = create_bom(
        client,
        token,
        product_id,
        material_id,
        2,
    )

    bom_id = data["id"]

    response = client.patch(
        f"/bom/{bom_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "quantity_required": 4,
        },
    )

    assert response.status_code == 200
    assert response.json()["quantity_required"] == 4


def test_deactivate_bom(client):
    token = get_bom_manager_token(client)

    product_id, material_id = create_bom_setup(
        client,
        token,
    )

    data = create_bom(
        client,
        token,
        product_id,
        material_id,
        2,
    )

    bom_id = data["id"]

    response = client.patch(
        f"/bom/{bom_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "is_active": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False
