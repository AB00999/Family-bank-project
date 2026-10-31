import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from login_checker import (
    load_account,
    main,
    save_account,
    validate_password,
    validate_username,
)


class LoginCheckerTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.account_file = Path(self.temporary_directory.name) / "account.json"
        # Fewer hashing rounds keep the tests fast.
        patcher = patch("login_checker.HASH_ITERATIONS", 1000)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.temporary_directory.cleanup)

    def run_checker(self, typed, hidden):
        # typed = answers to input(); hidden = answers to getpass (passwords).
        output = io.StringIO()
        with patch("builtins.input", side_effect=typed), patch(
            "login_checker.getpass.getpass", side_effect=hidden
        ), redirect_stdout(output):
            result = main(self.account_file)
        return result, output.getvalue()

    def make_account(self):
        save_account(self.account_file, "family_user", "StrongPass1")

    def test_username_must_be_three_to_twenty_ascii_letters_numbers_or_underscores(self):
        self.assertTrue(validate_username("abc"))
        self.assertTrue(validate_username("Family_Bank_01"))
        self.assertTrue(validate_username("a" * 20))
        self.assertFalse(validate_username("ab"))
        self.assertFalse(validate_username("a" * 21))
        self.assertFalse(validate_username("family bank"))
        self.assertFalse(validate_username("family-bank"))
        self.assertFalse(validate_username("café"))

    def test_password_must_meet_length_and_character_requirements(self):
        self.assertTrue(validate_password("StrongPass1"))
        self.assertTrue(validate_password("Abcdef1!"))
        self.assertFalse(validate_password("Ab1cdef"))
        self.assertFalse(validate_password("alllowercase1"))
        self.assertFalse(validate_password("ALLUPPERCASE1"))
        self.assertFalse(validate_password("NoDigitsHere"))

    def test_first_run_creates_account_with_hashed_password_then_logs_in(self):
        result, output = self.run_checker(
            ["family_user", "family_user"],
            ["StrongPass1", "StrongPass1", "StrongPass1"],
        )

        self.assertTrue(result)
        self.assertIn("Account created", output)
        self.assertIn("Login successful!", output)
        saved_text = self.account_file.read_text()
        self.assertNotIn("StrongPass1", saved_text)
        self.assertIn("family_user", saved_text)
        self.assertIn("hash", saved_text)

    def test_invalid_or_mismatched_new_account_details_are_asked_again(self):
        result, output = self.run_checker(
            ["x", "family_user", "family_user", "family_user"],
            ["weak", "StrongPass1", "Different1", "StrongPass1", "StrongPass1", "StrongPass1"],
        )

        self.assertTrue(result)
        self.assertIn("format is invalid", output)
        self.assertIn("Passwords did not match", output)
        self.assertEqual(load_account(self.account_file)["username"], "family_user")

    def test_correct_login_stops_after_a_failed_attempt(self):
        self.make_account()
        result, output = self.run_checker(
            ["family_user", "family_user", "unused"],
            ["WrongPass1", "StrongPass1", "unused"],
        )

        self.assertTrue(result)
        self.assertIn("Login attempt 1 of 3", output)
        self.assertIn("Login attempt 2 of 3", output)
        self.assertNotIn("Login attempt 3 of 3", output)
        self.assertIn("Incorrect username or password.", output)
        self.assertIn("Login successful!", output)
        self.assertNotIn("Account created", output)

    def test_three_wrong_attempts_deny_access(self):
        self.make_account()
        result, output = self.run_checker(
            ["family_user", "other_user", "family_user"],
            ["WrongPass1", "StrongPass1", "AnotherWrong2"],
        )

        self.assertFalse(result)
        self.assertEqual(output.count("Incorrect username or password."), 3)
        self.assertIn("Access denied", output)
        self.assertNotIn("Login successful!", output)

    def test_damaged_account_file_is_treated_as_missing(self):
        self.assertIsNone(load_account(self.account_file))
        for bad_contents in ("", "not json", "{}", '{"username": "a", "salt": "zz"}'):
            self.account_file.write_text(bad_contents)
            self.assertIsNone(load_account(self.account_file))

    def test_existing_account_is_not_overwritten_by_a_new_run(self):
        self.make_account()
        before = self.account_file.read_text()
        self.run_checker(["family_user"], ["StrongPass1"])
        self.assertEqual(self.account_file.read_text(), before)

    def test_same_password_gets_a_different_salt_and_hash(self):
        save_account(self.account_file, "family_user", "StrongPass1")
        first = self.account_file.read_text()
        save_account(self.account_file, "family_user", "StrongPass1")
        self.assertNotEqual(first, self.account_file.read_text())


if __name__ == "__main__":
    unittest.main()
