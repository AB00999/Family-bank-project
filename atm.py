from pathlib import Path

STARTING_BALANCE = 1000
BALANCE_FILE = Path(__file__).with_name("atm_balance.txt")


def load_balance(balance_file):
    # Use the starting balance if the file is missing or does not hold a valid amount.
    try:
        balance = int(Path(balance_file).read_text().strip())
    except (OSError, ValueError):
        return STARTING_BALANCE
    return balance if balance >= 0 else STARTING_BALANCE


def save_balance(balance_file, balance):
    try:
        Path(balance_file).write_text(str(balance))
    except OSError:
        print("Warning: your balance could not be saved.")


def main(balance_file=BALANCE_FILE):
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
            try:
                deposit = int(input("How much would you like to deposit? Enter whole dollars: "))
            except ValueError:
                print("Please enter a whole-dollar amount using numbers.")
            else:
                if deposit <= 0:
                    print("Please enter an amount greater than $0.")
                else:
                    balance += deposit
                    save_balance(balance_file, balance)
                    print("Deposit successful!")
                    print(f"New Balance: ${balance}")
        elif choice == "3":
            try:
                withdrawal = int(input("How much would you like to withdraw? Enter whole dollars: "))
            except ValueError:
                print("Please enter a whole-dollar amount using numbers.")
            else:
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


if __name__ == "__main__":
    main()
