from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, current_user
from flask_login import UserMixin, logout_user
from datetime import datetime, timezone
import string
import random
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev_key")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shortener.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# --- User Model ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)

    urls = db.relationship('URL', backref='user', lazy=True)


# --- URL Model ---
class URL(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.String(2048), nullable=False)
    short_code = db.Column(db.String(6), unique=True, nullable=False)
    click_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))  # Use timezone-aware UTC time

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def generate_short_code(self):
        characters = string.ascii_letters + string.digits
        self.short_code = ''.join(random.choices(characters, k=6))


with app.app_context():
    db.create_all()


# --- User Loader for Flask-Login ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists! Please choose another one.", "danger")
            return redirect(url_for("register"))

        # Check if the email already exists
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash("Email already registered! Please use another email.", "danger")
            return redirect(url_for("register"))

        # Create new user
        new_user = User(username=username, email=email, password_hash=password)  # Use hashed password here
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful!", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, login_required, logout_user


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and user.password_hash == password:  # Compare plain text passwords
            login_user(user)  # Log the user in
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    return f"Hello, {current_user.username}! <a href='/logout'>Logout</a>"


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "success")
    return redirect(url_for("login"))


@app.route("/shorten", methods=["POST"])
@login_required
def shorten_url():
    original_url = request.form["url"]
    short_code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))

    # Create a new URL entry in the database
    new_url = URL(original_url=original_url, short_code=short_code, user_id=current_user.id)
    db.session.add(new_url)
    db.session.commit()

    flash(f"URL shortened! Short code: {short_code}", "success")
    return redirect(url_for("dashboard"))

@app.route("/profile", methods=["GET", "POST"])
@login_required  # Ensure the user is logged in
def profile():
    user = current_user  # Get the currently logged-in user

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]

        # Update user details
        user.username = username
        user.email = email
        db.session.commit()

        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user)





if __name__ == '__main__':
    app.run(debug=True)
