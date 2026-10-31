import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from atm import load_balance, main, save_balance


class AtmTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.balance_file = Path(self.temporary_directory.name) / "balance.txt"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def run_atm(self, answers):
        output = io.StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(output):
            main(self.balance_file)
        return output.getvalue()

    def test_menu_repeats_until_exit_and_updates_balance(self):
        output = self.run_atm(["1", "2", "250", "3", "100", "1", "4"])

        self.assertIn("Current Balance: $1000", output)
        self.assertIn("New Balance: $1250", output)
        self.assertIn("Remaining Balance: $1150", output)
        self.assertEqual(output.count("1. Check Balance"), 5)
        self.assertIn("Thank you for using the Family Bank ATM demo.", output)

    def test_invalid_menu_choice_shows_error_and_returns_to_menu(self):
        output = self.run_atm(["9", "4"])

        self.assertIn("Invalid option. Please choose 1, 2, 3, or 4.", output)
        self.assertEqual(output.count("1. Check Balance"), 2)

    def test_invalid_deposit_and_withdrawal_amounts_do_not_change_balance(self):
        output = self.run_atm(["2", "abc", "2", "0", "3", "not a number", "3", "-5", "1", "4"])

        self.assertEqual(
            output.count("Please enter a whole-dollar amount using numbers."),
            2,
        )
        self.assertEqual(output.count("Please enter an amount greater than $0."), 2)
        self.assertIn("Current Balance: $1000", output)

    def test_withdrawal_cannot_exceed_balance(self):
        output = self.run_atm(["3", "1001", "1", "4"])

        self.assertIn("Insufficient funds!", output)
        self.assertIn("Current Balance: $1000", output)

    def test_balance_is_saved_and_loaded_on_next_run(self):
        self.run_atm(["2", "250", "3", "100", "4"])
        self.assertEqual(self.balance_file.read_text(), "1150")

        output = self.run_atm(["1", "4"])
        self.assertIn("Current Balance: $1150", output)

    def test_failed_transactions_do_not_save_a_balance(self):
        self.run_atm(["3", "5000", "2", "abc", "4"])
        self.assertFalse(self.balance_file.exists())

    def test_missing_or_invalid_balance_file_uses_starting_balance(self):
        self.assertEqual(load_balance(self.balance_file), 1000)
        for bad_contents in ("not a number", "", "-50"):
            self.balance_file.write_text(bad_contents)
            self.assertEqual(load_balance(self.balance_file), 1000)

    def test_save_and_load_balance_round_trip(self):
        save_balance(self.balance_file, 420)
        self.assertEqual(load_balance(self.balance_file), 420)


if __name__ == "__main__":
    unittest.main()
