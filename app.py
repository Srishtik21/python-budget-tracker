import os
import pytesseract
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Maya%402000@localhost/budget_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    transactions = db.relationship('Transactions', backref='user', lazy=True)

class Transactions(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100))
    amount = db.Column(db.Float)
    trans_type = db.Column(db.String(10))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists.")
            return redirect(url_for("register"))
        hashed_pw = generate_password_hash(password)
        db.session.add(User(username=username, password=hashed_pw))
        db.session.commit()
        flash("Registered successfully. Please log in.")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            login_user(user)
            return redirect(url_for("index"))
        flash("Invalid credentials.")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.")
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        description = request.form["description"]
        amount = float(request.form["amount"])
        trans_type = request.form["type"]
        db.session.add(Transactions(description=description, amount=amount, trans_type=trans_type, user_id=current_user.id))
        db.session.commit()
        flash("Transaction added.")
        return redirect(url_for("index"))

    user_transactions = Transactions.query.filter_by(user_id=current_user.id).all()
    return render_template("index.html", transactions=user_transactions)

@app.route("/upload", methods=["POST"])
@login_required
def upload():
    file = request.files["receipt"]
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # OCR processing
        text = pytesseract.image_to_string(Image.open(filepath))

        # Very basic parsing logic (you can improve this)
        lines = text.splitlines()
        description = lines[0] if lines else "Unknown"
        amount = 0
        for line in lines:
            if "total" in line.lower():
                digits = ''.join(c for c in line if c.isdigit() or c == '.')
                try:
                    amount = float(digits)
                    break
                except:
                    pass

        if amount:
            db.session.add(Transactions(description=description[:100], amount=amount, trans_type='expense', user_id=current_user.id))
            db.session.commit()
            flash("Receipt processed and expense added!")
        else:
            flash("Couldn't extract amount from receipt. Please check manually.")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
