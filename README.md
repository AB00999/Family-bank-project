# Family project

## About

A fictional banking website concept and Python learning project.

## Projects

### Family Bank Website
- Homepage
- Flask sign-in and registration demo
- SQLite stores password hashes, never plaintext passwords
- Demo dashboard with clearly simulated balances and a paginated transaction history
- Optional one-time, expiring password-reset email through locally configured SMTP
- Admin-only SQLite backup, restore, and account CSV export

### ATM Simulator
- Menu loop for checking balance, depositing, withdrawing, or exiting
- Starts with a simulated $1,000 balance, then saves changes to a local `atm_balance.txt` file so the balance carries over between runs (delete the file to reset it)
- Deposits and withdrawals accept positive whole-dollar amounts written with plain digits; the demo balance is limited to $1,000,000
- Ctrl+C or Ctrl+Z exits politely

### Login Checker
- Standalone format-validation exercise; it does not authenticate users
- Usernames must be 3-20 ASCII letters, numbers, or underscores
- Passwords must be at least 8 characters and contain uppercase, lowercase, and numeric characters
- Allows up to three tries to enter values that meet those format rules
- Run with `python login_checker.py`; tests are included in the test suite

## Tools Used

- Python
- HTML
- CSS
- JavaScript
- Git
- GitHub
- VS Code
- Flask

## Dependency updates

Dependabot is configured in `.github/dependabot.yml` to check Python dependencies from `requirements.txt` weekly and open up to five version-update pull requests at a time. Review each pull request and run the project tests before merging. To receive security-update pull requests, enable Dependabot alerts and Dependabot security updates in the repository's **Settings → Code security and analysis** page on GitHub.

## Run the sign-in demo

Create a project virtual environment, install the dependencies, and run the local app from the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open `http://127.0.0.1:5000` to view the concept homepage and animated feature tour. The Flask demo account pages are at `/register` and `/login`; the SQLite database is created in the Flask `instance` folder.
Registration collects an email address and phone number and records account creation, successful sign-in, and sign-out times. Contact details are not verified. The protected `/admin` page shows usernames, contact details, and those timestamps in UTC; it never displays passwords or password hashes. Existing accounts are preserved during schema migration; metadata not collected previously appears as "Not recorded." Use made-up contact information only; this demo is not suitable for collecting real customers' personal data.
The admin page also shows the latest 100 security audit events (account creation, successful/failed sign-in, locked-account sign-in attempts, sign-out, lock/unlock, role changes, password resets, and deletions). Events do not store passwords or submitted login details.
Admin accounts can lock/unlock demo users, assign Admin/Technician/User roles, reset a demo password, and delete a user account. These actions require CSRF-protected POST requests; deletion requires typing the username. The current admin cannot lock or delete their own account, and the last active admin cannot be locked, demoted, or deleted. Locking, deleting, role changes, and password resets invalidate that account's existing sessions. Password resets are local and do not send passwords by email. The admin page never displays passwords or hashes.
The dashboard shows a simulated ledger (an illustrative opening balance and sample activity); it does not represent real funds or permit actual transfers. Admins can export account summaries to CSV, download a consistent SQLite backup, and restore a validated backup. Restores first create a recovery backup and are limited to 25 MB. Only restore trusted files. Backups contain sensitive demo account data and password hashes, so keep them private.
The self-service password reset uses a random, single-use token stored only as a hash and expires after 30 minutes. To send links, configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY` (`starttls` or `ssl`), `SMTP_FROM`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `PUBLIC_BASE_URL` in the local process environment. For non-local URLs, `PUBLIC_BASE_URL` must use HTTPS. Keep SMTP credentials out of source control and chat; do not enable this app for public access.
Technicians can view the latest 100 application event types and timestamps at `/technician/activity`, without usernames, contact details, or account controls. Admins can also open this view. Regular users cannot access it.

## Public static concept

`docs/index.html` is the public-safe, static-only concept page. It contains no registration or sign-in form and does not connect to the Flask app. Its sample privacy notice and terms describe this static page only; they are not policies for a real bank or for the local Flask learning demo. The public concept is hosted separately at [Family Bank Concept](https://ab00999.github.io/family-bank-concept/); only the static HTML page is published. The Flask app, admin pages, and database remain private and local.

Do not configure a public host to run `app.py`: the local Flask learning demo stores submitted email addresses, phone numbers, and password hashes, and is not suitable for public use or real personal data.

To reset a demo account password locally as an administrator, stop the app if it is running, then run:

```powershell
python reset_password.py
```

Enter the account username and a new password when prompted. Password input is hidden; the password is hashed before it is saved. This local utility does not reveal existing passwords or provide a public reset page.

To designate an existing account as the initial admin, set `FAMILY_BANK_ADMIN_USERNAME` to that account's username before starting the app. The app assigns this role only when no admin role exists yet; after that, admins can manage roles from the protected admin page. Never leave the initial admin account unregistered or use a publicly guessable admin identity on a public server. For example, in PowerShell:

```powershell
$env:FAMILY_BANK_ADMIN_USERNAME = "your-demo-username"
python app.py
```

Visit `/admin` after signing in as that account. Regular users are denied, and the page never returns password hashes. Use made-up demo data only; the application is not suitable for public banking or real customer accounts.

This is a local learning project, not a real bank. Use only made-up credentials; do not deploy it publicly or use real/reused passwords. For production, configure a persistent random `FLASK_SECRET_KEY`, HTTPS, secure cookies, and a full security review.

## Author

Abdoul Sawadogo