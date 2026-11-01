import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from atm import load_balance, main, money, save_balance


class AtmTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.balance_file = Path(self.temporary_directory.name) / "balance.txt"
        self.history_file = Path(self.temporary_directory.name) / "history.txt"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def run_atm(self, answers):
        output = io.StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(output):
            main(self.balance_file, self.history_file)
        return output.getvalue()

    def test_menu_repeats_until_exit_and_updates_balance(self):
        output = self.run_atm(["1", "2", "250", "3", "100", "1", "5"])

        self.assertIn("Current Balance: $1,000", output)
        self.assertIn("New Balance: $1,250", output)
        self.assertIn("Remaining Balance: $1,150", output)
        self.assertEqual(output.count("1. Check Balance"), 5)
        self.assertIn("Thank you for using the Family Bank ATM demo.", output)

    def test_invalid_menu_choice_shows_error_and_returns_to_menu(self):
        output = self.run_atm(["9", "5"])

        self.assertIn("Invalid option. Please choose 1, 2, 3, 4, or 5.", output)
        self.assertEqual(output.count("1. Check Balance"), 2)

    def test_invalid_deposit_and_withdrawal_amounts_do_not_change_balance(self):
        output = self.run_atm(["2", "abc", "2", "0", "3", "not a number", "3", "-5", "1", "5"])

        self.assertEqual(
            output.count("Please enter a whole-dollar amount using numbers."),
            2,
        )
        self.assertEqual(output.count("Please enter an amount greater than $0."), 2)
        self.assertIn("Current Balance: $1,000", output)

    def test_withdrawal_cannot_exceed_balance(self):
        output = self.run_atm(["3", "1001", "1", "5"])

        self.assertIn("Insufficient funds!", output)
        self.assertIn("Current Balance: $1,000", output)

    def test_balance_is_saved_and_loaded_on_next_run(self):
        self.run_atm(["2", "250", "3", "100", "5"])
        self.assertEqual(self.balance_file.read_text(), "1150")

        output = self.run_atm(["1", "5"])
        self.assertIn("Current Balance: $1,150", output)

    def test_failed_transactions_do_not_save_a_balance(self):
        self.run_atm(["3", "5000", "2", "abc", "5"])
        self.assertFalse(self.balance_file.exists())
        self.assertFalse(self.history_file.exists())

    def test_missing_or_invalid_balance_file_uses_starting_balance(self):
        self.assertEqual(load_balance(self.balance_file), 1000)
        for bad_contents in ("not a number", "", "-50"):
            self.balance_file.write_text(bad_contents)
            self.assertEqual(load_balance(self.balance_file), 1000)

    def test_amounts_must_be_plain_ascii_digits(self):
        for bad_amount in ("1_000", "\u0663", "+5", "1.5", "99999999999999999999"):
            output = self.run_atm(["2", bad_amount, "1", "5"])
            self.assertIn("Please enter a whole-dollar amount using numbers.", output)
            self.assertIn("Current Balance: $1,000", output)
        self.assertFalse(self.balance_file.exists())

    def test_deposit_cannot_push_balance_over_the_limit(self):
        output = self.run_atm(["2", "999001", "2", "999000", "1", "5"])

        self.assertIn("Deposit not allowed", output)
        self.assertIn("New Balance: $1,000,000", output)
        self.assertEqual(self.balance_file.read_text(), "1000000")

        output = self.run_atm(["2", "1", "5"])
        self.assertIn("Deposit not allowed", output)

    def test_balance_file_over_the_limit_uses_starting_balance(self):
        self.balance_file.write_text("1000001")
        self.assertEqual(load_balance(self.balance_file), 1000)

    def test_history_lists_successful_transactions_newest_first(self):
        self.run_atm(["2", "250", "3", "5000", "3", "100", "5"])

        output = self.run_atm(["4", "5"])
        lines = [line for line in output.splitlines() if " | " in line]
        self.assertEqual(len(lines), 2)
        self.assertIn("Withdrawal | $100 | Balance: $1,150", lines[0])
        self.assertIn("Deposit | $250 | Balance: $1,250", lines[1])
        self.assertIn("newest first", output)

    def test_history_is_empty_at_first_and_shows_only_the_last_ten(self):
        self.assertIn("No transactions yet.", self.run_atm(["4", "5"]))

        self.run_atm(["2", "1"] * 12 + ["5"])
        output = self.run_atm(["4", "5"])
        lines = [line for line in output.splitlines() if " | " in line]
        self.assertEqual(len(lines), 10)
        self.assertIn("Balance: $1,012", lines[0])
        self.assertIn("Balance: $1,003", lines[-1])
        self.assertEqual(len(self.history_file.read_text().splitlines()), 12)

    def test_ctrl_c_and_ctrl_z_exit_politely_and_keep_saved_balance(self):
        for interruption in (KeyboardInterrupt(), EOFError()):
            output = self.run_atm(["2", "50", interruption])
            self.assertIn("Thank you for using the Family Bank ATM demo.", output)
            self.assertEqual(self.balance_file.read_text(), "1050")
            self.balance_file.unlink()

    def test_save_and_load_balance_round_trip(self):
        save_balance(self.balance_file, 420)
        self.assertEqual(load_balance(self.balance_file), 420)
        self.assertFalse(self.balance_file.with_name("balance.txt.tmp").exists())

    def test_money_adds_commas(self):
        self.assertEqual(money(5), "$5")
        self.assertEqual(money(1250), "$1,250")
        self.assertEqual(money(1_000_000), "$1,000,000")

    def test_save_failure_shows_a_clear_message(self):
        missing_folder_file = Path(self.temporary_directory.name) / "nope" / "balance.txt"
        output = io.StringIO()
        with redirect_stdout(output):
            save_balance(missing_folder_file, 500)
        self.assertIn("could not be saved", output.getvalue())


if __name__ == "__main__":
    unittest.main()
