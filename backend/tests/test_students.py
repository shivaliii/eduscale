"""
Tests for student API endpoints.

Covers:
  - GET /api/v1/students/me/dashboard — full dashboard retrieval
  - GET /api/v1/students/me/mastery — topic mastery list
  - GET /api/v1/students/me/quizzes — quiz listing
  - POST/GET quiz lifecycle: start → respond → submit → results
  - GET /api/v1/students/me/notes — notes listing
  - GET /api/v1/students/me/assignments — assignments listing
  - GET /api/v1/students/me/notifications — notifications listing
  - Role guard: teacher cannot access student endpoints
"""
import pytest


class TestStudentDashboard:
    """Tests for student dashboard."""

    def test_get_dashboard(self, client, auth_headers_student):
        """Student can retrieve their dashboard."""
        response = client.get(
            "/api/v1/students/me/dashboard",
            headers=auth_headers_student,
        )
        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "student" in data
        assert "overall_score" in data
        assert "total_questions_attempted" in data
        assert "quizzes_completed" in data
        assert "topic_mastery" in data
        assert "recommendations" in data
        assert "upcoming_assignments" in data
        assert "notifications" in data

        # Topic mastery should be a list
        assert isinstance(data["topic_mastery"], list)
        if len(data["topic_mastery"]) > 0:
            mastery = data["topic_mastery"][0]
            assert "topic_id" in mastery
            assert "topic_name" in mastery
            assert "mastery_score" in mastery
            assert "status" in mastery
            assert mastery["status"] in [
                "mastered", "working_towards", "needs_attention", "not_started"
            ]

    def test_dashboard_requires_student_role(self, client, auth_headers_teacher):
        """Teacher cannot access student dashboard."""
        response = client.get(
            "/api/v1/students/me/dashboard",
            headers=auth_headers_teacher,
        )
        assert response.status_code == 403


class TestStudentMastery:
    """Tests for topic mastery endpoint."""

    def test_get_mastery(self, client, auth_headers_student):
        """Student can retrieve their topic mastery."""
        response = client.get(
            "/api/v1/students/me/mastery",
            headers=auth_headers_student,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestStudentPerformance:
    """Tests for performance endpoint."""

    def test_get_performance(self, client, auth_headers_student):
        """Student can retrieve their performance trends."""
        response = client.get(
            "/api/v1/students/me/performance?days=30",
            headers=auth_headers_student,
        )
        assert response.status_code == 200
        data = response.json()
        assert "period_days" in data
        assert "total_attempts" in data
        assert "average_score" in data


class TestStudentQuizzes:
    """Tests for quiz listing and lifecycle."""

    def test_list_quizzes(self, client, auth_headers_student):
        """Student can list available quizzes."""
        response = client.get(
            "/api/v1/students/me/quizzes",
            headers=auth_headers_student,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            quiz = data[0]
            assert "id" in quiz
            assert "title" in quiz
            assert "question_count" in quiz

    def test_quiz_lifecycle(self, client, auth_headers_student):
        """Student can start, respond to, and submit a quiz."""
        # List quizzes to get an ID
        quizzes_resp = client.get(
            "/api/v1/students/me/quizzes",
            headers=auth_headers_student,
        )
        assert quizzes_resp.status_code == 200
        quizzes = quizzes_resp.json()
        if not quizzes:
            pytest.skip("No quizzes available")

        quiz_id = quizzes[0]["id"]

        # Start quiz
        start_resp = client.post(
            f"/api/v1/students/me/quizzes/{quiz_id}/start",
            headers=auth_headers_student,
        )
        assert start_resp.status_code == 200
        start_data = start_resp.json()
        assert "attempt_id" in start_data
        assert "questions" in start_data
        assert len(start_data["questions"]) > 0

        attempt_id = start_data["attempt_id"]
        questions = start_data["questions"]

        # Respond to first question
        q = questions[0]
        respond_resp = client.post(
            f"/api/v1/students/me/attempts/{attempt_id}/respond",
            headers=auth_headers_student,
            json={
                "question_id": q["id"],
                "answer": "A",  # Just pick A
            },
        )
        assert respond_resp.status_code == 200

        # Submit the quiz
        submit_resp = client.post(
            f"/api/v1/students/me/attempts/{attempt_id}/submit",
            headers=auth_headers_student,
        )
        assert submit_resp.status_code == 200
        result = submit_resp.json()
        assert "score" in result
        assert "total_questions" in result
        assert "correct_answers" in result
        assert "responses" in result

        # Get results
        results_resp = client.get(
            f"/api/v1/students/me/attempts/{attempt_id}/results",
            headers=auth_headers_student,
        )
        assert results_resp.status_code == 200
        results_data = results_resp.json()
        assert results_data["attempt_id"] == attempt_id


class TestStudentNotes:
    """Tests for notes endpoint."""

    def test_list_notes(self, client, auth_headers_student):
        """Student can list their notes."""
        response = client.get(
            "/api/v1/students/me/notes",
            headers=auth_headers_student,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            note = data[0]
            assert "id" in note
            assert "title" in note
            assert "content" in note

    def test_get_single_note(self, client, auth_headers_student):
        """Student can view a single note."""
        # List notes first
        notes_resp = client.get(
            "/api/v1/students/me/notes",
            headers=auth_headers_student,
        )
        notes = notes_resp.json()
        if not notes:
            pytest.skip("No notes available")

        note_id = notes[0]["id"]
        response = client.get(
            f"/api/v1/students/me/notes/{note_id}",
            headers=auth_headers_student,
        )
        assert response.status_code == 200


class TestStudentAssignments:
    """Tests for assignments endpoint."""

    def test_list_assignments(self, client, auth_headers_student):
        """Student can list their assignments."""
        response = client.get(
            "/api/v1/students/me/assignments",
            headers=auth_headers_student,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestStudentNotifications:
    """Tests for notifications endpoint."""

    def test_list_notifications(self, client, auth_headers_student):
        """Student can list their notifications."""
        response = client.get(
            "/api/v1/students/me/notifications",
            headers=auth_headers_student,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

