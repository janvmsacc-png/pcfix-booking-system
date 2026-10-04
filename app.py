import os
import secrets
import string
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, abort
)
from dotenv import load_dotenv
from supabase import create_client, Client
import resend
from resend.exceptions import ResendError
import jwt

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Supabase init error: {e}")

# Resend Settings
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
APP_URL = os.getenv("APP_URL", "http://localhost:5000")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Initialize Resend Key Globally
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
else:
    print("⚠️ WARNING: RESEND_API_KEY missing from environment variables. Running in local development print mode.")

# Services data
SERVICES = {
    "troubleshooting": {
        "name": "Troubleshooting",
        "description": "Diagnose and resolve software issues, error messages, and performance problems.",
        "price": 999,
        "duration": "1-2 hours",
        "features": ["Virus & malware scan", "Driver updates", "System optimization", "Error diagnostics"]
    },
    "maintenance": {
        "name": "Maintenance",
        "description": "Preventive care to keep your computer running smoothly and extend its lifespan.",
        "price": 1999,
        "duration": "2-3 hours",
        "features": ["Full system cleanup", "Hardware inspection", "Thermal paste refresh", "Backup assistance"]
    },
    "repair": {
        "name": "Repair",
        "description": "Hardware repairs including screen, keyboard, battery, and component replacement.",
        "price": 2999,
        "duration": "Same day / 1-3 days",
        "features": ["Component replacement", "Screen repair", "Battery service", "Data recovery option"]
    }
}

TIME_SLOTS = [
    "09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00"
]


def generate_otp(length=6):
    return "".join(secrets.choice(string.digits) for _ in range(length))


