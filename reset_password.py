import getpass
import re
from contextlib import closing

from werkzeug.security import generate_password_hash

from app import connect_database, record_audit_event


def reset_password(username, password):
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
        print("Username must be 3–32 characters: letters, numbers, ., _ or -.")
        return False
    if not 12 <= len(password) <= 128:
        print("Password must be between 12 and 128 characters.")
        return False

    with closing(connect_database()) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE users
                SET password_hash = ?, session_version = session_version + 1
                WHERE username = ?
                """,
                (generate_password_hash(password), username),
            )
            updated = cursor.rowcount == 1
            if updated:
                user_id = connection.execute(
                    "SELECT id FROM users WHERE username = ?",
                    (username,),
                ).fetchone()[0]
                record_audit_event(connection, "account_password_reset", user_id)

    if not updated:
        print("No account was found with that username.")
        return False

    print("Password reset. Sign in using the new password.")
    return True


def main():
    username = input("Account username: ").strip()
    password = getpass.getpass("New demo password (input hidden): ")
    confirmation = getpass.getpass("Confirm new password (input hidden): ")

    if password != confirmation:
        print("Passwords do not match. No changes were made.")
        return 1

    return 0 if reset_password(username, password) else 1


if __name__ == "__main__":
    raise SystemExit(main())
