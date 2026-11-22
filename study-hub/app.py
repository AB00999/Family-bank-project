import sqlite3
from contextlib import contextmanager
from datetime import date
import os
import secrets
from pathlib import Path

from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("STUDY_HUB_SECRET_KEY") or secrets.token_hex(32)
DATABASE = Path(__file__).parent / "study_hub.sqlite3"


@contextmanager
def connect_database():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database():
    with connect_database() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                phone TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT '#4f46e5',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL,
                target_minutes INTEGER NOT NULL CHECK (target_minutes > 0),
                due_date TEXT,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                mastered INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_id INTEGER NOT NULL,
                minutes INTEGER NOT NULL CHECK (minutes >= 0),
                notes TEXT,
                occurred_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
            """
        )
        for table in ("subjects", "goals", "flashcards", "study_sessions"):
            columns = {
                row[1] for row in connection.execute(f"PRAGMA table_info({table})")
            }
            if "user_id" not in columns:
                connection.execute(
                    f"ALTER TABLE {table} ADD COLUMN user_id INTEGER"
                )


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with connect_database() as connection:
        return connection.execute(
            "SELECT id, name, email, phone FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        if len(name) < 2:
            flash("Enter your name.")
        elif "@" not in email or "." not in email:
            flash("Enter a valid email address.")
        elif len(phone) < 7:
            flash("Enter a valid phone number.")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.")
        else:
            with connect_database() as connection:
                existing = connection.execute(
                    "SELECT id FROM users WHERE email = ?",
                    (email,),
                ).fetchone()
                if existing:
                    flash("An account with this email already exists.")
                    return render_template("register.html")
                cursor = connection.execute(
                    "INSERT INTO users (name, email, phone, password_hash, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        name,
                        email,
                        phone,
                        generate_password_hash(password),
                        date.today().isoformat(),
                    ),
                )
                session["user_id"] = cursor.lastrowid
                session["user_name"] = name
            flash("Your account is ready.")
            return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with connect_database() as connection:
            user = connection.execute(
                "SELECT id, name, password_hash FROM users WHERE email = ?",
                (email,),
            ).fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Email or password is incorrect.")
        else:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash("Signed in successfully.")
            return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been signed out.")
    return redirect(url_for("login"))


GROWTH_GUIDES = [
    {
        "category": "Cybersecurity",
        "icon": "01",
        "title": "Start a career in cybersecurity",
        "summary": "Build practical skills in networking, operating systems, scripting, and security fundamentals.",
        "steps": [
            "Learn computer fundamentals, TCP/IP networking, Linux, Windows, and basic Python.",
            "Practice only in authorized labs such as TryHackMe, OverTheWire, Hack The Box Academy, or a controlled home lab.",
            "Build a portfolio with investigations, scripts, network diagrams, and clear lab reports.",
            "Target entry-level roles such as SOC analyst, help desk technician, NOC technician, IT support specialist, or security associate.",
            "Consider role-aligned credentials such as CompTIA A+, Network+, or Security+ after gaining practical experience.",
        ],
    },
    {
        "category": "Career",
        "icon": "02",
        "title": "Get a job with a criminal record",
        "summary": "Prepare an honest, skills-focused plan and seek employers and programs that consider people fairly.",
        "steps": [
            "Request an official copy of your record and check it for errors or outdated information.",
            "Ask a licensed attorney or verified local legal aid organization whether sealing or expungement may be available.",
            "Use a clear, truthful resume that emphasizes skills, certifications, recent training, experience, and references.",
            "Practice an honest, brief explanation: what happened, what changed, and the value you bring now.",
            "Search for fair-chance employers, workforce programs, apprenticeships, unions, and established reentry organizations.",
            "Answer application questions truthfully according to the applicable law and employer policy.",
        ],
    },
    {
        "category": "Money",
        "icon": "03",
        "title": "Build a bill and recovery plan",
        "summary": "Create a stable baseline before pursuing long-term goals.",
        "steps": [
            "List every bill, due date, minimum amount, and available balance.",
            "Pay housing, utilities, food, transportation, and court/child-support obligations before optional spending.",
            "Contact creditors early to request due-date changes or hardship payment plans.",
            "Use one weekly budget check and set aside a small emergency amount as soon as possible.",
            "Ask a reputable nonprofit credit counselor or benefits specialist for help with debt or public benefits.",
        ],
    },
    {
        "category": "Life decisions",
        "icon": "04",
        "title": "Make calmer, smarter choices",
        "summary": "Slow down decisions, identify consequences, and choose the next responsible step.",
        "steps": [
            "Write the decision, facts you know, facts you need, and people who may be affected.",
            "Separate short-term relief from long-term consequences.",
            "Use a trusted mentor, counselor, attorney, or community program for high-impact decisions.",
            "Choose reversible actions first and delay large commitments until you have verified information.",
            "Review the result honestly, keep what worked, and adjust what did not.",
        ],
    },
    {
        "category": "Personal growth",
        "icon": "05",
        "title": "Become more informed and disciplined",
        "summary": "Use consistent routines, verifiable knowledge, and measurable goals to improve every area of life.",
        "steps": [
            "Choose one skill goal, one health goal, one financial goal, and one relationship goal.",
            "Set a 30-minute daily minimum instead of relying on motivation.",
            "Keep records of practice, applications, appointments, payments, and progress.",
            "Learn from primary sources and verify important legal, medical, financial, or technical claims.",
            "Ask for feedback from people who have achieved the result you want.",
        ],
    },
]


@app.route("/knowledge")
@login_required
def knowledge():
    user = current_user()
    return render_template(
        "knowledge.html",
        user=user,
        guides=GROWTH_GUIDES,
    )


@app.route("/early-learning")
def early_learning():
    user = current_user()
    return render_template("early_learning.html", user=user)


@app.route("/")
@login_required
def dashboard():
    user = current_user()
    user_id = session["user_id"]
    with connect_database() as connection:
        subjects = connection.execute(
            "SELECT * FROM subjects WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        goals = connection.execute(
            "SELECT * FROM goals WHERE user_id = ? "
            "ORDER BY completed, due_date, created_at DESC",
            (user_id,),
        ).fetchall()
        cards = connection.execute(
            "SELECT flashcards.*, subjects.name AS subject_name "
            "FROM flashcards JOIN subjects ON subjects.id = flashcards.subject_id "
            "WHERE flashcards.mastered = 0 AND flashcards.user_id = ? "
            "ORDER BY flashcards.id DESC",
            (user_id,),
        ).fetchall()
        sessions = connection.execute(
            "SELECT study_sessions.*, subjects.name AS subject_name "
            "FROM study_sessions JOIN subjects ON subjects.id = study_sessions.subject_id "
            "WHERE study_sessions.user_id = ? "
            "ORDER BY study_sessions.occurred_at DESC LIMIT 8",
            (user_id,),
        ).fetchall()
        today_minutes = connection.execute(
            "SELECT COALESCE(SUM(minutes), 0) FROM study_sessions "
            "WHERE user_id = ? AND substr(occurred_at, 1, 10) = ?",
            (user_id, date.today().isoformat()),
        ).fetchone()[0]

    return render_template(
        "dashboard.html",
        subjects=subjects,
        goals=goals,
        cards=cards,
        sessions=sessions,
        today_minutes=today_minutes,
        user=user,
    )


@app.route("/subjects", methods=["POST"])
@login_required
def add_subject():
    name = request.form.get("name", "").strip()
    color = request.form.get("color", "#4f46e5").strip()
    if not name:
        flash("Add a subject name.")
        return redirect(url_for("dashboard"))

    with connect_database() as connection:
        connection.execute(
            "INSERT INTO subjects (user_id, name, color, created_at) VALUES (?, ?, ?, ?)",
            (session["user_id"], name, color, date.today().isoformat()),
        )
    flash(f"{name} added.")
    return redirect(url_for("dashboard"))


@app.route("/subjects/<int:subject_id>/delete", methods=["POST"])
@login_required
def delete_subject(subject_id):
    with connect_database() as connection:
        connection.execute(
            "DELETE FROM subjects WHERE id = ? AND user_id = ?",
            (subject_id, session["user_id"]),
        )
    flash("Subject deleted.")
    return redirect(url_for("dashboard"))


@app.route("/goals", methods=["POST"])
@login_required
def add_goal():
    title = request.form.get("title", "").strip()
    target_minutes = request.form.get("target_minutes", type=int)
    due_date = request.form.get("due_date", "").strip() or None
    if not title or not target_minutes or target_minutes <= 0:
        flash("Add a goal title and positive target.")
        return redirect(url_for("dashboard"))

    with connect_database() as connection:
        connection.execute(
            "INSERT INTO goals (user_id, title, target_minutes, due_date, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                session["user_id"],
                title,
                target_minutes,
                due_date,
                date.today().isoformat(),
            ),
        )
    flash("Goal added.")
    return redirect(url_for("dashboard"))


@app.route("/goals/<int:goal_id>/toggle", methods=["POST"])
@login_required
def toggle_goal(goal_id):
    with connect_database() as connection:
        connection.execute(
            "UPDATE goals SET completed = CASE completed WHEN 1 THEN 0 ELSE 1 END "
            "WHERE id = ? AND user_id = ?",
            (goal_id, session["user_id"]),
        )
    return redirect(url_for("dashboard"))


@app.route("/flashcards", methods=["POST"])
@login_required
def add_flashcard():
    subject_id = request.form.get("subject_id", type=int)
    question = request.form.get("question", "").strip()
    answer = request.form.get("answer", "").strip()
    if not subject_id or not question or not answer:
        flash("Choose a subject and add both a question and answer.")
        return redirect(url_for("dashboard"))

    with connect_database() as connection:
        connection.execute(
            "INSERT INTO flashcards (user_id, subject_id, question, answer, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                session["user_id"],
                subject_id,
                question,
                answer,
                date.today().isoformat(),
            ),
        )
    flash("Flashcard added.")
    return redirect(url_for("dashboard"))


@app.route("/flashcards/<int:card_id>/master", methods=["POST"])
@login_required
def master_flashcard(card_id):
    with connect_database() as connection:
        connection.execute(
            "UPDATE flashcards SET mastered = 1 WHERE id = ? AND user_id = ?",
            (card_id, session["user_id"]),
        )
    return redirect(url_for("dashboard"))


@app.route("/sessions", methods=["POST"])
@login_required
def add_session():
    subject_id = request.form.get("subject_id", type=int)
    minutes = request.form.get("minutes", type=int)
    notes = request.form.get("notes", "").strip()
    if not subject_id or minutes is None or minutes < 0:
        flash("Choose a subject and enter valid session minutes.")
        return redirect(url_for("dashboard"))

    with connect_database() as connection:
        connection.execute(
            "INSERT INTO study_sessions (user_id, subject_id, minutes, notes, occurred_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                session["user_id"],
                subject_id,
                minutes,
                notes,
                date.today().isoformat(),
            ),
        )
    flash("Study session logged.")
    return redirect(url_for("dashboard"))


initialize_database()


if __name__ == "__main__":
    app.run(debug=True)
