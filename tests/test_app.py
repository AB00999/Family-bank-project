import csv
import io
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import app as family_bank
from werkzeug.security import check_password_hash, generate_password_hash


class FamilyBankFeatureTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "test.sqlite3"
        self.backup_directory = Path(self.temporary_directory.name) / "backups"
        self.database_patcher = patch.object(family_bank, "DATABASE", self.database_path)
        self.backup_patcher = patch.object(
            family_bank, "BACKUP_DIRECTORY", self.backup_directory
        )
        self.database_patcher.start()
        self.backup_patcher.start()
        family_bank.initialize_database()
        family_bank.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = family_bank.app.test_client()

    def tearDown(self):
        self.backup_patcher.stop()
        self.database_patcher.stop()
        self.temporary_directory.cleanup()

    def create_user(self, username="demo_user", email=None, role="User"):
        if email is None:
            email = f"{username}@example.test"
        with closing(family_bank.connect_database()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO users (
                        username, password_hash, email, phone_number, created_at, role
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        username,
                        generate_password_hash("old-test-password-123"),
                        email,
                        "555-0100",
                        family_bank.utc_timestamp(),
                        role,
                    ),
                )
                family_bank.seed_demo_transactions(connection, cursor.lastrowid)
                return cursor.lastrowid

    def csrf_token(self):
        with self.client.session_transaction() as browser_session:
            browser_session["_csrf_token"] = "test-csrf-token"
        return "test-csrf-token"

    def sign_in_as(self, user_id):
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = user_id
            browser_session["username"] = "demo_user"
            browser_session["session_version"] = 0
            browser_session["_csrf_token"] = "test-csrf-token"

    def test_registration_creates_demo_ledger_and_dashboard_shows_it(self):
        token = self.csrf_token()
        response = self.client.post(
            "/register",
            data={
                "csrf_token": token,
                "username": "new_demo",
                "email": "new@example.test",
                "phone_number": "555-0101",
                "password": "new-test-password-123",
            },
        )
        self.assertEqual(response.status_code, 302)
        dashboard = self.client.get("/dashboard")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"$2,583.00", dashboard.data)
        self.assertIn(b"Sample cafe purchase", dashboard.data)
        self.assertIn(b"No real funds", dashboard.data)

    def test_transaction_history_is_private_and_paginated(self):
        user_id = self.create_user()
        other_user_id = self.create_user(username="other_demo_user")
        with closing(family_bank.connect_database()) as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT INTO transactions (
                        user_id, amount_cents, description, occurred_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        (
                            user_id,
                            100,
                            f"History entry {day}",
                            f"2099-01-{day:02d}T00:00:00+00:00",
                        )
                        for day in range(1, 29)
                    ],
                )
                connection.execute(
                    """
                    INSERT INTO transactions (
                        user_id, amount_cents, description, occurred_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        other_user_id,
                        100,
                        "Private other-user entry",
                        "2099-01-29T00:00:00+00:00",
                    ),
                )

        response = self.client.get("/transactions")
        self.assertEqual(response.status_code, 302)

        self.sign_in_as(user_id)
        first_page = self.client.get("/transactions")
        self.assertEqual(first_page.status_code, 200)
        self.assertIn(b"History entry 28", first_page.data)
        self.assertIn(b"History entry 4", first_page.data)
        self.assertNotIn(b"History entry 3", first_page.data)
        self.assertNotIn(b"Private other-user entry", first_page.data)
        self.assertIn(b"Page 1 of 2", first_page.data)

        second_page = self.client.get("/transactions?page=2")
        self.assertEqual(second_page.status_code, 200)
        self.assertIn(b"History entry 3", second_page.data)
        self.assertIn(b"History entry 1", second_page.data)
        self.assertNotIn(b"History entry 4", second_page.data)

        invalid_page = self.client.get("/transactions?page=not-a-number")
        self.assertEqual(invalid_page.status_code, 400)

    def test_reset_link_is_hashed_expires_and_can_be_used_once(self):
        user_id = self.create_user(email="demo@example.test")
        self.csrf_token()
        with patch.dict(
            "os.environ",
            {
                "SMTP_HOST": "smtp.example.test",
                "SMTP_FROM": "demo@example.test",
                "PUBLIC_BASE_URL": "http://127.0.0.1:5000",
                "SMTP_SECURITY": "starttls",
            },
        ), patch.object(family_bank, "send_password_reset_email") as send_email:
            response = self.client.post(
                "/forgot-password",
                data={"csrf_token": "test-csrf-token", "email": "demo@example.test"},
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(send_email.call_count, 1)
        email_address, token = send_email.call_args.args
        self.assertEqual(email_address, "demo@example.test")
        self.assertEqual(self.client.get(f"/reset-password/{token}").status_code, 200)

        with closing(family_bank.connect_database()) as connection:
            stored_hash = connection.execute(
                "SELECT token_hash FROM password_reset_tokens"
            ).fetchone()[0]
            self.assertNotEqual(stored_hash, token)

        response = self.client.post(
            f"/reset-password/{token}",
            data={
                "csrf_token": "test-csrf-token",
                "password": "updated-test-password-456",
                "confirm_password": "updated-test-password-456",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(f"/reset-password/{token}").status_code, 302)
        with closing(family_bank.connect_database()) as connection:
            password_hash, session_version = connection.execute(
                "SELECT password_hash, session_version FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            token_count = connection.execute(
                "SELECT COUNT(*) FROM password_reset_tokens"
            ).fetchone()[0]
        self.assertTrue(
            check_password_hash(password_hash, "updated-test-password-456")
        )
        self.assertEqual(session_version, 1)
        self.assertEqual(token_count, 0)

    def test_password_reset_responses_do_not_disclose_unknown_email(self):
        token = self.csrf_token()
        response = self.client.post(
            "/forgot-password",
            data={"csrf_token": token, "email": "missing@example.test"},
            follow_redirects=True,
        )
        self.assertIn(
            b"If an active account uses that email address",
            response.data,
        )

    def test_smtp_configuration_requires_https_for_non_local_link(self):
        with patch.dict(
            "os.environ",
            {
                "SMTP_HOST": "smtp.example.test",
                "SMTP_FROM": "demo@example.test",
                "PUBLIC_BASE_URL": "http://example.test",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "must use HTTPS"):
                family_bank.reset_email_configuration()

    def test_smtp_sender_uses_starttls_and_sends_a_single_use_link(self):
        with patch.dict(
            "os.environ",
            {
                "SMTP_HOST": "smtp.example.test",
                "SMTP_PORT": "587",
                "SMTP_SECURITY": "starttls",
                "SMTP_FROM": "demo@example.test",
                "SMTP_USERNAME": "smtp-user",
                "SMTP_PASSWORD": "smtp-secret",
                "PUBLIC_BASE_URL": "http://127.0.0.1:5000",
            },
        ), patch.object(family_bank.smtplib, "SMTP") as smtp_factory:
            server = smtp_factory.return_value.__enter__.return_value
            with family_bank.app.test_request_context("/"):
                family_bank.send_password_reset_email(
                    "recipient@example.test",
                    "single-use-test-token",
                )

        smtp_factory.assert_called_once_with(
            "smtp.example.test",
            587,
            timeout=10,
        )
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("smtp-user", "smtp-secret")
        message = server.send_message.call_args.args[0]
        self.assertEqual(message["To"], "recipient@example.test")
        self.assertIn(
            "http://127.0.0.1:5000/reset-password/single-use-test-token",
            message.get_content(),
        )

    def test_missing_smtp_configuration_is_reported_and_token_is_removed(self):
        self.create_user(email="demo@example.test")
        self.csrf_token()
        with patch.dict("os.environ", {}, clear=True):
            response = self.client.post(
                "/forgot-password",
                data={"csrf_token": "test-csrf-token", "email": "demo@example.test"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"reset email could not be sent", response.data)
        with closing(family_bank.connect_database()) as connection:
            token_count = connection.execute(
                "SELECT COUNT(*) FROM password_reset_tokens"
            ).fetchone()[0]
            failed_events = connection.execute(
                """
                SELECT COUNT(*) FROM audit_events
                WHERE event_type = 'password_reset_email_failed'
                """
            ).fetchone()[0]
        self.assertEqual(token_count, 0)
        self.assertEqual(failed_events, 1)

    def test_admin_database_export_and_backup_restore(self):
        admin_id = self.create_user(username="demo_admin", role="Admin")
        self.sign_in_as(admin_id)

        export_response = self.client.get("/admin/database/export.csv")
        self.assertEqual(export_response.status_code, 200)
        rows = list(csv.reader(io.StringIO(export_response.get_data(as_text=True))))
        self.assertEqual(rows[0][0], "username")
        self.assertEqual(rows[1][0], "demo_admin")
        self.assertEqual(rows[1][3], "$2,583.00")

        backup_response = self.client.post(
            "/admin/database/backup",
            data={"csrf_token": "test-csrf-token"},
        )
        self.assertEqual(backup_response.status_code, 200)
        backup_bytes = backup_response.get_data()
        self.assertTrue(backup_bytes.startswith(b"SQLite format 3"))
        backup_response.close()

        newer_user_id = self.create_user(username="created_after_backup")
        with closing(family_bank.connect_database()) as connection:
            self.assertIsNotNone(
                connection.execute(
                    "SELECT id FROM users WHERE id = ?",
                    (newer_user_id,),
                ).fetchone()
            )

        restored = self.client.post(
            "/admin/database/restore",
            data={
                "csrf_token": "test-csrf-token",
                "backup_file": (io.BytesIO(backup_bytes), "demo-backup.sqlite3"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(restored.status_code, 302)
        self.assertEqual(restored.headers["Location"], "/admin")
        self.assertTrue(any(self.backup_directory.glob("family-bank-demo-*.sqlite3")))
        with closing(family_bank.connect_database()) as connection:
            restored_user = connection.execute(
                "SELECT username FROM users WHERE id = ?",
                (admin_id,),
            ).fetchone()
            missing_newer_user = connection.execute(
                "SELECT id FROM users WHERE id = ?",
                (newer_user_id,),
            ).fetchone()
        self.assertEqual(restored_user[0], "demo_admin")
        self.assertIsNone(missing_newer_user)

    def test_admin_restore_rejects_invalid_database_without_replacing_data(self):
        admin_id = self.create_user(username="demo_admin", role="Admin")
        self.sign_in_as(admin_id)
        response = self.client.post(
            "/admin/database/restore",
            data={
                "csrf_token": "test-csrf-token",
                "backup_file": (io.BytesIO(b"not a SQLite database"), "invalid.sqlite3"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"The database was not restored", response.data)
        with closing(family_bank.connect_database()) as connection:
            admin = connection.execute(
                "SELECT username FROM users WHERE id = ?",
                (admin_id,),
            ).fetchone()
        self.assertEqual(admin[0], "demo_admin")

    def test_admin_routes_remain_role_protected(self):
        user_id = self.create_user()
        self.sign_in_as(user_id)
        self.assertEqual(self.client.get("/admin").status_code, 403)
        self.assertEqual(self.client.get("/dashboard").status_code, 200)

        admin_id = self.create_user(username="demo_admin", role="Admin")
        self.sign_in_as(admin_id)
        admin_response = self.client.get("/admin")
        self.assertEqual(admin_response.status_code, 200)
        self.assertIn(b"SQLite demo database", admin_response.data)


if __name__ == "__main__":
    unittest.main()
