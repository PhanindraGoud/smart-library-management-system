
import os
import csv
from datetime import date, timedelta

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "change-this-secret-before-deployment"
)

database_url = os.environ.get("DATABASE_URL", "sqlite:///library.db")

if database_url.startswith("mysql://"):
    database_url = database_url.replace(
        "mysql://", "mysql+pymysql://", 1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    isbn = db.Column(db.String(30), unique=True)
    total_copies = db.Column(db.Integer, default=1, nullable=False)
    available_copies = db.Column(db.Integer, default=1, nullable=False)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    student_number = db.Column(db.String(40), unique=True, nullable=False)
    email = db.Column(db.String(150))


class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    issue_date = db.Column(db.Date, default=date.today, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date)

    book = db.relationship("Book", backref="loans")
    student = db.relationship("Student", backref="loans")


@app.route("/")
def index():
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    query = Book.query

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Book.title.ilike(term),
                Book.author.ilike(term),
                Book.category.ilike(term),
                Book.isbn.ilike(term),
            )
        )

    if category:
        query = query.filter_by(category=category)

    books = query.order_by(Book.title).all()

    categories = [
        item[0]
        for item in db.session.query(Book.category)
        .distinct()
        .order_by(Book.category)
        .all()
    ]

    return render_template(
        "index.html",
        books=books,
        q=search,
        categories=categories,
        selected_category=category,
        book_count=Book.query.count(),
        student_count=Student.query.count(),
        active_loans=Loan.query.filter_by(return_date=None).count(),
    )


@app.route("/students", methods=["POST"])
def add_student():
    name = request.form.get("name", "").strip()
    number = request.form.get("student_number", "").strip()
    email = request.form.get("email", "").strip()

    if not name or not number:
        flash("Student name and number are required.", "error")
    elif Student.query.filter_by(student_number=number).first():
        flash("Student number already exists.", "error")
    else:
        student = Student(
            name=name,
            student_number=number,
            email=email or None,
        )
        db.session.add(student)
        db.session.commit()
        flash("Student registered successfully.", "success")

    return redirect(url_for("index"))


@app.route("/issue", methods=["POST"])
def issue_book():
    try:
        book_id = int(request.form.get("book_id", ""))
        student_id = int(request.form.get("student_id", ""))
    except ValueError:
        flash("Select a valid book and student.", "error")
        return redirect(url_for("loans"))

    book = db.session.get(Book, book_id)
    student = db.session.get(Student, student_id)

    if not book or not student:
        flash("Book or student not found.", "error")
    elif book.available_copies < 1:
        flash("This book is unavailable.", "error")
    else:
        loan = Loan(
            book=book,
            student=student,
            due_date=date.today() + timedelta(days=14),
        )
        book.available_copies -= 1
        db.session.add(loan)
        db.session.commit()
        flash("Book issued successfully.", "success")

    return redirect(url_for("loans"))


@app.route("/return/<int:loan_id>", methods=["POST"])
def return_book(loan_id):
    loan = db.session.get(Loan, loan_id)

    if loan and loan.return_date is None:
        loan.return_date = date.today()
        loan.book.available_copies = min(
            loan.book.total_copies,
            loan.book.available_copies + 1,
        )
        db.session.commit()
        flash("Book returned successfully.", "success")

    return redirect(url_for("loans"))


@app.route("/loans")
def loans():
    all_loans = Loan.query.order_by(Loan.issue_date.desc()).all()
    students = Student.query.order_by(Student.name).all()
    books = Book.query.filter(
        Book.available_copies > 0
    ).order_by(Book.title).all()

    return render_template(
        "loans.html",
        loans=all_loans,
        students=students,
        books=books,
        today=date.today(),
    )


@app.route("/api/books")
def api_books():
    search = request.args.get("q", "").strip()
    query = Book.query

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Book.title.ilike(term),
                Book.author.ilike(term),
                Book.category.ilike(term),
            )
        )

    results = query.order_by(Book.title).limit(100).all()

    return jsonify([
        {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "category": book.category,
            "available": book.available_copies,
            "status": (
                "Available" if book.available_copies > 0
                else "Unavailable"
            ),
        }
        for book in results
    ])


@app.cli.command("init-db")
def init_db():
    db.create_all()
    print("Database tables created successfully.")


@app.cli.command("seed-books")
def seed_books():
    if Book.query.count() > 0:
        print("Books already exist. Import skipped.")
        return

    csv_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "books.csv",
    )

    with open(csv_path, newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            copies = int(row["total_copies"])
            db.session.add(
                Book(
                    title=row["title"],
                    author=row["author"],
                    category=row["category"],
                    isbn=row["isbn"],
                    total_copies=copies,
                    available_copies=copies,
                )
            )

    db.session.commit()
    print(f"Imported {Book.query.count()} books.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
