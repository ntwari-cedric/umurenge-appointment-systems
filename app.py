import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date, timedelta, datetime
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv
load_dotenv()

# ---------------- RESOURCE PATH ----------------
def resource_path(relative_path):
    """
    Get absolute path to resource.
    Works both in normal Python run and after packaging with PyInstaller.
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ---------------- APP SETUP ----------------
app = Flask(
    __name__,
    template_folder=resource_path("templates"),
    static_folder=resource_path("static")
)

app.secret_key = "umurenge_secret_key_2026"
app.config["SESSION_PERMANENT"] = False

# PostgreSQL Database configuration
# IMPORTANT: Replace 'YOUR-ACTUAL-PASSWORD' with your real Supabase password
# If your password has special characters like @, #, $, use URL encoding:
# @ = %40, # = %23, $ = %24
DATABASE_URL = os.getenv('DATABASE_URL')

ADMIN_EMAIL = "ntwaricedrick001@gmail.com"
ADMIN_PASSWORD = "1234cedo"

# ---------------- FORCE LOGIN ----------------
@app.before_request
def require_login():
    public_routes = ["home", "login", "register", "static"]

    if request.endpoint in public_routes:
        return

    if "role" not in session:
        return redirect(url_for("login"))

# ---------------- NO CACHE ----------------
@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ---------------- DATABASE ----------------
def get_db():
    """Create and return a PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

def create_tables():
    """Create all tables in PostgreSQL (matching your SQLite schema)"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    
    # Create services table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id SERIAL PRIMARY KEY,
            service_name TEXT NOT NULL UNIQUE
        )
    """)
    
    # Create appointments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id SERIAL PRIMARY KEY,
            user_email TEXT NOT NULL,
            office_email TEXT NOT NULL,
            service_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            office_comment TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users(email),
            FOREIGN KEY (office_email) REFERENCES users(email),
            FOREIGN KEY (service_id) REFERENCES services(id)
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ PostgreSQL tables created successfully!")

# Initialize tables when app starts
create_tables()

# ---------------- HELPERS ----------------
def tomorrow_date():
    return (date.today() + timedelta(days=1)).isoformat()

def is_valid_future_date(selected_date):
    try:
        picked = datetime.strptime(selected_date, "%Y-%m-%d").date()
        return picked >= (date.today() + timedelta(days=1))
    except ValueError:
        return False

def get_all_services():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM services ORDER BY service_name ASC")
    services = cursor.fetchall()
    conn.close()
    return services

def get_all_offices():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE role = 'umurenge_office' ORDER BY name ASC")
    offices = cursor.fetchall()
    conn.close()
    return offices

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not name or not email or not password:
            return render_template("register.html", error="All fields are required")

        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO users (email, name, password, role)
                VALUES (%s, %s, %s, %s)
            """, (email, name, password, "user"))
            conn.commit()
        except psycopg2.IntegrityError:
            conn.close()
            return render_template("register.html", error="Email already exists")

        conn.close()
        return render_template("login.html", success="Registration successful. Please login.")

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "").strip()

        if not email or not password or not role:
            return render_template("login.html", error="All fields are required")

        if role == "admin":
            if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
                session.clear()
                session.permanent = False
                session["role"] = "admin"
                session["user_name"] = "Admin"
                session["user_email"] = ADMIN_EMAIL
                return redirect(url_for("admin_dashboard"))
            else:
                error = "Invalid admin email or password"

        elif role in ["user", "umurenge_office"]:
            conn = get_db()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM users
                WHERE email = %s AND password = %s AND role = %s
            """, (email, password, role))

            user = cursor.fetchone()
            conn.close()

            if user:
                session.clear()
                session.permanent = False
                session["user_email"] = user[0]  # email is at index 0
                session["user_name"] = user[1]   # name is at index 1
                session["role"] = user[3]        # role is at index 3

                if user[3] == "user":
                    return redirect(url_for("user_dashboard"))

                if user[3] == "umurenge_office":
                    return redirect(url_for("office_dashboard"))
            else:
                error = "Wrong email, password, or role"
        else:
            error = "Please choose a valid role"

    return render_template("login.html", error=error)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    return render_template(
        "admin_dashboard.html",
        services=get_all_services(),
        offices=get_all_offices()
    )

# ---------------- VIEW USERS TABLE ----------------
@app.route("/view_users")
def view_users():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT email, name, role FROM users ORDER BY name ASC")
    users = cursor.fetchall()
    conn.close()

    return render_template("view_users.html", users=users)

