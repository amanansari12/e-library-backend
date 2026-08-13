from fastapi.testclient import TestClient


def register_user(client: TestClient, **overrides: str):
    payload = {
        "email": "alice@example.com",
        "username": "alice",
        "password": "secure-password-123",
        "full_name": "Alice Reader",
    }
    payload.update(overrides)
    return client.post("/api/v1/auth/register", json=payload)


def login_user(client: TestClient, password: str = "secure-password-123"):
    return client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": password},
    )


def test_registration_returns_safe_default_user(client: TestClient) -> None:
    response = register_user(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["username"] == "alice"
    assert body["role"] == "USER"
    assert "hashed_password" not in body


def test_registration_rejects_duplicate_email_and_username(client: TestClient) -> None:
    assert register_user(client).status_code == 201

    duplicate_email = register_user(client, username="other-user")
    duplicate_username = register_user(client, email="other@example.com")

    assert duplicate_email.status_code == 409
    assert duplicate_email.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    assert duplicate_username.status_code == 409
    assert duplicate_username.json()["error"]["code"] == "USERNAME_ALREADY_REGISTERED"


def test_registration_rejects_passwords_over_bcrypt_byte_limit(client: TestClient) -> None:
    response = register_user(client, password="x" * 73)

    assert response.status_code == 422


def test_login_profile_and_profile_update(client: TestClient) -> None:
    assert register_user(client).status_code == 201
    login_response = login_user(client)

    assert login_response.status_code == 200
    tokens = login_response.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    assert client.get("/api/v1/users/me").status_code == 401

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    profile_response = client.get("/api/v1/users/me", headers=headers)
    update_response = client.patch(
        "/api/v1/users/me", headers=headers, json={"full_name": "Alice Updated"}
    )

    assert profile_response.status_code == 200
    assert profile_response.json()["username"] == "alice"
    assert update_response.status_code == 200
    assert update_response.json()["full_name"] == "Alice Updated"


def test_profile_update_rejects_another_users_email(client: TestClient) -> None:
    assert register_user(client).status_code == 201
    assert register_user(client, email="other@example.com", username="other").status_code == 201
    token = login_user(client).json()["access_token"]

    response = client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "other@example.com"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_invalid_login_and_logout_revokes_refresh_token(client: TestClient) -> None:
    assert register_user(client).status_code == 201
    assert login_user(client, password="wrong-password").status_code == 401

    tokens = login_user(client).json()
    refresh_response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    logout_response = client.post(
        "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    revoked_refresh_response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]
    assert logout_response.status_code == 204
    assert revoked_refresh_response.status_code == 401
    assert revoked_refresh_response.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"
