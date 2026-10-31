def validate_username(username):
    return (
        3 <= len(username) <= 20
        and username.isascii()
        and username.replace("_", "").isalnum()
    )


def validate_password(password):
    return (
        len(password) >= 8
        and any(character.islower() for character in password)
        and any(character.isupper() for character in password)
        and any(character.isdigit() for character in password)
    )


def main():
    print("Username: 3-20 ASCII letters, numbers, or underscores.")
    print("Password: at least 8 characters, including uppercase, lowercase, and a number.")
    for attempt in range(1, 4):
        print(f"\nLogin attempt {attempt} of 3")
        username = input("Enter username: ").strip()
        password = input("Enter password: ")

        if validate_username(username) and validate_password(password):
            print("Username and password formats are valid.")
            print("This checker validates format only; it does not sign you in.")
            return

        print("Username or password format is invalid.")

    print("You have used all 3 attempts.")
    print("This checker validates format only; it does not sign you in.")


if __name__ == "__main__":
    main()
