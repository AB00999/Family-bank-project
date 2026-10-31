import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from login_checker import main, validate_password, validate_username


class LoginCheckerTests(unittest.TestCase):
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

    def test_main_stops_after_valid_format_attempt_without_authenticating(self):
        output = io.StringIO()
        with patch(
            "builtins.input",
            side_effect=[
                "x",
                "weak",
                "valid_user",
                "StrongPass1",
                "unused_user",
                "StrongPass1",
            ],
        ) as mocked_input, redirect_stdout(output):
            main()

        self.assertEqual(mocked_input.call_count, 4)
        self.assertIn("Login attempt 1 of 3", output.getvalue())
        self.assertIn("Login attempt 2 of 3", output.getvalue())
        self.assertNotIn("Login attempt 3 of 3", output.getvalue())
        self.assertIn("formats are valid", output.getvalue())
        self.assertIn("it does not sign you in", output.getvalue())
        self.assertNotIn("You have used all 3 attempts.", output.getvalue())
        self.assertNotIn("StrongPass1", output.getvalue())

    def test_main_stops_after_three_invalid_attempts(self):
        output = io.StringIO()
        with patch(
            "builtins.input",
            side_effect=["x", "weak", "x", "weak", "x", "weak"],
        ) as mocked_input, redirect_stdout(output):
            main()

        self.assertEqual(mocked_input.call_count, 6)
        self.assertIn("Login attempt 1 of 3", output.getvalue())
        self.assertIn("Login attempt 2 of 3", output.getvalue())
        self.assertIn("Login attempt 3 of 3", output.getvalue())
        self.assertIn("You have used all 3 attempts.", output.getvalue())
        self.assertIn("it does not sign you in", output.getvalue())


if __name__ == "__main__":
    unittest.main()