# ---------------- ADD OFFICE ----------------
@app.route("/add_office", methods=["POST"])
def add_office():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    if not name or not email or not password:
        return render_template(
            "admin_dashboard.html",
            services=get_all_services(),
            offices=get_all_offices(),
            error="All office fields are required"
        )

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (email, name, password, role)
            VALUES (%s, %s, %s, %s)
        """, (email, name, password, "umurenge_office"))
        conn.commit()
    except psycopg2.IntegrityError:
        conn.close()
        return render_template(
            "admin_dashboard.html",
            services=get_all_services(),
            offices=get_all_offices(),
            error="Office email already exists"
        )

    conn.close()
    return redirect(url_for("admin_dashboard"))

# ---------------- DELETE OFFICE ----------------
@app.route("/delete_office/<path:office_email>")
def delete_office(office_email):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM appointments WHERE office_email = %s", (office_email,))
    cursor.execute("DELETE FROM users WHERE email = %s AND role = 'umurenge_office'", (office_email,))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))

# ---------------- ADD SERVICE ----------------
@app.route("/add_service", methods=["POST"])
def add_service():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    service = request.form.get("service", "").strip()

    if not service:
        return render_template(
            "admin_dashboard.html",
            services=get_all_services(),
            offices=get_all_offices(),
            error="Service name is required"
        )

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO services (service_name) VALUES (%s)", (service,))
        conn.commit()
    except psycopg2.IntegrityError:
        conn.close()
        return render_template(
            "admin_dashboard.html",
            services=get_all_services(),
            offices=get_all_offices(),
            error="Service already exists"
        )

    conn.close()
    return redirect(url_for("admin_dashboard"))

# ---------------- DELETE SERVICE ----------------
@app.route("/delete_service/<int:service_id>")
def delete_service(service_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM appointments WHERE service_id = %s", (service_id,))
    cursor.execute("DELETE FROM services WHERE id = %s", (service_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))

# ---------------- USER DASHBOARD ----------------
@app.route("/user_dashboard")
def user_dashboard():
    if session.get("role") != "user":
        return redirect(url_for("login"))

    user_email = session["user_email"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            appointments.id,
            appointments.date,
            appointments.description,
            appointments.status,
            appointments.office_comment,
            services.service_name AS service_name,
            office.name AS office_name
        FROM appointments
        JOIN services ON appointments.service_id = services.id
        JOIN users AS office ON appointments.office_email = office.email
        WHERE appointments.user_email = %s
        ORDER BY appointments.date ASC, appointments.created_at DESC
    """, (user_email,))
    appointments = cursor.fetchall()

    conn.close()

    return render_template(
        "user_dashboard.html",
        user_name=session["user_name"],
        services=get_all_services(),
        offices=get_all_offices(),
        appointments=appointments,
        tomorrow=tomorrow_date()
    )

# ---------------- BOOK APPOINTMENT ----------------
@app.route("/book_appointment", methods=["POST"])
def book_appointment():
    if session.get("role") != "user":
        return redirect(url_for("login"))

    user_email = session["user_email"]
    office_email = request.form.get("office_email", "").strip()
    service_id = request.form.get("service_id", "").strip()
    selected_date = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    if not office_email or not service_id or not selected_date or not description:
        return "<h3>All booking fields are required.</h3><a href='/user_dashboard'>Back</a>"

    if not is_valid_future_date(selected_date):
        return "<h3>Date must start from tomorrow.</h3><a href='/user_dashboard'>Back</a>"

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO appointments (user_email, office_email, service_id, date, description, status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (user_email, office_email, service_id, selected_date, description, "Pending"))

    conn.commit()
    conn.close()

    return redirect(url_for("user_dashboard"))

