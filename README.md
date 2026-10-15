
# Smart Library Management System

A web-based library management project built with Python, Flask, SQLAlchemy, HTML, CSS, and JavaScript.

## Features

- Book catalogue with search and category filters
- Voice-based book search
- Student registration
- Book issue and return management
- Loan due dates and overdue status
- SQLite support for local development
- MySQL-compatible database configuration
- CSV import for 100 sample book records

## Technologies

- Python
- Flask
- Flask-SQLAlchemy
- SQLite / MySQL
- HTML, CSS, JavaScript
- Browser Speech Recognition API

## Installation

Install Python and clone this repository.

```bash
git clone https://github.com/YOUR_USERNAME/smart-library-management-system.git
cd smart-library-management-system
python -m venv .venv
```

Activate the virtual environment and install dependencies:

```bash
pip install -r requirements.txt
```

Initialize the database:

```bash
flask --app app init-db
flask --app app seed-books
```

Start the application:

```bash
flask --app app run
```

Open http://127.0.0.1:5000 in your browser.

## Database

The sample catalogue is stored in `books.csv`. The seed command imports the records into the configured database.

The default local database is SQLite. Set `DATABASE_URL` to a valid MySQL connection string to use MySQL.

## Important

The sample ISBN identifiers are placeholders, not verified ISBNs.

Set a secure `SECRET_KEY` before deploying. Do not commit passwords, credentials, or private student information.

## Project Status

Educational starter project. Test and secure the application before production use.
