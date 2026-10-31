from pathlib import Path

STARTING_BALANCE = 1000
MAX_BALANCE = 1_000_000
BALANCE_FILE = Path(__file__).with_name("atm_balance.txt")


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


def save_balance(balance_file, balance):
    try:
        Path(balance_file).write_text(str(balance))
    except OSError:
        print("Warning: your balance could not be saved.")


def run_menu(balance_file):
    balance = load_balance(balance_file)
    print("Family Bank ATM (demo)")

    while True:
        print("\n1. Check Balance")
        print("2. Deposit Money")
        print("3. Withdraw Money")
        print("4. Exit")
        choice = input("Choose an option (1, 2, 3, or 4): ").strip()

        if choice == "1":
            print(f"Current Balance: ${balance}")
        elif choice == "2":
            deposit = read_amount("How much would you like to deposit? Enter whole dollars: ")
            if deposit is not None:
                if deposit <= 0:
                    print("Please enter an amount greater than $0.")
                elif balance + deposit > MAX_BALANCE:
                    print(f"Deposit not allowed: the demo balance limit is ${MAX_BALANCE:,}.")
                else:
                    balance += deposit
                    save_balance(balance_file, balance)
                    print("Deposit successful!")
                    print(f"New Balance: ${balance}")
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
                    print("Withdrawal successful!")
                    print(f"Remaining Balance: ${balance}")
        elif choice == "4":
            print("Thank you for using the Family Bank ATM demo.")
            break
        else:
            print("Invalid option. Please choose 1, 2, 3, or 4.")


def main(balance_file=BALANCE_FILE):
    # Ctrl+C or Ctrl+Z ends the program politely instead of showing an error.
    try:
        run_menu(balance_file)
    except (KeyboardInterrupt, EOFError):
        print("\nThank you for using the Family Bank ATM demo.")


if __name__ == "__main__":
    main()
