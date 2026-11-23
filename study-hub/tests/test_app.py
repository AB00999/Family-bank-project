import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as study_hub


class StudyHubTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = Path(self.temporary_directory.name) / "test.sqlite3"
        self.patcher = patch.object(study_hub, "DATABASE", self.database)
        self.patcher.start()
        study_hub.initialize_database()
        study_hub.app.config.update(TESTING=True, SECRET_KEY="test")
        self.client = study_hub.app.test_client()

    def tearDown(self):
        self.patcher.stop()
        self.temporary_directory.cleanup()

    def register_user(self, email="student@example.test"):
        return self.client.post(
            "/register",
            data={
                "name": "Student",
                "email": email,
                "phone": "+1 555 123 4567",
                "password": "StudyPass123",
            },
        )

    def test_dashboard_loads(self):
        self.register_user()
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Study Hub", response.data)

    def test_subject_goal_flashcard_and_session_can_be_added(self):
        self.register_user()
        subject_response = self.client.post(
            "/subjects", data={"name": "Python", "color": "#4f46e5"}
        )
        self.assertEqual(subject_response.status_code, 302)

        with study_hub.connect_database() as connection:
            subject_id = connection.execute(
                "SELECT id FROM subjects WHERE name = 'Python'"
            ).fetchone()[0]

        goal_response = self.client.post(
            "/goals",
            data={"title": "Review functions", "target_minutes": "60", "due_date": ""},
        )
        card_response = self.client.post(
            "/flashcards",
            data={"subject_id": subject_id, "question": "What is a list?", "answer": "An ordered collection."},
        )
        session_response = self.client.post(
            "/sessions",
            data={"subject_id": subject_id, "minutes": "25", "notes": "Functions"},
        )

        self.assertEqual(goal_response.status_code, 302)
        self.assertEqual(card_response.status_code, 302)
        self.assertEqual(session_response.status_code, 302)

        with study_hub.connect_database() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM goals").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM flashcards").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM study_sessions").fetchone()[0], 1)

    def test_invalid_goal_is_rejected(self):
        self.register_user()
        response = self.client.post(
            "/goals",
            data={"title": "Invalid", "target_minutes": "0", "due_date": ""},
        )
        self.assertEqual(response.status_code, 302)
        with study_hub.connect_database() as connection:
            count = connection.execute("SELECT COUNT(*) FROM goals").fetchone()[0]
        self.assertEqual(count, 0)

    def test_registration_login_and_wrong_password(self):
        register_response = self.register_user("student2@example.test")
        self.assertEqual(register_response.status_code, 302)

        logout_response = self.client.post("/logout")
        self.assertEqual(logout_response.status_code, 302)

        login_response = self.client.post(
            "/login",
            data={"email": "student2@example.test", "password": "WrongPassword123"},
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertIn(b"Email or password is incorrect", login_response.data)

    def test_growth_guides_require_login_and_render(self):
        unauthenticated = self.client.get("/knowledge")
        self.assertEqual(unauthenticated.status_code, 302)

        self.register_user("growth@example.test")
        response = self.client.get("/knowledge")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Cybersecurity", response.data)
        self.assertIn(b"criminal record", response.data)
        self.assertIn(b"Build a bill and recovery plan", response.data)

    def test_early_learning_lesson_is_public_and_renders_safety_guidance(self):
        response = self.client.get("/early-learning")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Colors around us", response.data)
        self.assertIn(b"within arm's reach", response.data)
        self.assertIn(b"Lesson 10", response.data)
        self.assertEqual(response.data.count(b'class="lesson-card curriculum-lesson"'), 10)
        self.assertIn(b"Cyber safety: stop and ask", response.data)
        self.assertIn(b"AI is a tool, not a person", response.data)
        self.assertIn(b"Show grown-up answer", response.data)
        self.assertIn(b"Baby Loves Coding!", response.data)
        self.assertIn(b"nothing is saved", response.data)
        self.assertIn(b'id="print-lessons"', response.data)
        self.assertEqual(response.data.count(b'class="lesson-accessibility"'), 10)
        self.assertEqual(response.data.count(b'class="quiz-choice"'), 20)
        self.assertEqual(response.data.count(b'data-correct="true"'), 10)
        self.assertEqual(response.data.count(b'class="quiz-feedback"'), 10)


if __name__ == "__main__":
    unittest.main()
