# Complaint Desk - Complaint Management System

A web-based complaint management system built with **Flask** as an academic project.
Users submit complaints and follow their progress; staff and admins respond and update the status.

## Features

**For users**
- Register and log in (animated lamp login page, live username check, password strength rules, show/hide password)
- Submit complaints with title, category, priority and description
- See only their own complaints, with a status timeline and staff replies

**For staff and admins**
- See all complaints, reply, and change the status (Open, In Progress, Resolved, Closed)
- Reports page with complaint counts by category, status and priority, plus a JSON export

**General**
- Role-based access (user, staff, admin)
- Passwords are stored as salted hashes
- CSRF protection on all forms, server-side validation, safe redirects
- Responsive layout with a dark mode toggle
- Times are shown in Bangladesh time (UTC+6)

## Tech stack

Python, Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Bootstrap 5, SQLite (default) or MySQL.

## Run it locally

```bash
cd complaint_management_system
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

On the first run an `admin` account is created and its generated password is printed in the terminal.
To choose the password yourself, set `ADMIN_PASSWORD` before the first run.

## Configuration (environment variables)

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Signs session cookies. Set it for any real deployment. |
| `DATABASE_URL` | Database address. Defaults to a local SQLite file. Example for MySQL: `mysql+mysqlconnector://user:password@localhost/complaint_db` |
| `ADMIN_PASSWORD` | Password for the first admin account. |
| `FLASK_DEBUG` | Set to `1` for debug mode while developing. Never use it in production. |

## Managing users

New registrations are always normal users. An admin can promote someone or reset a password:

```bash
python manage_user.py role <username> staff
python manage_user.py password <username> <new_password>
```

## Project structure

```
complaint_management_system/
  app.py            routes, models, validation
  config.py         settings (read from environment variables)
  manage_user.py    admin helper
  templates/        Jinja templates
  static/style.css  design system, light and dark themes
  database/         sample MySQL schema
```
