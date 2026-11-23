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


EARLY_LESSONS = [
    {
        "number": "01",
        "title": "Colors around us",
        "focus": "Words and noticing",
        "accessibility": "Use high-contrast objects; looking, reaching, or a gesture can be an answer instead of naming a color.",
        "materials": [
            "A sturdy board book or large picture with clear colors.",
            "Two large, intact, age-appropriate soft toys in different colors.",
        ],
        "steps": [
            "Name the color of one object, then pause so the child can look or gesture.",
            "Offer the second object and say its color in a short, friendly phrase.",
            "Repeat the words together during a brief read-aloud; stop when the child needs a break.",
        ],
        "quiz": {
            "question": "Which object is blue?",
            "choices": ["The blue soft toy", "The red book"],
            "correct_choice": "The blue soft toy",
            "answer": "The blue soft toy. If the child is unsure, point to it and say the color together.",
        },
    },
    {
        "number": "02",
        "title": "Count with claps",
        "focus": "Early number sense",
        "accessibility": "Count with gentle taps or a visual cue; the child can listen instead of clapping.",
        "materials": [
            "A comfortable place to sit or stand together.",
            "Your hands; no loose counters or small objects are needed.",
        ],
        "steps": [
            "Clap once gently and say, “One clap.”",
            "Try two slow claps, counting each one aloud.",
            "Invite the child to clap, tap knees, or simply listen.",
        ],
        "quiz": {
            "question": "How many claps did we try first?",
            "choices": ["One", "Ten"],
            "correct_choice": "One",
            "answer": "One. Count again together; a look, sound, or movement is a response.",
        },
    },
    {
        "number": "03",
        "title": "Shapes all around",
        "focus": "Looking and comparing",
        "accessibility": "Use large, high-contrast pictures and trace shapes in the air rather than requiring a grasp.",
        "materials": [
            "A sturdy picture book or large picture showing simple shapes.",
            "One large, safe household object with a clear round or square shape.",
        ],
        "steps": [
            "Look at a circle and a square in a picture.",
            "Trace each shape in the air with your finger while naming it.",
            "Find a similar shape in the room without picking up anything unsafe.",
        ],
        "quiz": {
            "question": "Which shape has a round edge?",
            "choices": ["A circle", "A square"],
            "correct_choice": "A circle",
            "answer": "A circle. Show it in the picture and trace it together.",
        },
    },
    {
        "number": "04",
        "title": "Storytime and new words",
        "focus": "Language and connection",
        "accessibility": "Pause for speech, signs, eye gaze, AAC, or quiet listening; one picture at a time is enough.",
        "materials": [
            "A sturdy board book chosen by the child.",
            "A cozy, safe place to read together.",
        ],
        "steps": [
            "Let the child look at or choose a page.",
            "Name one picture and add a few simple words, such as “big, yellow bus.”",
            "Pause for pointing, sounds, gestures, device-based communication, or a quiet look.",
        ],
        "quiz": {
            "question": "What can we do when we see a picture?",
            "choices": ["Point to it and talk about it", "Rush to finish the book"],
            "correct_choice": "Point to it and talk about it",
            "answer": "Point to it and talk about it. Follow the child's interest and enjoy the moment.",
        },
    },
    {
        "number": "05",
        "title": "Feelings and kindness",
        "focus": "Social and emotional learning",
        "accessibility": "Use simple words or pictures; never require eye contact, facial imitation, or touch.",
        "materials": [
            "A board book about feelings or familiar faces.",
            "A trusted adult who can model a kind response.",
        ],
        "steps": [
            "Look at a face in a book and name one feeling, such as happy or sad.",
            "Model a gentle response: “Would you like help?” or “Let's ask a grown-up.”",
            "Let the child answer in their own way; never require a hug or touch.",
        ],
        "quiz": {
            "question": "If someone seems upset, what is a kind next step?",
            "choices": ["Ask if they want help or tell a trusted adult", "Take their toy"],
            "correct_choice": "Ask if they want help or tell a trusted adult",
            "answer": "Ask if they want help or tell a trusted adult. Respect the other person's space.",
        },
    },
    {
        "number": "06",
        "title": "Notice nature",
        "focus": "Observation and curiosity",
        "accessibility": "A window view is a comfortable alternative to going outside; adjust light and sound to the child.",
        "materials": [
            "A window view or a safe outdoor spot with an adult.",
            "Weather-appropriate clothing if you go outside.",
        ],
        "steps": [
            "Look for the sun, clouds, or moving leaves from a safe place.",
            "Use simple words to describe what you notice: “bright,” “windy,” or “cloudy.”",
            "If you go outdoors, stay close to the child and leave plants and objects where they are.",
        ],
        "quiz": {
            "question": "Who stays close during an outdoor walk?",
            "choices": ["A trusted grown-up", "No one"],
            "correct_choice": "A trusted grown-up",
            "answer": "A trusted grown-up stays close. Explore only in a safe, supervised place.",
        },
    },
    {
        "number": "07",
        "title": "What is a computer?",
        "focus": "Technology basics, unplugged",
        "accessibility": "Give one step at a time; the grown-up can model the movement while the child watches.",
        "materials": [
            "Your hands and voices for a pretend instruction game.",
            "No computer or screen is needed.",
        ],
        "steps": [
            "Explain simply: “A computer is a tool that follows instructions.”",
            "Give the grown-up two playful steps, such as “wave, then clap,” and let the grown-up follow them.",
            "Switch roles only if the child wants; keep the game silly and brief.",
        ],
        "quiz": {
            "question": "What helps a computer do a task?",
            "choices": ["Clear instructions", "A computer guessing what we mean"],
            "correct_choice": "Clear instructions",
            "answer": "Clear instructions. A grown-up can help explain and check what a computer does.",
        },
    },
    {
        "number": "08",
        "title": "Cyber safety: stop and ask",
        "focus": "Safe technology habits",
        "accessibility": "Practice “ask first” with speech, a sign, pointing, or the child's usual communication system.",
        "materials": [
            "A trusted grown-up to role-play with.",
            "No real device, website, password, or personal information is needed.",
        ],
        "steps": [
            "Pretend a new button appears; the child practices pausing.",
            "Model saying, “I will ask my grown-up first.”",
            "Remind the child that grown-ups decide which devices and apps are okay to use.",
        ],
        "quiz": {
            "question": "A new button appears on a device. What should the child do?",
            "choices": ["Ask a trusted grown-up first", "Tap it alone"],
            "correct_choice": "Ask a trusted grown-up first",
            "answer": "Ask a trusted grown-up first. Children this young should use devices only with an adult.",
        },
    },
    {
        "number": "09",
        "title": "Meet AI: a computer helper",
        "focus": "AI ideas, unplugged",
        "accessibility": "Use two familiar, high-contrast pictures; the child can watch while the grown-up describes them.",
        "materials": [
            "Two large, safe picture cards or soft toys that an adult can hold.",
            "No AI app, internet connection, or screen is needed.",
        ],
        "steps": [
            "Sort two pictures together by a visible feature, such as animal versus vehicle.",
            "Explain: “Some computer tools look for patterns and make a guess.”",
            "Say that AI is a tool, not a person, and it can be wrong; a grown-up checks it.",
        ],
        "quiz": {
            "question": "Can an AI computer helper make a mistake?",
            "choices": ["Yes; a grown-up checks", "No; it is always right"],
            "correct_choice": "Yes; a grown-up checks",
            "answer": "Yes. AI can make mistakes, so a trusted grown-up checks important information.",
        },
    },
    {
        "number": "10",
        "title": "Create a safe little story",
        "focus": "Creativity and review",
        "accessibility": "Let the child choose by looking, gesturing, using AAC, or speaking; the grown-up can narrate.",
        "materials": [
            "A favorite board book or two large, age-appropriate toys.",
            "A trusted grown-up to tell the story with the child.",
        ],
        "steps": [
            "Let the child choose a toy or picture to start an imaginary story.",
            "Take turns adding one simple action or sound.",
            "Review the safe-tech habit: ask a grown-up before using a device or computer helper.",
        ],
        "quiz": {
            "question": "Who should help a young child use a computer or AI tool?",
            "choices": ["A trusted grown-up", "The child alone"],
            "correct_choice": "A trusted grown-up",
            "answer": "A trusted grown-up. Never share a child's name, photo, voice, or other private details with a tool.",
        },
    },
]


