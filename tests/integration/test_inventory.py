from uuid import uuid4

from app.models.raw_material import RawMaterial


def unique(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def register_and_login(client, role: str):
    email = (
        f"{role.lower().replace(' ', '_').replace('-', '_')}_"
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


def auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def create_raw_material(client, token: str, quantity: float = 100):
    response = client.post(
        "/raw-materials",
        json={
            "name": unique("Inventory Material"),
            "code": unique("RM"),
            "category": "Metal",
            "unit": "kg",
            "available_quantity": quantity,
            "minimum_stock": 10,
            "reorder_level": 20,
            "supplier_reference": "SUP-001",
            "description": "Inventory movement test material",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text

    return response.json()["id"]


def setup_material(client, role="Store Manager", quantity=100):
    token = register_and_login(client, role)

    material_id = create_raw_material(
        client,
        token,
        quantity=quantity,
    )

    return token, material_id


# ---------------------------------------------------------
# CREATE INVENTORY MOVEMENT - IN
# ---------------------------------------------------------


def test_create_inventory_in_success(client):
    token, material_id = setup_material(
        client,
        "Store Manager",
        quantity=100,
    )

    response = client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "IN",
            "quantity": 50,
            "reference": "GRN-001",
            "notes": "Received new stock",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["raw_material_id"] == material_id
    assert data["movement_type"] == "IN"
    assert data["quantity"] == 50
    assert data["quantity_before"] == 100
    assert data["quantity_after"] == 150
    assert data["reference"] == "GRN-001"
    assert data["notes"] == "Received new stock"


def test_inventory_in_updates_material_quantity(client, db):
    token, material_id = setup_material(
        client,
        "Store Manager",
        quantity=100,
    )

    response = client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "IN",
            "quantity": 25,
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201

    db.expire_all()

    material = db.query(RawMaterial).filter(
        RawMaterial.id == material_id
    ).first()

    assert material is not None
    assert material.available_quantity == 125


# ---------------------------------------------------------
# CREATE INVENTORY MOVEMENT - OUT
# ---------------------------------------------------------


def test_create_inventory_out_success(client):
    token, material_id = setup_material(
        client,
        "Store Manager",
        quantity=100,
    )

    response = client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "OUT",
            "quantity": 40,
            "reference": "ISSUE-001",
            "notes": "Material issued to production",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["movement_type"] == "OUT"
    assert data["quantity"] == 40
    assert data["quantity_before"] == 100
    assert data["quantity_after"] == 60


def test_inventory_out_updates_material_quantity(client, db):
    token, material_id = setup_material(
        client,
        "Store Manager",
        quantity=100,
    )

    response = client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "OUT",
            "quantity": 30,
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201

    db.expire_all()

    material = db.query(RawMaterial).filter(
        RawMaterial.id == material_id
    ).first()

    assert material is not None
    assert material.available_quantity == 70


def test_inventory_out_cannot_create_negative_stock(client):
    token, material_id = setup_material(
        client,
        "Store Manager",
        quantity=50,
    )

    response = client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "OUT",
            "quantity": 60,
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400

    assert (
        response.json()["detail"]
        == "Insufficient stock. Negative inventory is not allowed"
    )


def test_inventory_out_exact_available_quantity(client):
    token, material_id = setup_material(
        client,
        "Store Manager",
        quantity=50,
    )

    response = client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "OUT",
            "quantity": 50,
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["quantity_before"] == 50
    assert data["quantity_after"] == 0


# ---------------------------------------------------------
# INVALID MOVEMENT TYPES
# ---------------------------------------------------------


def test_invalid_inventory_movement_type_rejected(client):
    token, material_id = setup_material(
        client,
        "Store Manager",
    )

    response = client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "INVALID",
            "quantity": 10,
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400

    assert (
        response.json()["detail"]
        == "Invalid movement type. Use IN, OUT, or ADJUSTMENT"
    )


def test_adjustment_must_use_adjustment_endpoint(client):
    token, material_id = setup_material(
        client,
        "Store Manager",
    )

    response = client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "ADJUSTMENT",
            "quantity": 10,
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400

    assert (
        response.json()["detail"]
        == "Use the adjustment endpoint for ADJUSTMENT movements"
    )


# ---------------------------------------------------------
# INVENTORY ADJUSTMENT
# ---------------------------------------------------------


def test_inventory_adjustment_increase(client):
    token, material_id = setup_material(
        client,
        "Store Manager",
        quantity=100,
    )

    response = client.post(
        "/inventory-movements/adjustment",
        json={
            "raw_material_id": material_id,
            "new_quantity": 150,
            "reference": "ADJ-001",
            "notes": "Physical stock count",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["movement_type"] == "ADJUSTMENT"
    assert data["quantity"] == 50
    assert data["quantity_before"] == 100
    assert data["quantity_after"] == 150
    assert data["reference"] == "ADJ-001"


def test_inventory_adjustment_decrease(client):
    token, material_id = setup_material(
        client,
        "Store Manager",
        quantity=100,
    )

    response = client.post(
        "/inventory-movements/adjustment",
        json={
            "raw_material_id": material_id,
            "new_quantity": 60,
            "reference": "ADJ-002",
            "notes": "Stock correction",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["movement_type"] == "ADJUSTMENT"
    assert data["quantity"] == 40
    assert data["quantity_before"] == 100
    assert data["quantity_after"] == 60


def test_inventory_adjustment_to_zero(client):
    token, material_id = setup_material(
        client,
        "Store Manager",
        quantity=100,
    )

    response = client.post(
        "/inventory-movements/adjustment",
        json={
            "raw_material_id": material_id,
            "new_quantity": 0,
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["quantity_before"] == 100
    assert data["quantity_after"] == 0
    assert data["quantity"] == 100


def test_inventory_adjustment_updates_material(client, db):
    token, material_id = setup_material(
        client,
        "Store Manager",
        quantity=100,
    )

    response = client.post(
        "/inventory-movements/adjustment",
        json={
            "raw_material_id": material_id,
            "new_quantity": 75,
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201

    db.expire_all()

    material = db.query(RawMaterial).filter(
        RawMaterial.id == material_id
    ).first()

    assert material is not None
    assert material.available_quantity == 75


# ---------------------------------------------------------
# RAW MATERIAL VALIDATION
# ---------------------------------------------------------


def test_inventory_material_not_found(client):
    token = register_and_login(
        client,
        "Store Manager",
    )

    response = client.post(
        "/inventory-movements",
        json={
            "raw_material_id": 999999,
            "movement_type": "IN",
            "quantity": 10,
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Raw material not found"


def test_inventory_adjustment_material_not_found(client):
    token = register_and_login(
        client,
        "Store Manager",
    )

    response = client.post(
        "/inventory-movements/adjustment",
        json={
            "raw_material_id": 999999,
            "new_quantity": 100,
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Raw material not found"


def test_inventory_inactive_material_rejected(client, db):
    token, material_id = setup_material(
        client,
        "Store Manager",
        quantity=100,
    )

    material = db.query(RawMaterial).filter(
        RawMaterial.id == material_id
    ).first()

    assert material is not None

    material.is_active = False
    db.commit()
    db.refresh(material)

    response = client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "IN",
            "quantity": 10,
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Raw material is inactive"
    )


# ---------------------------------------------------------
# ROLE PROTECTION
# ---------------------------------------------------------


def test_worker_cannot_create_inventory_movement(client):
    store_token = register_and_login(
        client,
        "Store Manager",
    )

    material_id = create_raw_material(
        client,
        store_token,
        quantity=100,
    )

    worker_token = register_and_login(
        client,
        "Worker",
    )

    response = client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "IN",
            "quantity": 10,
        },
        headers=auth_headers(worker_token),
    )

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "You do not have permission to manage inventory"
    )


def test_quality_manager_cannot_create_inventory_movement(client):
    store_token = register_and_login(
        client,
        "Store Manager",
    )

    material_id = create_raw_material(
        client,
        store_token,
        quantity=100,
    )

    quality_token = register_and_login(
        client,
        "Quality Manager",
    )

    response = client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "IN",
            "quantity": 10,
        },
        headers=auth_headers(quality_token),
    )

    assert response.status_code == 403


def test_worker_cannot_create_inventory_adjustment(client):
    store_token = register_and_login(
        client,
        "Store Manager",
    )

    material_id = create_raw_material(
        client,
        store_token,
        quantity=100,
    )

    worker_token = register_and_login(
        client,
        "Worker",
    )

    response = client.post(
        "/inventory-movements/adjustment",
        json={
            "raw_material_id": material_id,
            "new_quantity": 50,
        },
        headers=auth_headers(worker_token),
    )

    assert response.status_code == 403


# ---------------------------------------------------------
# LIST MOVEMENTS
# ---------------------------------------------------------


def test_list_inventory_movements(client):
    token, material_id = setup_material(
        client,
        "Store Manager",
        quantity=100,
    )

    client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "IN",
            "quantity": 20,
        },
        headers=auth_headers(token),
    )

    client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "OUT",
            "quantity": 10,
        },
        headers=auth_headers(token),
    )

    response = client.get(
        "/inventory-movements",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 2


def test_list_material_movements(client):
    token, material_id = setup_material(
        client,
        "Store Manager",
        quantity=100,
    )

    client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "IN",
            "quantity": 25,
        },
        headers=auth_headers(token),
    )

    client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "OUT",
            "quantity": 10,
        },
        headers=auth_headers(token),
    )

    response = client.get(
        f"/inventory-movements/material/{material_id}",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 2

    for movement in response.json():
        assert movement["raw_material_id"] == material_id


def test_list_material_movements_not_found(client):
    token = register_and_login(
        client,
        "Store Manager",
    )

    response = client.get(
        "/inventory-movements/material/999999",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Raw material not found"


# ---------------------------------------------------------
# MULTIPLE MOVEMENTS / QUANTITY TRACKING
# ---------------------------------------------------------


def test_inventory_quantity_tracking_across_multiple_movements(
    client,
    db,
):
    token, material_id = setup_material(
        client,
        "Store Manager",
        quantity=100,
    )

    response = client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "IN",
            "quantity": 50,
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    assert response.json()["quantity_after"] == 150

    response = client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "OUT",
            "quantity": 30,
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    assert response.json()["quantity_after"] == 120

    response = client.post(
        "/inventory-movements/adjustment",
        json={
            "raw_material_id": material_id,
            "new_quantity": 110,
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    assert response.json()["quantity_after"] == 110

    db.expire_all()

    material = db.query(RawMaterial).filter(
        RawMaterial.id == material_id
    ).first()

    assert material is not None
    assert material.available_quantity == 110


def test_inventory_movement_records_created_by_user(client):
    token, material_id = setup_material(
        client,
        "Store Manager",
        quantity=100,
    )

    response = client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "IN",
            "quantity": 20,
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["created_by"] is not None


# ---------------------------------------------------------
# ALLOWED ROLES
# ---------------------------------------------------------


def test_production_manager_can_create_inventory_movement(client):
    store_token = register_and_login(
        client,
        "Store Manager",
    )

    material_id = create_raw_material(
        client,
        store_token,
        quantity=100,
    )

    production_manager_token = register_and_login(
        client,
        "Production Manager",
    )

    response = client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "IN",
            "quantity": 10,
        },
        headers=auth_headers(production_manager_token),
    )

    assert response.status_code == 201, response.text
def test_super_admin_can_create_inventory_movement(client):
    token = register_and_login(
        client,
        "Super Admin",
    )

    material_id = create_raw_material(
        client,
        token,
        quantity=100,
    )

    response = client.post(
        "/inventory-movements",
        json={
            "raw_material_id": material_id,
            "movement_type": "IN",
            "quantity": 10,
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text