def send_email(to: str, subject: str, html: str) -> bool:
    """
    Sends transactional template emails via Resend API.
    Falls back to terminal text representation if no API key is set.
    """
    if not RESEND_API_KEY:
        print(f"[DEV EMAIL] To: {to} | Subject: {subject}")
        print(html[:500])
        return True
    try:
        # Construct explicit dictionary conforming to Resend execution schema
        email_payload = {
            "from": FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        
        # Fire over the network
        response = resend.Emails.send(email_payload)
        print(f"✅ Email delivered cleanly via Resend! ID: {response.get('id')}")
        return True
        
    except ResendError as re:
        print(f"❌ Resend Specific Engine Exception: {re}")
        return False
    except Exception as e:
        print(f"❌ Email transmission pipeline error: {e}")
        return False


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Admin access required.", "error")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated



# ---------- Public Routes ----------

@app.route("/")
def index():
    return render_template("index.html", services=SERVICES)


@app.route("/services")
def services():
    return render_template("services.html", services=SERVICES)


@app.route("/pricing")
def pricing():
    return render_template("pricing.html", services=SERVICES)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if not all([name, email, message]):
            flash("All fields are required.", "error")
            return redirect(url_for("contact"))
        html = f"""
        <h2>New Contact Message</h2>
        <p><strong>Name:</strong> {name}</p>
        <p><strong>Email:</strong> {email}</p>
        <p><strong>Message:</strong></p>
        <p>{message}</p>
        """
        send_email(ADMIN_EMAIL, f"Contact from {name}", html)
        flash("Thank you! Your message has been sent. We'll reply shortly.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")


# ---------- Auth ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        if not username or not email:
            flash("Username and email are required.", "error")
            return redirect(url_for("register"))
        if len(username) < 3:
            flash("Username must be at least 3 characters.", "error")
            return redirect(url_for("register"))

        if supabase:
            try:
                # Check existing
                existing = supabase.table("users").select("id").or_(
                    f"username.eq.{username},email.eq.{email}"
                ).execute()
                if existing.data:
                    flash("Username or email already registered.", "error")
                    return redirect(url_for("register"))

                result = supabase.table("users").insert({
                    "username": username,
                    "email": email,
                }).execute()
                user = result.data[0] if result.data else None
                if user:
                    session["user_id"] = user["id"]
                    session["username"] = username
                    session["email"] = email
                    flash("Account created successfully! Welcome.", "success")
                    return redirect(url_for("index"))
            except Exception as e:
                print(f"Register error: {e}")
                flash("Registration failed. Please try again.", "error")
        else:
            # Dev fallback
            session["user_id"] = secrets.token_hex(8)
            session["username"] = username
            session["email"] = email
            flash("Account created (dev mode).", "success")
            return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        step = request.form.get("step", "username")
        if step == "username":
            username = request.form.get("username", "").strip().lower()
            if not username:
                flash("Please enter your username.", "error")
                return redirect(url_for("login"))

            email = None
            if supabase:
                try:
                    result = supabase.table("users").select("id, email, username").eq(
                        "username", username
                    ).execute()
                    if result.data:
                        email = result.data[0]["email"]
                        session["pending_user"] = result.data[0]
                    else:
                        flash("Username not found.", "error")
                        return redirect(url_for("login"))
                except Exception as e:
                    print(f"Login lookup error: {e}")
                    flash("Login service temporarily unavailable.", "error")
                    return redirect(url_for("login"))
            else:
                # Dev: accept any username, use a fake email
                email = f"{username}@example.com"
                session["pending_user"] = {
                    "id": secrets.token_hex(8),
                    "username": username,
                    "email": email
                }

            # Generate & store OTP
            otp = generate_otp()
            session["otp"] = otp
            session["otp_expires"] = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
            session["otp_email"] = email

            html = f"""
            <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
              <h2 style="color: #0F766E;">Your PCfix Login Code</h2>
              <p>Use this one-time code to sign in:</p>
              <p style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #0EA5E9;">{otp}</p>
              <p style="color: #64748B;">This code expires in 10 minutes. If you did not request it, ignore this email.</p>
            </div>
            """
            send_email(email, "Your PCfix Login Code", html)
            flash("A verification code has been sent to your email.", "success")
            return render_template("login.html", step="otp", username=username)

        elif step == "otp":
            code = request.form.get("code", "").strip()
            stored = session.get("otp")
            expires = session.get("otp_expires")
            pending = session.get("pending_user")

            if not all([stored, expires, pending]):
                flash("Session expired. Please try again.", "error")
                return redirect(url_for("login"))

            if datetime.utcnow() > datetime.fromisoformat(expires):
                flash("Code expired. Please request a new one.", "error")
                session.pop("otp", None)
                return redirect(url_for("login"))

            if code != stored:
                flash("Invalid code. Please try again.", "error")
                return render_template("login.html", step="otp", username=pending.get("username"))

            # Success
            session["user_id"] = pending["id"]
            session["username"] = pending["username"]
            session["email"] = pending["email"]
            for k in ["otp", "otp_expires", "otp_email", "pending_user"]:
                session.pop(k, None)
            flash(f"Welcome back, {pending['username']}!", "success")
            next_url = request.args.get("next") or url_for("index")
            return redirect(next_url)

    return render_template("login.html", step="username")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    if request.method == "POST" and request.form.get("action") == "delete":
        if supabase:
            try:
                supabase.table("users").delete().eq("id", session["user_id"]).execute()
            except Exception as e:
                print(f"Delete account error: {e}")
        session.clear()
        flash("Your account has been permanently deleted.", "success")
        return redirect(url_for("index"))
    return render_template("account.html")


# ---------- Booking ----------

@app.route("/book", methods=["GET", "POST"])
def book():
    if request.method == "POST":
        service_key = request.form.get("service")
        date = request.form.get("date")
        time_slot = request.form.get("time_slot")
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip().lower()

        if not all([service_key, date, time_slot, name, phone, email]):
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("book"))

        if service_key not in SERVICES:
            flash("Invalid service selected.", "error")
            return redirect(url_for("book"))

        booking_id = secrets.token_urlsafe(12)
        booking_data = {
            "id": booking_id,
            "user_id": session.get("user_id"),
            "service": service_key,
            "date": date,
            "time_slot": time_slot,
            "name": name,
            "phone": phone,
            "email": email,
            "status": "pending",
            "payment_status": "unpaid",
            "machine_details": None,
            "created_at": datetime.utcnow().isoformat(),
        }

        if supabase:
            try:
                supabase.table("bookings").insert(booking_data).execute()
            except Exception as e:
                print(f"Booking insert error: {e}")
                # Continue with session storage for demo
                session["last_booking"] = booking_data
        else:
            session["last_booking"] = booking_data

        # Send confirmation email with link
        confirm_url = f"{APP_URL}/confirm/{booking_id}"
        service_name = SERVICES[service_key]["name"]
        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 560px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0;">
          <div style="background: linear-gradient(135deg, #0F766E, #0EA5E9); padding: 32px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">Booking Confirmed</h1>
          </div>
          <div style="padding: 32px;">
            <p style="font-size: 16px; color: #334155;">Hi {name},</p>
            <p style="color: #64748B;">Thank you for choosing <strong>PCfix</strong>. Your booking has been received.</p>
            <table style="width: 100%; border-collapse: collapse; margin: 24px 0;">
              <tr><td style="padding: 8px 0; color: #64748B;">Service</td><td style="padding: 8px 0; font-weight: 600;">{service_name}</td></tr>
              <tr><td style="padding: 8px 0; color: #64748B;">Date</td><td style="padding: 8px 0; font-weight: 600;">{date}</td></tr>
              <tr><td style="padding: 8px 0; color: #64748B;">Time</td><td style="padding: 8px 0; font-weight: 600;">{time_slot}</td></tr>
            </table>
            <p style="color: #64748B;">Please complete the machine details and downpayment to secure your slot:</p>
            <a href="{confirm_url}" style="display: inline-block; background: #0EA5E9; color: white; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; margin-top: 8px;">Complete Confirmation &amp; Downpayment</a>
            <p style="margin-top: 32px; font-size: 13px; color: #94A3B8;">If the button doesn't work, copy this link:<br>{confirm_url}</p>
          </div>
        </div>
        """
        send_email(email, f"PCfix Booking Confirmation – {service_name}", html)

        # Notify admin
        admin_html = f"""
        <h2>New Booking</h2>
        <p>Name: {name}<br>Email: {email}<br>Phone: {phone}<br>
        Service: {service_name}<br>Date: {date} {time_slot}</p>
        <p>Booking ID: {booking_id}</p>
        """
        send_email(ADMIN_EMAIL, f"New Booking: {name}", admin_html)

        flash("Booking received! Check your email for the confirmation link.", "success")
        return redirect(url_for("book_success", booking_id=booking_id))

    return render_template("book.html", services=SERVICES, time_slots=TIME_SLOTS)


@app.route("/book/success/<booking_id>")
def book_success(booking_id):
    return render_template("book_success.html", booking_id=booking_id)


@app.route("/confirm/<booking_id>", methods=["GET", "POST"])
def confirm(booking_id):
    booking = None
    if supabase:
        try:
            result = supabase.table("bookings").select("*").eq("id", booking_id).execute()
            if result.data:
                booking = result.data[0]
        except Exception as e:
            print(f"Confirm fetch error: {e}")

    if not booking:
        # Fallback to session
        booking = session.get("last_booking")
        if not booking or booking.get("id") != booking_id:
            flash("Booking not found or link expired.", "error")
            return redirect(url_for("index"))

    if request.method == "POST":
        brand = request.form.get("brand", "").strip()
        os_name = request.form.get("os", "").strip()
        issue = request.form.get("issue", "").strip()
        payment_method = request.form.get("payment_method", "gcash")

        if not all([brand, os_name, issue]):
            flash("Please fill in all machine details.", "error")
            return redirect(url_for("confirm", booking_id=booking_id))

        details = {
            "brand": brand,
            "os": os_name,
            "issue": issue,
            "payment_method": payment_method,
        }

        if supabase:
            try:
                supabase.table("bookings").update({
                    "machine_details": details,
                    "payment_status": "pending_review",
                    "status": "confirmed",
                }).eq("id", booking_id).execute()
            except Exception as e:
                print(f"Confirm update error: {e}")

        flash("Details submitted! Our team will review your downpayment shortly.", "success")
        return redirect(url_for("confirm_success", booking_id=booking_id))

    service = SERVICES.get(booking.get("service", ""), {})
    return render_template(
        "confirm.html",
        booking=booking,
        service=service,
        booking_id=booking_id,
    )


@app.route("/confirm/success/<booking_id>")
def confirm_success(booking_id):
    return render_template("confirm_success.html", booking_id=booking_id)


# ---------- Admin ----------

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["is_admin"] = True
            flash("Admin access granted.", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Incorrect password.", "error")
    return render_template("admin/login.html")


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    bookings = []
    if supabase:
        try:
            result = supabase.table("bookings").select("*").order(
                "created_at", desc=True
            ).execute()
            bookings = result.data or []
        except Exception as e:
            print(f"Admin fetch error: {e}")
    else:
        # Demo data
        if "last_booking" in session:
            bookings = [session["last_booking"]]

    active = sum(1 for b in bookings if b.get("status") in ("pending", "confirmed"))
    pending_pay = sum(1 for b in bookings if b.get("payment_status") in ("unpaid", "pending_review"))

    return render_template(
        "admin/dashboard.html",
        bookings=bookings,
        services=SERVICES,
        active_count=active,
        pending_pay_count=pending_pay,
    )


@app.route("/admin/action", methods=["POST"])
@admin_required
def admin_action():
    booking_id = request.form.get("booking_id")
    action = request.form.get("action")
    if not booking_id or not action:
        flash("Invalid request.", "error")
        return redirect(url_for("admin_dashboard"))

    updates = {}
    if action == "mark_paid":
        updates = {"payment_status": "paid"}
    elif action == "archive":
        updates = {"status": "archived"}
    elif action == "reschedule":
        # Simple: set status back to pending for manual reschedule
        updates = {"status": "pending"}

    if updates and supabase:
        try:
            supabase.table("bookings").update(updates).eq("id", booking_id).execute()
            flash(f"Booking updated: {action.replace('_', ' ').title()}", "success")
        except Exception as e:
            print(f"Admin action error: {e}")
            flash("Update failed.", "error")
    else:
        flash(f"Action '{action}' noted (dev mode).", "success")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("Admin logged out.", "success")
    return redirect(url_for("index"))


# ---------- API helpers (for JS calendar availability) ----------

@app.route("/api/slots")
def api_slots():
    date = request.args.get("date")
    # In production, query bookings for that date and exclude taken slots
    # For now return all slots
    return jsonify({"slots": TIME_SLOTS})


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
