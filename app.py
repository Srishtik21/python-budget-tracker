import os
import json
import pytesseract
import openai
import speech_recognition as sr
from pydub import AudioSegment
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
from dotenv import load_dotenv

from test_voice import extract_financial_entries

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Maya%402000@localhost/budget_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@app.route("/process_speech_text", methods=["POST"])
@login_required
def process_speech_text():
    try:
        data = request.get_json()
        raw_text = data.get("text", "")
        entries = extract_financial_entries(raw_text)
        return jsonify(entries)
    except Exception as e:
        print("❌ Error in /process_speech_text:", str(e))
        return jsonify({"error": str(e)}), 500

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
    trans_type = db.Column(db.String(10))  # 'credit' or 'debit'
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
        trans_type = request.form["type"]  # should be 'credit' or 'debit'
        db.session.add(Transactions(description=description, amount=amount, trans_type=trans_type, user_id=current_user.id))
        db.session.commit()
        flash("Transaction added.")
        return redirect(url_for("index"))

    user_transactions = Transactions.query.filter_by(user_id=current_user.id).all()
    return render_template("index.html", transactions=user_transactions)

@app.route("/upload", methods=["POST"])
@login_required
def upload():
    file = request.files.get("receipt")
    if not file:
        flash("No receipt uploaded.")
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    text = pytesseract.image_to_string(Image.open(filepath))
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
        db.session.add(Transactions(description=description[:100], amount=amount, trans_type='debit', user_id=current_user.id))
        db.session.commit()
        flash("Receipt processed and debit added!")
    else:
        flash("Couldn't extract amount from receipt. Please check manually.")

    return redirect(url_for("index"))

@app.route("/speech", methods=["POST"])
@login_required
def speech():
    file = request.files.get('audio')
    if not file:
        flash("No audio uploaded.")
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    if not filepath.endswith(".wav"):
        sound = AudioSegment.from_file(filepath)
        filepath = filepath.rsplit('.', 1)[0] + ".wav"
        sound.export(filepath, format="wav")

    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(filepath) as source:
            audio = recognizer.record(source)
            voice_text = recognizer.recognize_google(audio)
    except Exception as e:
        flash("Speech recognition failed: " + str(e))
        return redirect(url_for("index"))

    try:
        entries = extract_financial_entries(voice_text)
        for item in entries:
            db.session.add(Transactions(
                description=item['description'][:100],
                amount=float(item['amount']),
                trans_type=item['status'],
                user_id=current_user.id
            ))
        db.session.commit()
        flash("Voice input processed and saved!")
    except Exception as e:
        flash("Failed to process via LLM: " + str(e))

    return redirect(url_for("index"))

@app.route("/add_multiple", methods=["POST"])
@login_required
def bulk_add():
    try:
        descriptions = request.form.getlist("description[]")
        statuses = request.form.getlist("status[]")
        amounts = request.form.getlist("amount[]")

        for desc, status, amount in zip(descriptions, statuses, amounts):
            db.session.add(Transactions(
                description=desc[:100],
                amount=float(amount),
                trans_type=status,
                user_id=current_user.id
            ))

        db.session.commit()
        flash(f"{len(descriptions)} transactions added.")
        return redirect(url_for("index"))
    except Exception as e:
        flash("Error adding multiple transactions: " + str(e))
        return redirect(url_for("index"))




if __name__ == "__main__":
    app.run(debug=True)
