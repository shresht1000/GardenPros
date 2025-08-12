from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import smtplib
import ssl
from email.message import EmailMessage
import os
import paypalrestsdk
import bcrypt
import uuid
import secrets      

app = Flask(__name__)
app.secret_key = "your_secret_key"

DB_FILE = "users.db"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = "shreshtmit09@gmail.com"
SENDER_PASSWORD = "krun zgdz tmuj cngd"

# PayPal Configuration (LIVE MODE)
paypalrestsdk.configure({
    "mode": "live",  # Live mode for real transactions
    "client_id": "YOUR_LIVE_PAYPAL_CLIENT_ID",
    "client_secret": "YOUR_LIVE_PAYPAL_CLIENT_SECRET"
})

# Database Setup
if not os.path.exists(DB_FILE):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password BLOB NOT NULL,
            confirmation_token TEXT,
            confirmed INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# Email Confirmation Function
def send_confirmation_email(email, token):
    msg = EmailMessage()
    msg["Subject"] = "Confirm Your Account"
    msg["From"] = SENDER_EMAIL
    msg["To"] = email
    confirmation_link = f"http://gardepros.onrender.com/confirm/{token}"
    msg.set_content(f"Click the link below to confirm your account:\n\n{confirmation_link}")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)

# Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/buy")
def buy():
    return render_template("buy.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        token = str(uuid.uuid4())  

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (email, password, confirmation_token) VALUES (?, ?, ?)", 
                           (email, hashed_password, token))
            conn.commit()
            send_confirmation_email(email, token)
            flash("Account created! Check your email for confirmation.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already registered!", "danger")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/confirm/<token>")
def confirm_account(token):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE confirmation_token = ?", (token,))
    user = cursor.fetchone()

    if user:
        cursor.execute("UPDATE users SET confirmed = 1, confirmation_token = NULL WHERE id = ?", (user[0],))
        conn.commit()
        flash("Account confirmed! You can now log in.", "success")
    else:
        flash("Invalid or expired confirmation link.", "danger")

    conn.close()
    return render_template("confirmation.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT password, confirmed FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and bcrypt.checkpw(password.encode("utf-8"), user[0]):
            if user[1] == 0:
                flash("Please confirm your email before logging in.", "warning")
                return redirect(url_for("login"))
            session["email"] = email
            flash("Login successful!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid credentials!", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("email", None)
    flash("Logged out successfully!", "info")
    return redirect(url_for("index"))

@app.route("/cart")
def cart():
    return render_template("cart.html")
@app.route("/checkout", methods=["POST","GET"])
def checkout():
    if request.method == "GET":
        return render_template("checkout.html")  # Render checkout page

    try:
        cart_items = session.get("cart", [])
        donation = float(request.form.get("donation", 0))  # Get donation amount (default 0)
        
        if not cart_items:
            flash("Your cart is empty!", "danger")
            return redirect(url_for("cart"))

        total_amount = sum(item["price"] * item["quantity"] for item in cart_items) + donation
        
        # Create PayPal Payment
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": url_for("payment_success", _external=True),
                "cancel_url": url_for("payment_canceled", _external=True),
            },
            "transactions": [{
                "item_list": {"items": [
                    {"name": item["name"], "price": f"{item['price']:.2f}", "currency": "USD", "quantity": item["quantity"]}
                    for item in cart_items
                ] + ([{"name": "Donation", "price": f"{donation:.2f}", "currency": "USD", "quantity": 1}] if donation > 0 else [])},
                "amount": {"total": f"{total_amount:.2f}", "currency": "USD"},
                "description": "Garden Pros Purchase",
            }]
        })

        if payment.create():
            for link in payment.links:
                if link.rel == "approval_url":
                    return redirect(link.href)
        else:
            flash("Payment failed. Try again!", "danger")
            return redirect(url_for("cart"))

    except Exception as e:
        print("Error in checkout:", str(e))
        flash("Something went wrong. Please try again.", "danger")
        return redirect(url_for("cart"))


@app.route('/execute_payment', methods=['GET'])
def execute_payment():
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')
    payment = paypalrestsdk.Payment.find(payment_id)

    if payment.execute({"payer_id": payer_id}):
        flash("Payment successful!", "success")
        session["cart"] = []
        return redirect(url_for("index"))
    else:
        flash("Error executing PayPal payment.", "danger")
        return redirect(url_for("checkout"))

@app.route('/payment_canceled')
def payment_canceled():
    flash("Payment canceled.", "info")
    return redirect(url_for("checkout"))

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data received"}), 400
        
        name = data.get("name")
        price = data.get("price")
        if not name or not price:
            return jsonify({"error": "Missing name or price"}), 400

        session.setdefault("cart", []).append({"name": name, "price": price, "quantity": 1})
        session.modified = True

        return jsonify({"message": f"{name} added to cart", "cart": session["cart"]}), 200

    except Exception as e:
        print("Error in /add_to_cart:", str(e))
        return jsonify({"error": "Something went wrong"}), 500
    
@app.route("/pots")
def pots():
    return render_template("pots.html")

@app.route("/appliances")
def appliances():
    return render_template("appliances.html")

@app.route("/seeds")
def seeds():
    return render_template("seeds.html")
@app.route("/ebook", methods=["GET", "POST"])
def ebook():
    if request.method == "POST":
        email = request.form["email"]

        # Validate email format
        if "@" not in email or "." not in email:
            flash("Invalid email format!", "danger")
            return redirect(url_for("ebook"))

        # Generate a unique confirmation token
        token = secrets.token_urlsafe(16)

        # Compose the email
        msg = EmailMessage()
        msg["Subject"] = "Your Free eBook Link"
        msg["From"] = SENDER_EMAIL
        msg["To"] = email
        msg.set_content("Click the link below to download your eBook:\n\n"
                        "https://docs.google.com/document/d/14z05oDhZL-OeCnd6rcBTWfuQiMzMCYWBJWwK0MmbnUg/edit?usp=sharing")

        # Send the email
        context = ssl.create_default_context()
        try:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)
            flash("Check your email for the eBook download link.", "success")
        except Exception as e:
            flash(f"Failed to send email: {str(e)}", "danger")

        return redirect(url_for("index"))

    return render_template("ebook.html")

# Password Recovery Routes
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user:
            reset_token = str(uuid.uuid4())
            cursor.execute("UPDATE users SET reset_token = ? WHERE email = ?", (reset_token, email))
            conn.commit()
            reset_link = f"http://127.0.0.1:5000/reset_password/{reset_token}"
            send_email(email, "Reset Your Password", f"Click here to reset your password: {reset_link}")
            flash("Password reset link sent! Check your email.", "info")
        else:
            flash("Email not found!", "danger")

        conn.close()
        return redirect(url_for("forgot_password"))

    return render_template("forgot_password.html")


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if request.method == "POST":
        new_password = request.form["password"]
        hashed_password = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE reset_token = ?", (token,))
        user = cursor.fetchone()

        if user:
            cursor.execute("UPDATE users SET password = ?, reset_token = NULL WHERE id = ?", (hashed_password, user[0]))
            conn.commit()
            flash("Password reset successful! You can now log in.", "success")
            return redirect(url_for("login"))
        else:
            flash("Invalid or expired reset link.", "danger")

        conn.close()

    return render_template("reset_password.html")

if __name__ == "__main__":
    app.run(debug=False)
