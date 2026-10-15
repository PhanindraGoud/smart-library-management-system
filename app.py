
import os
import csv
from datetime import date, timedelta

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "change-this-secret-before-production"
)

# Database configuration
database_url = os.environ.get("DATABASE_URL", "sqlite:///library.db")

# Some hosting providers supply MySQL URLs using mysql://
if database_url.startswith("mysql://"):
    database_url = database_url.replace(
        "mysql://", "mysql+pymysql://", 1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# Database models
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(30), unique=True)
    total_copies = db.Column(db.Integer, nullable=False, default=1)
    available_copies = db.Column(db.Integer, nullable=False, default=1)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    student_number = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(150))

    loans = db.relationship("Loan", back_populates="student")


class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(
        db.Integer, db.ForeignKey("book.id"), nullable=False
    )
    student_id = db.Column(
        db.Integer, db.ForeignKey("student.id"), nullable=False
    )
    issue_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date)

    book = db.relationship("Book")
    student = db.relationship("Student", back_populates="loans")


# Create database tables when Gunicorn starts the application.
# This fixes the "no such table: book" deployment error.
with app.app_context():
    db.create_all()


# Home page and book catalogue
@app.route("/")
def index():
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()

    query = Book.query

    if search:
        query = query.filter(
            db.or_(
                Book.title.ilike(f"%{search}%"),
                Book.author.ilike(f"%{search}%"),
                Book.isbn.ilike(f"%{search}%"),
            )
        )

    if category:
        query = query.filter(Book.category == category)

    books = query.order_by(Book.title).all()

    categories = [
        row[0]
        for row in db.session.query(Book.category)
        .distinct()
        .order_by(Book.category)
        .all()
    ]

    total_books = db.session.query(
        db.func.coalesce(db.func.sum(Book.total_copies), 0)
    ).scalar()

    total_students = Student.query.count()
    active_loans = Loan.query.filter(Loan.return_date.is_(None)).count()

    return render_template(
        "index.html",
        books=books,
        categories=categories,
        search=search,
        selected_category=category,
        total_books=total_books,
        total_students=total_students,
        active_loans=active_loans,
    )


# Register a student
@app.route("/students", methods=["POST"])
def add_student():
    name = request.form.get("name", "").strip()
    student_number = request.form.get("student_number", "").strip()
    email = request.form.get("email", "").strip()

    if not name or not student_number:
        flash("Name and student number are required.", "error")
        return redirect(url_for("index"))

    if Student.query.filter_by(student_number=student_number).first():
        flash("That student number is already registered.", "error")
        return redirect(url_for("index"))

    student = Student(
        name=name,
        student_number=student_number,
        email=email or None,
    )

    db.session.add(student)
    db.session.commit()

    flash("Student registered successfully.", "success")
    return redirect(url_for("index"))


# Issue a book to a student
@app.route("/issue", methods=["POST"])
def issue_book():
    try:
        book_id = int(request.form.get("book_id", ""))
        student_id = int(request.form.get("student_id", ""))
    except (TypeError, ValueError):
        flash("Please select a valid book and student.", "error")
        return redirect(url_for("loans"))

    book = db.session.get(Book, book_id)
    student = db.session.get(Student, student_id)

    if book is None or student is None:
        flash("The selected book or student was not found.", "error")
        return redirect(url_for("loans"))

    if book.available_copies < 1:
        flash("This book is currently unavailable.", "error")
        return redirect(url_for("loans"))

    loan = Loan(
        book_id=book.id,
        student_id=student.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=14),
    )

    book.available_copies -= 1
    db.session.add(loan)
    db.session.commit()

    flash("Book issued successfully.", "success")
    return redirect(url_for("loans"))


# Return a book
@app.route("/return/<int:loan_id>", methods=["POST"])
def return_book(loan_id):
    loan = db.session.get(Loan, loan_id)

    if loan is None:
        flash("Loan record not found.", "error")
        return redirect(url_for("loans"))

    if loan.return_date is not None:
        flash("This book has already been returned.", "error")
        return redirect(url_for("loans"))

    loan.return_date = date.today()
    loan.book.available_copies += 1
    db.session.commit()

    flash("Book returned successfully.", "success")
    return redirect(url_for("loans"))


# Loans and issue/return page
@app.route("/loans")
def loans():
    all_loans = Loan.query.order_by(Loan.issue_date.desc()).all()
    students = Student.query.order_by(Student.name).all()
    books = Book.query.order_by(Book.title).all()
    active_loans = Loan.query.filter(Loan.return_date.is_(None)).count()

    return render_template(
        "loans.html",
        loans=all_loans,
        students=students,
        books=books,
        active_loans=active_loans,
    )


# Book catalogue API
@app.route("/api/books")
def api_books():
    books = Book.query.order_by(Book.title).all()

    return jsonify([
        {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "category": book.category,
            "isbn": book.isbn,
            "total_copies": book.total_copies,
            "available_copies": book.available_copies,
        }
        for book in books
    ])


# Load the catalogue from books.csv if the database is empty.
def seed_books_if_empty():
    if Book.query.first():
        return

    csv_path = os.path.join(app.root_path, "books.csv")

    if not os.path.exists(csv_path):
        app.logger.warning("books.csv was not found; no books were loaded.")
        return

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            title = (row.get("title") or "").strip()
            author = (row.get("author") or "").strip()
            category = (row.get("category") or "General").strip()
            isbn = (row.get("isbn") or "").strip() or None

            if not title or not author:
                continue

            total_copies = int(row.get("total_copies") or 1)

            if isbn and Book.query.filter_by(isbn=isbn).first():
                continue

            db.session.add(
                Book(
                    title=title,
                    author=author,
                    category=category,
                    isbn=isbn,
                    total_copies=total_copies,
                    available_copies=total_copies,
                )
            )

        db.session.commit()


# Ensure tables and initial catalogue exist on startup.
with app.app_context():
    db.create_all()
    seed_books_if_empty()


# Optional commands for manual database setup
@app.cli.command("init-db")
def init_db():
    db.create_all()
    print("Database tables created.")


@app.cli.command("seed-books")
def seed_books():
    seed_books_if_empty()
    print("Book catalogue loaded if the database was empty.")


if __name__ == "__main__":
    app.run(debug=True)
