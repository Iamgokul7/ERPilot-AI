from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        )

        user = cursor.fetchone()

        conn.close()

        if user and check_password_hash(
            user["password_hash"],
            password
        ):

            session["user_id"] = user["id"]
            session["tenant_id"] = user["tenant_id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]

            return redirect("/dashboard")

        return "Invalid Email or Password"

    return render_template("auth/login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        company_name = request.form["company_name"]
        company_email = request.form["company_email"]

        admin_name = request.form["admin_name"]
        admin_email = request.form["admin_email"]

        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return "Passwords do not match"

        password_hash = generate_password_hash(password)

        slug = company_name.lower().replace(" ", "-")

        conn = get_connection()
        cursor = conn.cursor()

        # Create Tenant
        cursor.execute("""
            INSERT INTO tenants
            (company_name, company_email, slug)
            VALUES (?, ?, ?)
        """, (
            company_name,
            company_email,
            slug
        ))

        tenant_id = cursor.lastrowid

        # Create Admin User
        cursor.execute("""
            INSERT INTO users
            (tenant_id, name, email, password_hash, role)
            VALUES (?, ?, ?, ?, ?)
        """, (
            tenant_id,
            admin_name,
            admin_email,
            password_hash,
            "admin"
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))