EARLY_BOOKS = [
    {
        "title": "Brown Bear, Brown Bear, What Do You See?",
        "author": "Bill Martin Jr.; illustrated by Eric Carle",
        "age": "Publisher age range: 2-5",
        "focus": "Repeated words, animals, and colors.",
        "url": "https://us.macmillan.com/books/9780805002010/brownbearbrownbearwhatdoyousee/",
    },
    {
        "title": "Baby Loves Coding!",
        "author": "Ruth Spiro; illustrated by Irene Chan",
        "age": "Publisher age range: 0-3",
        "focus": "Patterns, sequence, and step-by-step problem solving.",
        "url": "https://www.penguinrandomhouse.com/books/566615/baby-loves-coding-by-ruth-spiro-author-irene-chan-illustrator/",
    },
    {
        "title": "Baby Loves Meteorology",
        "author": "Ruth Spiro; illustrated by Kat Uno",
        "age": "Publisher age range: 0-3",
        "focus": "Weather words and noticing the world.",
        "url": "https://www.penguinrandomhouse.com/books/762947/baby-loves-meteorology-by-ruth-spiro-author-kat-uno-illustrator/",
    },
    {
        "title": "Artificial Intelligence for Babies",
        "author": "Chris Ferrie",
        "age": "A board-book introduction; share with an adult.",
        "focus": "An early, simple introduction to AI ideas.",
        "url": "https://www.penguin.co.nz/books/artificial-intelligence-for-babies-9781464221453",
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
    return render_template(
        "early_learning.html",
        user=user,
        lessons=EARLY_LESSONS,
        books=EARLY_BOOKS,
    )


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
