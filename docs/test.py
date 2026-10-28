import secrets
import string
import sys


def generate_password(length=16, use_upper=True, use_digits=True, use_symbols=True):
    if length < 8:
        raise ValueError("Password length must be at least 8.")

    pools = [string.ascii_lowercase]
    if use_upper:
        pools.append(string.ascii_uppercase)
    if use_digits:
        pools.append(string.digits)
    if use_symbols:
        pools.append("!@#$%^&*()-_=+[]{};:,.?")

    # Guarantee at least one character from each selected pool.
    characters = [secrets.choice(pool) for pool in pools]
    all_characters = "".join(pools)
    characters += [secrets.choice(all_characters) for _ in range(length - len(characters))]
    secrets.SystemRandom().shuffle(characters)
    return "".join(characters)


def ask_yes_no(question):
    return input(f"{question} (Y/n): ").strip().lower() != "n"


def main():
    raw_length = input("Password length (default 16): ").strip()
    length = int(raw_length) if raw_length.isdigit() else 16
    password = generate_password(
        length,
        use_upper=ask_yes_no("Include uppercase letters?"),
        use_digits=ask_yes_no("Include numbers?"),
        use_symbols=ask_yes_no("Include symbols?"),
    )
    print(f"Your password: {password}")


def create_forgot_password_app():
    from flask import Flask, request

    app = Flask(__name__)
    reset_tokens = {}

    @app.route("/forgot-password", methods=["GET", "POST"])
    def forgot_password():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            if email:
                token = secrets.token_urlsafe(32)
                reset_tokens[token] = email
                print(f"Demo reset link: http://127.0.0.1:5003/reset/{token}")
            return "If that email exists, a reset link was sent."
        return (
            '<form method="post">'
            '<input type="email" name="email" placeholder="Email" required>'
            '<button type="submit">Send reset link</button>'
            "</form>"
        )

    return app


if __name__ == "__main__":
    if "--web" in sys.argv:
        create_forgot_password_app().run(port=5003)
    else:
        main()
