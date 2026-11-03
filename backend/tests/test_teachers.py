"""
Tests for teacher API endpoints.

Covers:
  - GET /api/v1/teachers/me/dashboard — class dashboard
  - GET /api/v1/teachers/me/classes — class listing
  - GET /api/v1/teachers/students/{id} — student detail
  - POST /api/v1/teachers/assignments — create assignment
  - GET /api/v1/teachers/courses — courses with topics
  - Role guard: student cannot access teacher endpoints
"""
import pytest


class TestTeacherDashboard:
    """Tests for teacher dashboard."""

    def test_get_dashboard(self, client, auth_headers_teacher):
        """Teacher can retrieve their class dashboard."""
        response = client.get(
            "/api/v1/teachers/me/dashboard",
            headers=auth_headers_teacher,
        )
        assert response.status_code == 200
        data = response.json()

        assert "teacher" in data
        assert "classes" in data
        assert "class_average_score" in data
        assert "total_students" in data
        assert "student_proficiency" in data
        assert "topic_distribution" in data
        assert "alerts" in data

        # Validate structure
        assert isinstance(data["classes"], list)
        assert isinstance(data["student_proficiency"], list)
        assert isinstance(data["topic_distribution"], list)
        assert isinstance(data["alerts"], list)

    def test_dashboard_with_class_filter(self, client, auth_headers_teacher):
        """Teacher can filter dashboard by class."""
        # First get classes
        classes_resp = client.get(
            "/api/v1/teachers/me/classes",
            headers=auth_headers_teacher,
        )
        classes = classes_resp.json()
        if not classes:
            pytest.skip("No classes available")

        class_id = classes[0]["id"]
        response = client.get(
            f"/api/v1/teachers/me/dashboard?class_id={class_id}",
            headers=auth_headers_teacher,
        )
        assert response.status_code == 200

    def test_dashboard_requires_teacher_role(self, client, auth_headers_student):
        """Student cannot access teacher dashboard."""
        response = client.get(
            "/api/v1/teachers/me/dashboard",
            headers=auth_headers_student,
        )
        assert response.status_code == 403


class TestTeacherClasses:
    """Tests for class listing."""

    def test_list_classes(self, client, auth_headers_teacher):
        """Teacher can list their classes."""
        response = client.get(
            "/api/v1/teachers/me/classes",
            headers=auth_headers_teacher,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            cls = data[0]
            assert "id" in cls
            assert "name" in cls
            assert "student_count" in cls


class TestTeacherStudentDetail:
    """Tests for individual student detail view."""

    def test_get_student_detail(self, client, auth_headers_teacher):
        """Teacher can view a student's detail."""
        # Get dashboard to find a student ID
        dash_resp = client.get(
            "/api/v1/teachers/me/dashboard",
            headers=auth_headers_teacher,
        )
        students = dash_resp.json().get("student_proficiency", [])
        if not students:
            pytest.skip("No students in class")

        student_id = students[0]["student_id"]
        response = client.get(
            f"/api/v1/teachers/students/{student_id}",
            headers=auth_headers_teacher,
        )
        assert response.status_code == 200
        data = response.json()
        assert "student_id" in data
        assert "student_name" in data
        assert "topic_mastery" in data
        assert "quiz_history" in data


class TestTeacherAssignments:
    """Tests for assignment creation."""

    def test_create_assignment(self, client, auth_headers_teacher):
        """Teacher can create an assignment for a student."""
        # Get a student and topic
        dash_resp = client.get(
            "/api/v1/teachers/me/dashboard",
            headers=auth_headers_teacher,
        )
        dashboard = dash_resp.json()
        students = dashboard.get("student_proficiency", [])
        topics = dashboard.get("topic_distribution", [])

        if not students or not topics:
            pytest.skip("No students or topics available")

        response = client.post(
            "/api/v1/teachers/assignments",
            headers=auth_headers_teacher,
            json={
                "student_id": students[0]["student_id"],
                "topic_id": topics[0]["topic_id"],
                "title": "Test Assignment",
                "description": "Created by automated test",
                "difficulty": "medium",
                "question_count": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == "Test Assignment"


class TestTeacherCourses:
    """Tests for course listing."""

    def test_list_courses(self, client, auth_headers_teacher):
        """Teacher can list courses with topics."""
        response = client.get(
            "/api/v1/teachers/courses",
            headers=auth_headers_teacher,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            course = data[0]
            assert "id" in course
            assert "name" in course
            assert "topics" in course

