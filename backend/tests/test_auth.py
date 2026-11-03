"""
Tests for authentication endpoints.

Covers:
  - POST /api/v1/auth/login — successful login, wrong password, non-existent user
  - GET /api/v1/auth/me — current user retrieval with valid/invalid token
  - Role-based token claims
"""
import pytest


class TestAuthLogin:
    """Tests for the /api/v1/auth/login endpoint."""

    def test_teacher_login_success(self, client, seeded_db):
        """Teacher can log in with correct credentials."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "teacher@eduscale.demo", "password": "teacher123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["role"] == "teacher"
        assert data["user"]["email"] == "teacher@eduscale.demo"

    def test_student_login_success(self, client, seeded_db):
        """Student can log in with correct credentials."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "alex@eduscale.demo", "password": "student123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "student"
        assert data["user"]["full_name"] == "Alex Johnson"

    def test_login_wrong_password(self, client, seeded_db):
        """Login fails with wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "teacher@eduscale.demo", "password": "wrongpass"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client, seeded_db):
        """Login fails for non-existent user."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "nobody@eduscale.demo", "password": "password"},
        )
        assert response.status_code == 401


class TestAuthMe:
    """Tests for the /api/v1/auth/me endpoint."""

    def test_get_current_user(self, client, auth_headers_teacher):
        """Authenticated user can retrieve their profile."""
        response = client.get("/api/v1/auth/me", headers=auth_headers_teacher)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "teacher@eduscale.demo"
        assert data["role"] == "teacher"

    def test_get_current_student(self, client, auth_headers_student):
        """Authenticated student can retrieve their profile."""
        response = client.get("/api/v1/auth/me", headers=auth_headers_student)
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "student"

    def test_no_token_returns_401(self, client, seeded_db):
        """Request without token returns 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client, seeded_db):
        """Request with invalid token returns 401."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

