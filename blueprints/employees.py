from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from utils.auth_utils import role_required
from utils.db_utils import require_tenant_id
from database import get_connection

employees_bp = Blueprint("employees", __name__)

def _employee_form_data():
    return {
        "employee_id": request.form.get("employee_id", "").strip(),
        "name": request.form.get("name", "").strip(),
        "department": request.form.get("department", "").strip(),
        "designation": request.form.get("designation", "").strip(),
        "email": request.form.get("email", "").strip(),
        "phone": request.form.get("phone", "").strip(),
        "join_date": request.form.get("join_date", "").strip(),
    }


def _employee_id_exists(conn, tenant_id, employee_code, record_id=None):
    query = "SELECT id FROM employees WHERE LOWER(employee_id) = LOWER(?)"
    params = [employee_code]

    if tenant_id is not None:
        query += " AND tenant_id = ?"
        params.append(tenant_id)

    if record_id is not None:
        query += " AND id != ?"
        params.append(record_id)

    cursor = conn.cursor()
    cursor.execute(query, params)
    return cursor.fetchone() is not None


def _fetch_employees(conn, tenant_id, search=""):
    query = "SELECT * FROM employees"
    params = []
    filters = []

    if tenant_id is not None:
        filters.append("tenant_id = ?")
        params.append(tenant_id)

    if search:
        filters.append(
            """(
                employee_id LIKE ?
                OR name LIKE ?
                OR department LIKE ?
                OR designation LIKE ?
                OR email LIKE ?
                OR phone LIKE ?
            )"""
        )
        search_value = f"%{search}%"
        params.extend([search_value] * 6)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY id DESC"

    cursor = conn.cursor()
    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


def _get_employee(conn, tenant_id, record_id):
    query = "SELECT * FROM employees WHERE id = ?"
    params = [record_id]

    if tenant_id is not None:
        query += " AND tenant_id = ?"
        params.append(tenant_id)

    cursor = conn.cursor()
    cursor.execute(query, params)
    employee = cursor.fetchone()
    return dict(employee) if employee else None


def _employee_stats(conn, tenant_id):
    params = []
    where_clause = ""

    if tenant_id is not None:
        where_clause = "WHERE tenant_id = ?"
        params.append(tenant_id)

    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) AS total FROM employees {where_clause}", params)
    total = cursor.fetchone()["total"]

    cursor.execute(
        f"""
        SELECT COUNT(DISTINCT department) AS total
        FROM employees
        {where_clause}
        AND department IS NOT NULL
        AND department != ''
        """
        if where_clause
        else """
        SELECT COUNT(DISTINCT department) AS total
        FROM employees
        WHERE department IS NOT NULL
        AND department != ''
        """,
        params,
    )
    departments = cursor.fetchone()["total"]

    return {
        "total_employees": total,
        "department_count": departments,
    }


@employees_bp.route("/employees", methods=["GET", "POST"])
@role_required(['admin', 'manager'])
def employees():
    conn = get_connection()
    tenant_id = require_tenant_id()

    if request.method == "POST":
        data = _employee_form_data()

        if not data["employee_id"] or not data["name"]:
            flash("Employee ID and name are required.", "danger")
        elif _employee_id_exists(conn, tenant_id, data["employee_id"]):
            flash("An employee with this Employee ID already exists.", "danger")
        else:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO employees
                (tenant_id, employee_id, name, department, designation, email, phone, join_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    data["employee_id"],
                    data["name"],
                    data["department"],
                    data["designation"],
                    data["email"],
                    data["phone"],
                    data["join_date"],
                ),
            )
            conn.commit()
            conn.close()
            flash("Employee saved successfully.", "success")
            return redirect(url_for("employees.employees"))

    search = request.args.get("search", "").strip()
    employees_list = _fetch_employees(conn, tenant_id, search)
    stats = _employee_stats(conn, tenant_id)
    conn.close()

    return render_template(
        "employees/employees.html",
        employees=employees_list,
        search=search,
        edit_employee=None,
        **stats,
    )


@employees_bp.route("/employees/<int:record_id>/edit")
@role_required(['admin', 'manager'])
def edit_employee(record_id):
    conn = get_connection()
    tenant_id = require_tenant_id()
    employee = _get_employee(conn, tenant_id, record_id)

    if employee is None:
        conn.close()
        flash("Employee not found.", "danger")
        return redirect(url_for("employees.employees"))

    search = request.args.get("search", "").strip()
    employees_list = _fetch_employees(conn, tenant_id, search)
    stats = _employee_stats(conn, tenant_id)
    conn.close()

    return render_template(
        "employees/employees.html",
        employees=employees_list,
        search=search,
        edit_employee=employee,
        **stats,
    )


@employees_bp.route("/employees/<int:record_id>/update", methods=["POST"])
@role_required(['admin'])
def update_employee(record_id):
    conn = get_connection()
    tenant_id = require_tenant_id()
    employee = _get_employee(conn, tenant_id, record_id)

    if employee is None:
        conn.close()
        flash("Employee not found.", "danger")
        return redirect(url_for("employees.employees"))

    data = _employee_form_data()

    if not data["employee_id"] or not data["name"]:
        conn.close()
        flash("Employee ID and name are required.", "danger")
        return redirect(url_for("employees.edit_employee", record_id=record_id))

    if _employee_id_exists(conn, tenant_id, data["employee_id"], record_id):
        conn.close()
        flash("An employee with this Employee ID already exists.", "danger")
        return redirect(url_for("employees.edit_employee", record_id=record_id))

    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE employees
        SET employee_id = ?,
            name = ?,
            department = ?,
            designation = ?,
            email = ?,
            phone = ?,
            join_date = ?
        WHERE id = ?
        """
        + (" AND tenant_id = ?" if tenant_id is not None else ""),
        (
            data["employee_id"],
            data["name"],
            data["department"],
            data["designation"],
            data["email"],
            data["phone"],
            data["join_date"],
            record_id,
            *([tenant_id] if tenant_id is not None else []),
        ),
    )
    conn.commit()
    conn.close()

    flash("Employee updated successfully.", "success")
    return redirect(url_for("employees.employees"))


@employees_bp.route("/employees/<int:record_id>/delete", methods=["POST"])
@role_required(['admin'])
def delete_employee(record_id):
    conn = get_connection()
    tenant_id = require_tenant_id()
    employee = _get_employee(conn, tenant_id, record_id)

    if employee is None:
        conn.close()
        flash("Employee not found.", "danger")
        return redirect(url_for("employees.employees"))

    query = "DELETE FROM employees WHERE id = ?"
    params = [record_id]

    if tenant_id is not None:
        query += " AND tenant_id = ?"
        params.append(tenant_id)

    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

    flash("Employee deleted successfully.", "success")
    return redirect(url_for("employees.employees"))