# ---------------- CANCEL APPOINTMENT ----------------
@app.route("/cancel_appointment/<int:appointment_id>")
def cancel_appointment(appointment_id):
    if session.get("role") != "user":
        return redirect(url_for("login"))

    user_email = session["user_email"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE appointments
        SET status = 'Cancelled'
        WHERE id = %s AND user_email = %s
    """, (appointment_id, user_email))

    conn.commit()
    conn.close()

    return redirect(url_for("user_dashboard"))

# ---------------- SHIFT APPOINTMENT ----------------
@app.route("/shift_appointment/<int:appointment_id>", methods=["GET", "POST"])
def shift_appointment(appointment_id):
    if session.get("role") != "user":
        return redirect(url_for("login"))

    user_email = session["user_email"]

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        new_date = request.form.get("new_date", "").strip()

        if not new_date:
            conn.close()
            return "<h3>New date is required.</h3><a href='/user_dashboard'>Back</a>"

        if not is_valid_future_date(new_date):
            conn.close()
            return "<h3>New date must start from tomorrow.</h3><a href='/user_dashboard'>Back</a>"

        cursor.execute("""
            UPDATE appointments
            SET date = %s, status = 'Pending'
            WHERE id = %s AND user_email = %s
        """, (new_date, appointment_id, user_email))

        conn.commit()
        conn.close()
        return redirect(url_for("user_dashboard"))

    cursor.execute("""
        SELECT
            appointments.id,
            appointments.date,
            appointments.status,
            appointments.office_comment,
            services.service_name AS service_name,
            office.name AS office_name
        FROM appointments
        JOIN services ON appointments.service_id = services.id
        JOIN users AS office ON appointments.office_email = office.email
        WHERE appointments.id = %s AND appointments.user_email = %s
    """, (appointment_id, user_email))

    appointment = cursor.fetchone()
    conn.close()

    if not appointment:
        return "<h3>Appointment not found.</h3><a href='/user_dashboard'>Back</a>"

    return render_template(
        "shift_appointment.html",
        appointment=appointment,
        tomorrow=tomorrow_date()
    )

# ---------------- OFFICE DASHBOARD ----------------
@app.route("/office_dashboard")
def office_dashboard():
    if session.get("role") != "umurenge_office":
        return redirect(url_for("login"))

    office_email = session["user_email"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            appointments.id,
            user.name AS user_name,
            user.email AS user_email,
            services.service_name AS service,
            appointments.date AS appointment_date,
            appointments.description,
            appointments.status,
            appointments.office_comment,
            appointments.created_at
        FROM appointments
        JOIN users AS user ON appointments.user_email = user.email
        JOIN services ON appointments.service_id = services.id
        WHERE appointments.office_email = %s
        ORDER BY appointments.date ASC, appointments.created_at DESC
    """, (office_email,))
    appointments = cursor.fetchall()

    conn.close()

    return render_template(
        "office_dashboard.html",
        office_name=session["user_name"],
        appointments=appointments
    )

# ---------------- VIEW APPOINTMENT ----------------
@app.route("/view_appointment/<int:appointment_id>")
def view_appointment(appointment_id):
    if session.get("role") != "umurenge_office":
        return redirect(url_for("login"))

    office_email = session["user_email"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            appointments.id,
            user.name AS user_name,
            user.email AS user_email,
            services.service_name AS service,
            appointments.date AS appointment_date,
            appointments.description,
            appointments.status,
            appointments.office_comment,
            appointments.created_at
        FROM appointments
        JOIN users AS user ON appointments.user_email = user.email
        JOIN services ON appointments.service_id = services.id
        WHERE appointments.id = %s AND appointments.office_email = %s
    """, (appointment_id, office_email))

    appointment = cursor.fetchone()
    conn.close()

    if not appointment:
        return "<h3>Appointment not found.</h3><a href='/office_dashboard'>Back</a>"

    return render_template("appointment_details.html", appointment=appointment)

# ---------------- APPROVE ----------------
@app.route("/approve/<int:appointment_id>", methods=["POST"])
def approve_appointment(appointment_id):
    if session.get("role") != "umurenge_office":
        return redirect(url_for("login"))

    office_email = session["user_email"]
    comment = request.form.get("comment", "").strip()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE appointments
        SET status = 'Approved', office_comment = %s
        WHERE id = %s AND office_email = %s
    """, (comment, appointment_id, office_email))

    conn.commit()
    conn.close()

    return redirect(url_for("office_dashboard"))

# ---------------- REJECT ----------------
@app.route("/reject/<int:appointment_id>", methods=["POST"])
def reject_appointment(appointment_id):
    if session.get("role") != "umurenge_office":
        return redirect(url_for("login"))

    office_email = session["user_email"]
    comment = request.form.get("comment", "").strip()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE appointments
        SET status = 'Rejected', office_comment = %s
        WHERE id = %s AND office_email = %s
    """, (comment, appointment_id, office_email))

    conn.commit()
    conn.close()

    return redirect(url_for("office_dashboard"))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)