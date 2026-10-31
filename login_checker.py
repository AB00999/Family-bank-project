import getpass
import hashlib
import hmac
import json
import os
from pathlib import Path

ACCOUNT_FILE = Path(__file__).with_name("login_account.json")
HASH_ITERATIONS = 600_000


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


def hash_password(password, salt, iterations):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)


def save_account(account_file, username, password):
    # Only a random salt and the password's hash are saved, never the password.
    salt = os.urandom(16)
    account = {
        "username": username,
        "salt": salt.hex(),
        "hash": hash_password(password, salt, HASH_ITERATIONS).hex(),
        "iterations": HASH_ITERATIONS,
    }
    Path(account_file).write_text(json.dumps(account))


def load_account(account_file):
    # Return None if the file is missing or damaged.
    try:
        account = json.loads(Path(account_file).read_text())
        return {
            "username": str(account["username"]),
            "salt": bytes.fromhex(account["salt"]),
            "hash": bytes.fromhex(account["hash"]),
            "iterations": int(account["iterations"]),
        }
    except (OSError, ValueError, KeyError, TypeError):
        return None


def check_login(account, username, password):
    # Always hash the password so a wrong username and a wrong password
    # take the same time and give the same message.
    attempt_hash = hash_password(password, account["salt"], account["iterations"])
    password_matches = hmac.compare_digest(attempt_hash, account["hash"])
    username_matches = hmac.compare_digest(username.encode(), account["username"].encode())
    return password_matches and username_matches


def create_account(account_file):
    print("No account found. Let's create one.")
    print("Username: 3-20 ASCII letters, numbers, or underscores.")
    print("Password: at least 8 characters, including uppercase, lowercase, and a number.")
    while True:
        username = input("Choose a username: ").strip()
        password = getpass.getpass("Choose a password: ")
        if not validate_username(username) or not validate_password(password):
            print("Username or password format is invalid. Please try again.")
        elif getpass.getpass("Confirm password: ") != password:
            print("Passwords did not match. Please try again.")
        else:
            break
    save_account(account_file, username, password)
    print("Account created. Please log in.")


def main(account_file=ACCOUNT_FILE):
    # Returns True after a successful login, otherwise False.
    account = load_account(account_file)
    if account is None:
        create_account(account_file)
        account = load_account(account_file)

    for attempt in range(1, 4):
        print(f"\nLogin attempt {attempt} of 3")
        username = input("Enter username: ").strip()
        password = getpass.getpass("Enter password: ")

        if check_login(account, username, password):
            print("Login successful!")
            return True

        print("Incorrect username or password.")

    print("You have used all 3 attempts. Access denied.")
    return False


if __name__ == "__main__":
    main()
