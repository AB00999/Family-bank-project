# Study Hub

A local Flask learning dashboard for organizing subjects, goals, flashcards, and study sessions.

Study Hub also includes a public Early Learners course with ten short, caregiver-led lessons for children from birth to age 3. It includes read-aloud quizzes, book suggestions, age adaptations, screen-free computer, cyber safety, and AI activities, plus accessibility tips and print-friendly lesson cards. It does not require an account or collect child information.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open `http://127.0.0.1:5000`.

This project stores local demo data in `study_hub.sqlite3`.
