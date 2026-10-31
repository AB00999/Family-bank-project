import csv
import hashlib
import io
import os
import re
import secrets
import smtplib
import ssl
import sqlite3
import tempfile
from email.message import EmailMessage
from contextlib import closing
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from urllib.parse import urlsplit

from flask import (
    Flask,
    Response,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__, instance_relative_config=True)
app.config.update(
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_COOKIE_SECURE") == "1",
    MAX_CONTENT_LENGTH=25 * 1024 * 1024,
)

Path(app.instance_path).mkdir(parents=True, exist_ok=True)
DATABASE = Path(app.instance_path) / "family_bank.sqlite3"
BACKUP_DIRECTORY = Path(app.instance_path) / "backups"


def initialize_database():
    with closing(connect_database()) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    email TEXT,
                    phone_number TEXT,
                    created_at TEXT,
                    last_login_at TEXT,
                    last_logout_at TEXT
                )
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
            for column in (
                "email",
                "phone_number",
                "created_at",
                "last_login_at",
                "last_logout_at",
                "role",
                "is_locked",
                "session_version",
            ):
                if column not in columns and column in {
                    "email",
                    "phone_number",
                    "created_at",
                    "last_login_at",
                    "last_logout_at",
                }:
                    connection.execute(f"ALTER TABLE users ADD COLUMN {column} TEXT")
            if "role" not in columns:
                connection.execute(
                    "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'User'"
                )
            if "is_locked" not in columns:
                connection.execute(
                    "ALTER TABLE users ADD COLUMN is_locked INTEGER NOT NULL DEFAULT 0"
                )
            if "session_version" not in columns:
                connection.execute(
                    "ALTER TABLE users ADD COLUMN session_version INTEGER NOT NULL DEFAULT 0"
                )
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS users_email_unique "
                "ON users(email COLLATE NOCASE) WHERE email IS NOT NULL"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    details TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                )
                """
            )
            audit_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(audit_events)")
            }
            if "details" not in audit_columns:
                connection.execute("ALTER TABLE audit_events ADD COLUMN details TEXT")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount_cents INTEGER NOT NULL CHECK (amount_cents != 0),
                    description TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS transactions_user_history
                ON transactions(user_id, occurred_at DESC, id DESC)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS password_reset_user_created
                ON password_reset_tokens(user_id, created_at)
                """
            )

            existing_users = connection.execute("SELECT id FROM users").fetchall()
            for (user_id,) in existing_users:
                seed_demo_transactions(connection, user_id)

            admin_username = os.environ.get("FAMILY_BANK_ADMIN_USERNAME", "").strip()
            has_admin = connection.execute(
                "SELECT 1 FROM users WHERE role = 'Admin' LIMIT 1"
            ).fetchone()
            if admin_username and not has_admin:
                connection.execute(
                    "UPDATE users SET role = 'Admin' WHERE username = ? COLLATE NOCASE",
                    (admin_username,),
                )


