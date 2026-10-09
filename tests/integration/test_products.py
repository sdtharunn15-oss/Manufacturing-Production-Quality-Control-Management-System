def get_manager_token(client):
    register = client.post(
        "/auth/register",
        json={
            "full_name": "Product Manager Test",
            "email": "productmanager@test.com",
            "password": "Test@12345",
            "role": "Plant Manager",
        },
    )

    assert register.status_code == 201

    login = client.post(
        "/auth/login",
        json={
            "email": "productmanager@test.com",
            "password": "Test@12345",
        },
    )

    assert login.status_code == 200

    return login.json()["access_token"]


def create_plant_and_line(client, token):
    plant_response = client.post(
        "/plants",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Product Test Plant",
            "code": "PTP-001",
            "location": "Chennai",
            "description": "Plant for product tests",
        },
    )

    assert plant_response.status_code == 201

    plant_id = plant_response.json()["id"]

    line_response = client.post(
        "/production-lines",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Product Test Line",
            "code": "PTL-001",
            "plant_id": plant_id,
            "description": "Line for product tests",
        },
    )

    assert line_response.status_code == 201

    return line_response.json()["id"]


def test_create_product(client):
    token = get_manager_token(client)
    line_id = create_plant_and_line(client, token)

    response = client.post(
        "/products",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Test Steel Gear",
            "code": "TSG-001",
            "product_type": "Finished Product",
            "unit": "pcs",
            "production_line_id": line_id,
            "description": "Test manufactured product",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Test Steel Gear"
    assert data["code"] == "TSG-001"
    assert data["product_type"] == "Finished Product"
    assert data["unit"] == "pcs"
    assert data["production_line_id"] == line_id


def test_list_products_requires_authentication(client):
    response = client.get("/products")

    assert response.status_code in (401, 403)
