balance = 1000

print("Family Bank ATM")
print("1. Check Balance")
print("2. Withdraw Money")
print("3. Deposit Money")

choice = input("Choose an option (1, 2, or 3): ").strip()

if choice == "1":
    print(f"Current Balance: ${balance}")
elif choice == "2":
    try:
        withdrawal = int(input("How much would you like to withdraw? Enter whole dollars: "))
    except ValueError:
        print("Please enter a whole-dollar amount using numbers.")
    else:
        if withdrawal <= 0:
            print("Please enter an amount greater than $0.")
        elif withdrawal <= balance:
            balance -= withdrawal
            print("Withdrawal successful!")
            print(f"Remaining Balance: ${balance}")
        else:
            print("Insufficient funds!")
elif choice == "3":
    try:
        deposit = int(input("How much would you like to deposit? Enter whole dollars: "))
    except ValueError:
        print("Please enter a whole-dollar amount using numbers.")
    else:
        if deposit <= 0:
            print("Please enter an amount greater than $0.")
        else:
            balance += deposit
            print("Deposit successful!")
            print(f"New Balance: ${balance}")
else:
    print("Invalid option. Please choose 1, 2, or 3.")