def connect_database():
    connection = sqlite3.connect(DATABASE)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def record_audit_event(connection, event_type, user_id=None, details=None):
    connection.execute(
        """
        INSERT INTO audit_events (user_id, event_type, occurred_at, details)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, event_type, utc_timestamp(), details),
    )


def utc_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def format_demo_amount(amount_cents):
    sign = "-" if amount_cents < 0 else ""
    dollars, cents = divmod(abs(amount_cents), 100)
    return f"{sign}${dollars:,}.{cents:02d}"


def seed_demo_transactions(connection, user_id):
    already_seeded = connection.execute(
        "SELECT 1 FROM transactions WHERE user_id = ? LIMIT 1",
        (user_id,),
    ).fetchone()
    if already_seeded:
        return

    now = datetime.now(timezone.utc)
    examples = (
        (250000, "Demo opening balance", now - timedelta(days=4)),
        (-4200, "Sample cafe purchase", now - timedelta(days=2)),
        (12500, "Sample demo deposit", now - timedelta(days=1)),
    )
    connection.executemany(
        """
        INSERT INTO transactions (user_id, amount_cents, description, occurred_at)
        VALUES (?, ?, ?, ?)
        """,
        [
            (user_id, amount_cents, description, occurred_at.isoformat(timespec="seconds"))
            for amount_cents, description, occurred_at in examples
        ],
    )


def reset_email_configuration():
    required = ("SMTP_HOST", "SMTP_FROM", "PUBLIC_BASE_URL")
    missing = [name for name in required if not os.environ.get(name, "").strip()]
    if missing:
        raise RuntimeError(
            "Password reset email is not configured; missing " + ", ".join(missing)
        )

    base_url = os.environ["PUBLIC_BASE_URL"].strip().rstrip("/")
    parsed_url = urlsplit(base_url)
    is_loopback = parsed_url.hostname in {"localhost", "127.0.0.1", "::1"}
    if (
        not parsed_url.hostname
        or parsed_url.username
        or parsed_url.password
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise RuntimeError("PUBLIC_BASE_URL must be a valid base URL without credentials.")
    if parsed_url.scheme != "https" and not is_loopback:
        raise RuntimeError("PUBLIC_BASE_URL must use HTTPS for non-local hosts.")

    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError as error:
        raise RuntimeError("SMTP_PORT must be a valid port number.") from error
    if not 1 <= port <= 65535:
        raise RuntimeError("SMTP_PORT must be between 1 and 65535.")
    return base_url, port


def send_password_reset_email(email, token):
    base_url, port = reset_email_configuration()
    host = os.environ["SMTP_HOST"].strip()
    sender = os.environ["SMTP_FROM"].strip()
    reset_url = (
        f"{base_url}{url_for('reset_password', token=token)}"
    )

    message = EmailMessage()
    message["Subject"] = "Reset your Family Bank demo password"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        "A password reset was requested for your Family Bank learning demo.\n\n"
        f"Use this one-time link within 30 minutes:\n{reset_url}\n\n"
        "If you did not request this, you can ignore this email. "
        "This is a fictional learning demo, not a real bank."
    )

    username = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    security = os.environ.get("SMTP_SECURITY", "starttls").strip().lower()
    context = ssl.create_default_context()
    if security == "ssl":
        with smtplib.SMTP_SSL(host, port, timeout=10, context=context) as server:
            if username:
                server.login(username, password)
            server.send_message(message)
    elif security == "starttls":
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls(context=context)
            if username:
                server.login(username, password)
            server.send_message(message)
    else:
        raise RuntimeError("SMTP_SECURITY must be either 'starttls' or 'ssl'.")


def create_database_backup():
    BACKUP_DIRECTORY.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = BACKUP_DIRECTORY / (
        f"family-bank-demo-{timestamp}-{secrets.token_hex(4)}.sqlite3"
    )
    with closing(connect_database()) as source, closing(
        sqlite3.connect(backup_path)
    ) as destination:
        source.backup(destination)
    return backup_path


def validate_restore_database(path):
    with closing(sqlite3.connect(path)) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if integrity is None or integrity[0] != "ok":
            raise ValueError("The uploaded SQLite database failed its integrity check.")

        required_tables = {
            "users",
            "audit_events",
            "transactions",
            "password_reset_tokens",
        }
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if not required_tables.issubset(table_names):
            raise ValueError("The SQLite file is missing required demo database tables.")

        required_columns = {
            "users": {
                "id",
                "username",
                "password_hash",
                "email",
                "phone_number",
                "created_at",
                "last_login_at",
                "last_logout_at",
                "role",
                "is_locked",
                "session_version",
            },
            "audit_events": {"id", "user_id", "event_type", "occurred_at", "details"},
            "transactions": {"id", "user_id", "amount_cents", "description", "occurred_at"},
            "password_reset_tokens": {
                "id",
                "user_id",
                "token_hash",
                "created_at",
                "expires_at",
            },
        }
        for table, expected_columns in required_columns.items():
            columns = {
                row[1] for row in connection.execute(f"PRAGMA table_info({table})")
            }
            if not expected_columns.issubset(columns):
                raise ValueError(f"The SQLite {table} table has an unsupported schema.")

        active_admin_count = connection.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'Admin' AND is_locked = 0"
        ).fetchone()[0]
        if active_admin_count < 1:
            raise ValueError("The SQLite database must contain an active demo admin.")
        invalid_roles = connection.execute(
            """
            SELECT 1 FROM users
            WHERE role NOT IN ('Admin', 'Technician', 'User')
            LIMIT 1
            """
        ).fetchone()
        if invalid_roles is not None:
            raise ValueError("The SQLite database contains an unsupported user role.")

        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise ValueError("The SQLite database contains invalid foreign-key records.")


def create_account_export():
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        ("username", "role", "account_status", "demo_balance", "transaction_count")
    )
    with closing(connect_database()) as connection:
        users = connection.execute(
            """
                SELECT users.username, users.role, users.is_locked,
                   COALESCE(SUM(transactions.amount_cents), 0),
                   COUNT(transactions.id)
            FROM users
            LEFT JOIN transactions ON transactions.user_id = users.id
            GROUP BY users.id
            ORDER BY users.username COLLATE NOCASE
            """
        )
        for username, role, is_locked, balance, transaction_count in users:
            writer.writerow(
                (
                    username,
                    role,
                    "Locked" if is_locked else "Active",
                    format_demo_amount(balance),
                    transaction_count,
                )
            )
    return output.getvalue()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "info")
            return redirect(url_for("login"))
        with closing(connect_database()) as connection:
            connection.row_factory = sqlite3.Row
            user = connection.execute(
                """
                SELECT id, username, role, is_locked, session_version
                FROM users WHERE id = ?
                """,
                (session["user_id"],),
            ).fetchone()
        if user is None or user["is_locked"]:
            session.clear()
            flash("This account is unavailable. Contact the demo administrator.", "error")
            return redirect(url_for("login"))
        if session.get("session_version") != user["session_version"]:
            session.clear()
            flash("Your session has expired. Please sign in again.", "info")
            return redirect(url_for("login"))
        g.current_user = user
        return view(**kwargs)

    return wrapped_view


def role_required(*allowed_roles):
    def decorate(view):
        @wraps(view)
        @login_required
        def wrapped_view(**kwargs):
            if g.current_user["role"] not in allowed_roles:
                abort(403)
            return view(**kwargs)

        return wrapped_view

    return decorate


admin_required = role_required("Admin")


def csrf_token_is_valid():
    submitted_token = request.form.get("csrf_token", "")
    session_token = session.get("_csrf_token", "")
    return bool(session_token) and secrets.compare_digest(submitted_token, session_token)


@app.context_processor
def provide_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)
    return {
        "csrf_token": session["_csrf_token"],
        "format_demo_amount": format_demo_amount,
    }


@app.route("/")
def home():
    # The shared static page stays untouched; only this local copy gets the real sign-in link.
    page = (Path(app.root_path) / "docs" / "index.html").read_text(encoding="utf-8")
    menu_item = '<li><a href="#login">Sign-in design</a></li>'
    page = page.replace(
        menu_item,
        menu_item + '\n                <li><a href="/login">Sign in</a></li>',
        1,
    )
    return Response(page, mimetype="text/html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not csrf_token_is_valid():
            flash("Your form expired. Please try again.", "error")
            return redirect(url_for("register"))

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        phone_number = request.form.get("phone_number", "").strip()
        password = request.form.get("password", "")

        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
            flash("Username must be 3–32 characters: letters, numbers, ., _ or -.", "error")
            return render_template("register.html")
        configured_admin = os.environ.get("FAMILY_BANK_ADMIN_USERNAME", "").strip()
        if configured_admin and username.casefold() == configured_admin.casefold():
            flash("That username is reserved for the configured demo administrator.", "error")
            return render_template("register.html")
        if (
            len(email) > 254
            or not re.fullmatch(r"[^@\s]{1,64}@[^@\s.]+(?:\.[^@\s.]+)+", email)
        ):
            flash("Enter a valid email address.", "error")
            return render_template("register.html")
        phone_digits = re.sub(r"[^0-9]", "", phone_number)
        if (
            not re.fullmatch(r"\+?[0-9][0-9()\s.-]{5,24}", phone_number)
            or not 7 <= len(phone_digits) <= 15
        ):
            flash("Enter a valid phone number with 7–15 digits.", "error")
            return render_template("register.html")
        if not 12 <= len(password) <= 128:
            flash("Password must be between 12 and 128 characters.", "error")
            return render_template("register.html")

        password_hash = generate_password_hash(password)
        try:
            with closing(connect_database()) as connection:
                with connection:
                    cursor = connection.execute(
                        """
                        INSERT INTO users (
                            username, password_hash, email, phone_number, created_at
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (username, password_hash, email, phone_number, utc_timestamp()),
                    )
                    user_id = cursor.lastrowid
                    seed_demo_transactions(connection, user_id)
                    record_audit_event(connection, "account_registered", user_id)
        except sqlite3.IntegrityError:
            flash("We couldn't create that account. Please try different details.", "error")
            return render_template("register.html")

        session.clear()
        session["user_id"] = user_id
        session["username"] = username
        session["session_version"] = 0
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if not csrf_token_is_valid():
            flash("Your form expired. Please try again.", "error")
            return redirect(url_for("login"))

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with closing(connect_database()) as connection:
            connection.row_factory = sqlite3.Row
            user = connection.execute(
                """
                SELECT id, username, password_hash, role, is_locked, session_version
                FROM users WHERE username = ?
                """,
                (username,),
            ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            with closing(connect_database()) as connection:
                with connection:
                    record_audit_event(
                        connection,
                        "sign_in_failed",
                        user["id"] if user is not None else None,
                    )
            flash("Username or password is incorrect.", "error")
            return render_template("login.html")

        if user["is_locked"]:
            with closing(connect_database()) as connection:
                with connection:
                    record_audit_event(
                        connection,
                        "locked_account_sign_in_attempt",
                        user["id"],
                    )
            flash("Username or password is incorrect.", "error")
            return render_template("login.html")

        with closing(connect_database()) as connection:
            with connection:
                connection.execute(
                    "UPDATE users SET last_login_at = ? WHERE id = ?",
                    (utc_timestamp(), user["id"]),
                )
                record_audit_event(connection, "sign_in_succeeded", user["id"])

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["session_version"] = user["session_version"]
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    with closing(connect_database()) as connection:
        connection.row_factory = sqlite3.Row
        balance_cents = connection.execute(
            """
            SELECT COALESCE(SUM(amount_cents), 0)
            FROM transactions WHERE user_id = ?
            """,
            (g.current_user["id"],),
        ).fetchone()[0]
        transactions = connection.execute(
            """
            SELECT description, amount_cents, occurred_at
            FROM transactions
            WHERE user_id = ?
            ORDER BY occurred_at DESC, id DESC
            LIMIT 50
            """,
            (g.current_user["id"],),
        ).fetchall()

    return render_template(
        "dashboard.html",
        username=session["username"],
        role=g.current_user["role"],
        balance=format_demo_amount(balance_cents),
        transactions=transactions,
    )


@app.route("/transactions")
@login_required
def transaction_history():
    page_size = 25
    try:
        requested_page = int(request.args.get("page", "1"))
    except ValueError:
        abort(400)

    with closing(connect_database()) as connection:
        connection.row_factory = sqlite3.Row
        total_count = connection.execute(
            "SELECT COUNT(*) FROM transactions WHERE user_id = ?",
            (g.current_user["id"],),
        ).fetchone()[0]
        page_count = (total_count + page_size - 1) // page_size
        page = min(max(requested_page, 1), max(page_count, 1))
        transactions = connection.execute(
            """
            SELECT description, amount_cents, occurred_at
            FROM transactions
            WHERE user_id = ?
            ORDER BY occurred_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (g.current_user["id"], page_size, (page - 1) * page_size),
        ).fetchall()

    return render_template(
        "transaction_history.html",
        transactions=transactions,
        page=page,
        page_count=page_count,
        total_count=total_count,
    )


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        if not csrf_token_is_valid():
            flash("Your form expired. Please try again.", "error")
            return redirect(url_for("forgot_password"))

        email = request.form.get("email", "").strip()
        if len(email) > 254:
            flash("Enter a valid email address.", "error")
            return render_template("forgot_password.html")

        reset_token = None
        user_id = None
        with closing(connect_database()) as connection:
            connection.row_factory = sqlite3.Row
            with connection:
                connection.execute(
                    "DELETE FROM password_reset_tokens WHERE expires_at <= ?",
                    (utc_timestamp(),),
                )
                user = connection.execute(
                    """
                    SELECT id, email FROM users
                    WHERE email = ? COLLATE NOCASE AND is_locked = 0
                    """,
                    (email,),
                ).fetchone()
                if user is not None and user["email"]:
                    recently_requested = connection.execute(
                        """
                        SELECT 1 FROM password_reset_tokens
                        WHERE user_id = ? AND created_at > ?
                        LIMIT 1
                        """,
                        (
                            user["id"],
                            (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(
                                timespec="seconds"
                            ),
                        ),
                    ).fetchone()
                    if recently_requested is None:
                        reset_token = secrets.token_urlsafe(32)
                        user_id = user["id"]
                        now = datetime.now(timezone.utc)
                        connection.execute(
                            """
                            INSERT INTO password_reset_tokens (
                                user_id, token_hash, created_at, expires_at
                            )
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                user_id,
                                hashlib.sha256(reset_token.encode("utf-8")).hexdigest(),
                                now.isoformat(timespec="seconds"),
                                (now + timedelta(minutes=30)).isoformat(timespec="seconds"),
                            ),
                        )
                        record_audit_event(
                            connection,
                            "password_reset_requested",
                            user_id,
                        )

        if reset_token is not None:
            try:
                send_password_reset_email(email, reset_token)
            except (OSError, smtplib.SMTPException, RuntimeError, ValueError) as error:
                with closing(connect_database()) as connection:
                    with connection:
                        connection.execute(
                            "DELETE FROM password_reset_tokens WHERE token_hash = ?",
                            (
                                hashlib.sha256(
                                    reset_token.encode("utf-8")
                                ).hexdigest(),
                            ),
                        )
                        record_audit_event(
                            connection,
                            "password_reset_email_failed",
                            user_id,
                        )
                app.logger.error(
                    "Password reset email delivery failed (%s).",
                    type(error).__name__,
                )
                flash(
                    "The reset email could not be sent. Check the local SMTP settings "
                    "and try again later.",
                    "error",
                )
                return render_template("forgot_password.html")

        flash(
            "If an active account uses that email address, a reset link will be sent.",
            "info",
        )
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = utc_timestamp()

    with closing(connect_database()) as connection:
        connection.row_factory = sqlite3.Row
        token_row = connection.execute(
            """
            SELECT user_id FROM password_reset_tokens
            WHERE token_hash = ? AND expires_at > ?
            """,
            (token_hash, now),
        ).fetchone()

    if token_row is None:
        flash("That reset link is invalid or expired. Request a new link.", "error")
        return redirect(url_for("forgot_password"))

    if request.method == "GET":
        return render_template("reset_password.html", token=token)

    if not csrf_token_is_valid():
        flash("Your form expired. Please try again.", "error")
        return redirect(url_for("reset_password", token=token))

    password = request.form.get("password", "")
    confirmation = request.form.get("confirm_password", "")
    if not 12 <= len(password) <= 128 or password != confirmation:
        flash("Passwords must match and be between 12 and 128 characters.", "error")
        return render_template("reset_password.html", token=token)

    with closing(connect_database()) as connection:
        with connection:
            cursor = connection.execute(
                """
                DELETE FROM password_reset_tokens
                WHERE token_hash = ? AND expires_at > ?
                """,
                (token_hash, utc_timestamp()),
            )
            if cursor.rowcount != 1:
                flash("That reset link is invalid or expired. Request a new link.", "error")
                return redirect(url_for("forgot_password"))

            connection.execute(
                """
                UPDATE users
                SET password_hash = ?, session_version = session_version + 1
                WHERE id = ?
                """,
                (generate_password_hash(password), token_row["user_id"]),
            )
            record_audit_event(
                connection,
                "account_password_reset",
                token_row["user_id"],
            )

    flash("Your demo password has been updated. Please sign in.", "info")
    return redirect(url_for("login"))


@app.route("/technician/activity")
@role_required("Admin", "Technician")
def technician_activity():
    with closing(connect_database()) as connection:
        connection.row_factory = sqlite3.Row
        events = connection.execute(
            """
            SELECT event_type, occurred_at
            FROM audit_events
            ORDER BY id DESC
            LIMIT 100
            """
        ).fetchall()

    return render_template("technician_activity.html", events=events)


@app.route("/admin")
@admin_required
def admin():
    with closing(connect_database()) as connection:
        connection.row_factory = sqlite3.Row
        users = connection.execute(
            """
            SELECT id, username, email, phone_number, created_at, last_login_at,
                   last_logout_at, role, is_locked
            FROM users
            ORDER BY username COLLATE NOCASE
            """
        ).fetchall()
        audit_events = connection.execute(
            """
            SELECT audit_events.event_type, audit_events.occurred_at,
                   audit_events.details, users.username
            FROM audit_events
            LEFT JOIN users ON users.id = audit_events.user_id
            ORDER BY audit_events.id DESC
            LIMIT 100
            """
        ).fetchall()

    return render_template(
        "admin_users.html",
        users=users,
        email_count=sum(bool(user["email"]) for user in users),
        phone_count=sum(bool(user["phone_number"]) for user in users),
        audit_events=audit_events,
        current_user_id=g.current_user["id"],
    )


@app.route("/admin/database/export.csv")
@admin_required
def admin_database_export():
    return Response(
        create_account_export(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="family-bank-demo-accounts.csv"'
        },
    )


@app.route("/admin/database/backup", methods=["POST"])
@admin_required
def admin_database_backup():
    if not admin_form_is_valid():
        return redirect(url_for("admin"))
    backup_path = create_database_backup()
    return send_file(
        backup_path,
        as_attachment=True,
        download_name=backup_path.name,
        mimetype="application/vnd.sqlite3",
    )


@app.route("/admin/database/restore", methods=["POST"])
@admin_required
def admin_database_restore():
    if not admin_form_is_valid():
        return redirect(url_for("admin"))

    uploaded_file = request.files.get("backup_file")
    if uploaded_file is None or not uploaded_file.filename:
        flash("Choose a SQLite backup file to restore.", "error")
        return redirect(url_for("admin"))

    temporary_file = tempfile.NamedTemporaryFile(
        prefix="restore-",
        suffix=".sqlite3",
        dir=app.instance_path,
        delete=False,
    )
    temporary_path = Path(temporary_file.name)
    temporary_file.close()
    try:
        uploaded_file.save(temporary_path)
        validate_restore_database(temporary_path)
        recovery_backup = create_database_backup()
        os.replace(temporary_path, DATABASE)
    except (OSError, sqlite3.DatabaseError, ValueError) as error:
        app.logger.error(
            "SQLite restore failed (%s).",
            type(error).__name__,
        )
        flash(
            "The database was not restored. The file is invalid or could not be installed.",
            "error",
        )
        return redirect(url_for("admin"))
    finally:
        temporary_path.unlink(missing_ok=True)

    flash(
        f"Database restored. A safety backup was saved as {recovery_backup.name}.",
        "info",
    )
    return redirect(url_for("admin"))


def admin_form_is_valid():
    if csrf_token_is_valid():
        return True
    flash("Your form expired. Please try again.", "error")
    return False


def get_user_or_404(connection, user_id):
    connection.row_factory = sqlite3.Row
    user = connection.execute(
        "SELECT id, username, role, is_locked FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if user is None:
        abort(404)
    return user


def active_admin_count(connection):
    return connection.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'Admin' AND is_locked = 0"
    ).fetchone()[0]


@app.route("/admin/users/<int:user_id>/lock", methods=["POST"])
@admin_required
def admin_toggle_lock(user_id):
    if not admin_form_is_valid():
        return redirect(url_for("admin"))

    with closing(connect_database()) as connection:
        with connection:
            user = get_user_or_404(connection, user_id)
            if user["id"] == g.current_user["id"]:
                flash("You cannot lock your own admin account.", "error")
                return redirect(url_for("admin"))
            if (
                not user["is_locked"]
                and user["role"] == "Admin"
                and active_admin_count(connection) <= 1
            ):
                flash("The last active admin account cannot be locked.", "error")
                return redirect(url_for("admin"))

            new_lock_state = 0 if user["is_locked"] else 1
            connection.execute(
                """
                UPDATE users
                SET is_locked = ?, session_version = session_version + 1
                WHERE id = ?
                """,
                (new_lock_state, user_id),
            )
            if new_lock_state:
                connection.execute(
                    "DELETE FROM password_reset_tokens WHERE user_id = ?",
                    (user_id,),
                )
            record_audit_event(
                connection,
                "account_locked" if new_lock_state else "account_unlocked",
                g.current_user["id"],
                user["username"],
            )

    flash(
        f"Account {user['username']} {'locked' if new_lock_state else 'unlocked'}.",
        "info",
    )
    return redirect(url_for("admin"))


@app.route("/admin/users/<int:user_id>/role", methods=["POST"])
@admin_required
def admin_update_role(user_id):
    if not admin_form_is_valid():
        return redirect(url_for("admin"))

    new_role = request.form.get("role", "")
    if new_role not in {"Admin", "Technician", "User"}:
        abort(400)

    with closing(connect_database()) as connection:
        with connection:
            user = get_user_or_404(connection, user_id)
            if user["id"] == g.current_user["id"] and new_role != "Admin":
                flash("You cannot remove your own admin role.", "error")
                return redirect(url_for("admin"))
            if (
                user["role"] == "Admin"
                and new_role != "Admin"
                and not user["is_locked"]
                and active_admin_count(connection) <= 1
            ):
                flash("The last active admin role cannot be removed.", "error")
                return redirect(url_for("admin"))
            if user["role"] != new_role:
                connection.execute(
                    """
                    UPDATE users SET role = ?, session_version = session_version + 1
                    WHERE id = ?
                    """,
                    (new_role, user_id),
                )
                record_audit_event(
                    connection,
                    "account_role_changed",
                    g.current_user["id"],
                    f"{user['username']}: {user['role']} to {new_role}",
                )

    flash(f"Updated {user['username']} role to {new_role}.", "info")
    return redirect(url_for("admin"))


@app.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
@admin_required
def admin_reset_password(user_id):
    if not admin_form_is_valid():
        return redirect(url_for("admin"))

    password = request.form.get("password", "")
    confirmation = request.form.get("confirm_password", "")
    if not 12 <= len(password) <= 128 or password != confirmation:
        flash("Passwords must match and be between 12 and 128 characters.", "error")
        return redirect(url_for("admin"))

    with closing(connect_database()) as connection:
        with connection:
            user = get_user_or_404(connection, user_id)
            connection.execute(
                """
                UPDATE users
                SET password_hash = ?, session_version = session_version + 1
                WHERE id = ?
                """,
                (generate_password_hash(password), user_id),
            )
            connection.execute(
                "DELETE FROM password_reset_tokens WHERE user_id = ?",
                (user_id,),
            )
            record_audit_event(
                connection,
                "account_password_reset",
                g.current_user["id"],
                user["username"],
            )

    flash(f"Password reset for {user['username']}. They must sign in again.", "info")
    return redirect(url_for("admin"))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_account(user_id):
    if not admin_form_is_valid():
        return redirect(url_for("admin"))

    with closing(connect_database()) as connection:
        with connection:
            user = get_user_or_404(connection, user_id)
            if user["id"] == g.current_user["id"]:
                flash("You cannot delete your own admin account.", "error")
                return redirect(url_for("admin"))
            if request.form.get("confirm_username", "").strip().casefold() != user[
                "username"
            ].casefold():
                flash("Type the account username exactly to confirm deletion.", "error")
                return redirect(url_for("admin"))
            if (
                user["role"] == "Admin"
                and not user["is_locked"]
                and active_admin_count(connection) <= 1
            ):
                flash("The last admin account cannot be deleted.", "error")
                return redirect(url_for("admin"))

            record_audit_event(
                connection,
                "account_deleted",
                g.current_user["id"],
                user["username"],
            )
            connection.execute("DELETE FROM users WHERE id = ?", (user_id,))

    flash(f"Deleted account {user['username']}.", "info")
    return redirect(url_for("admin"))


@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    if request.method == "GET":
        return redirect(url_for("dashboard"))

    if not csrf_token_is_valid():
        flash("Your form expired. Please try again.", "error")
        return redirect(url_for("dashboard"))

    with closing(connect_database()) as connection:
        with connection:
            connection.execute(
                "UPDATE users SET last_logout_at = ? WHERE id = ?",
                (utc_timestamp(), session["user_id"]),
            )
            record_audit_event(connection, "signed_out", session["user_id"])

    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("login"))


initialize_database()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
