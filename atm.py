from datetime import datetime
from pathlib import Path

STARTING_BALANCE = 1000
MAX_BALANCE = 1_000_000
HISTORY_LINES_SHOWN = 10
BALANCE_FILE = Path(__file__).with_name("atm_balance.txt")
HISTORY_FILE = Path(__file__).with_name("atm_history.txt")


def load_balance(balance_file):
    # Use the starting balance if the file is missing or does not hold a valid amount.
    try:
        balance = int(Path(balance_file).read_text().strip())
    except (OSError, ValueError):
        return STARTING_BALANCE
    return balance if 0 <= balance <= MAX_BALANCE else STARTING_BALANCE


def read_amount(prompt):
    # Accept only plain 0-9 digits (with an optional leading minus) so input
    # like "1_000" or non-English digits is rejected. Return None if invalid.
    text = input(prompt).strip()
    digits = text[1:] if text.startswith("-") else text
    if digits.isascii() and digits.isdigit() and len(digits) <= 15:
        return int(text)
    print("Please enter a whole-dollar amount using numbers.")
    return None


def money(amount):
    # 1250 -> "$1,250"
    return f"${amount:,}"


def save_balance(balance_file, balance):
    # Write to a temporary file first, then swap it in, so a crash while
    # saving can never leave a half-written balance file.
    balance_file = Path(balance_file)
    temp_file = balance_file.with_name(balance_file.name + ".tmp")
    try:
        temp_file.write_text(str(balance))
        temp_file.replace(balance_file)
    except OSError:
        print("Warning: your balance could not be saved, so it will reset to the last saved amount next time.")


def record_transaction(history_file, kind, amount, balance):
    # Add one line to the end of the history file, e.g.
    # "2026-10-31 17:00 | Deposit | $250 | Balance: $1250"
    when = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"{when} | {kind} | {money(amount)} | Balance: {money(balance)}\n"
    try:
        with open(history_file, "a") as file:
            file.write(line)
    except OSError:
        print("Warning: this transaction could not be added to your history.")


def show_history(history_file):
    try:
        lines = Path(history_file).read_text().splitlines()
    except OSError:
        lines = []
    if not lines:
        print("No transactions yet.")
        return
    print(f"Last {HISTORY_LINES_SHOWN} transactions (newest first):")
    for line in reversed(lines[-HISTORY_LINES_SHOWN:]):
        print(line)


def run_menu(balance_file, history_file):
    balance = load_balance(balance_file)
    print("Family Bank ATM (demo)")

    while True:
        print("\n1. Check Balance")
        print("2. Deposit Money")
        print("3. Withdraw Money")
        print("4. Transaction History")
        print("5. Exit")
        choice = input("Choose an option (1, 2, 3, 4, or 5): ").strip()

        if choice == "1":
            print(f"Current Balance: {money(balance)}")
        elif choice == "2":
            deposit = read_amount("How much would you like to deposit? Enter whole dollars: ")
            if deposit is not None:
                if deposit <= 0:
                    print("Please enter an amount greater than $0.")
                elif balance + deposit > MAX_BALANCE:
                    print(f"Deposit not allowed: the demo balance limit is {money(MAX_BALANCE)}.")
                else:
                    balance += deposit
                    save_balance(balance_file, balance)
                    record_transaction(history_file, "Deposit", deposit, balance)
                    print("Deposit successful!")
                    print(f"New Balance: {money(balance)}")
        elif choice == "3":
            withdrawal = read_amount("How much would you like to withdraw? Enter whole dollars: ")
            if withdrawal is not None:
                if withdrawal <= 0:
                    print("Please enter an amount greater than $0.")
                elif withdrawal > balance:
                    print("Insufficient funds!")
                else:
                    balance -= withdrawal
                    save_balance(balance_file, balance)
                    record_transaction(history_file, "Withdrawal", withdrawal, balance)
                    print("Withdrawal successful!")
                    print(f"Remaining Balance: {money(balance)}")
        elif choice == "4":
            show_history(history_file)
        elif choice == "5":
            print("Thank you for using the Family Bank ATM demo.")
            break
        else:
            print("Invalid option. Please choose 1, 2, 3, 4, or 5.")


def main(balance_file=BALANCE_FILE, history_file=HISTORY_FILE):
    # Ctrl+C or Ctrl+Z ends the program politely instead of showing an error.
    try:
        run_menu(balance_file, history_file)
    except (KeyboardInterrupt, EOFError):
        print("\nThank you for using the Family Bank ATM demo.")


if __name__ == "__main__":
    main()
