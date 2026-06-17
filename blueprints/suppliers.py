from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from utils.auth_utils import role_required
from utils.db_utils import require_tenant_id
from database import get_connection
from utils.notification_utils import add_notification

suppliers_bp = Blueprint("suppliers", __name__)

def _supplier_form_data():
    return {
        "supplier_name": request.form.get("supplier_name", "").strip(),
        "contact_person": request.form.get("contact_person", "").strip(),
        "email": request.form.get("email", "").strip(),
        "phone": request.form.get("phone", "").strip(),
        "address": request.form.get("address", "").strip(),
    }

def _fetch_suppliers(conn, tenant_id, search=""):
    query = "SELECT * FROM suppliers"
    params = []
    filters = []

    if tenant_id is not None:
        filters.append("tenant_id = ?")
        params.append(tenant_id)

    if search:
        filters.append("(supplier_name LIKE ? OR contact_person LIKE ? OR email LIKE ?)")
        search_value = f"%{search}%"
        params.extend([search_value] * 3)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY id DESC"
    cursor = conn.cursor()
    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]

@suppliers_bp.route("/suppliers", methods=["GET", "POST"])
@role_required(['admin', 'manager', 'employee'])
def suppliers():
    conn = get_connection()
    tenant_id = require_tenant_id()

    if request.method == "POST":
        if session.get('role') not in ['admin', 'manager']:
            flash("You do not have permission to modify suppliers.", "danger")
            return redirect(url_for("suppliers.suppliers"))

        data = _supplier_form_data()
        if not data["supplier_name"]:
            flash("Supplier name is required.", "danger")
        else:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO suppliers (tenant_id, supplier_name, contact_person, email, phone, address)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (tenant_id, data["supplier_name"], data["contact_person"], data["email"], data["phone"], data["address"]),
            )
            conn.commit()
            
            # Notification
            add_notification(tenant_id, f"New Supplier Added: {data['supplier_name']}", "success")
            
            flash("Supplier registered successfully.", "success")
            return redirect(url_for("suppliers.suppliers"))

    search = request.args.get("search", "").strip()
    suppliers_list = _fetch_suppliers(conn, tenant_id, search)
    
    # Calculate stats
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM suppliers WHERE tenant_id = ?", (tenant_id,))
    total_suppliers = cursor.fetchone()["total"]

    conn.close()

    return render_template(
        "suppliers/suppliers.html",
        suppliers=suppliers_list,
        total_suppliers=total_suppliers,
        search=search,
        edit_supplier=None,
    )

@suppliers_bp.route("/suppliers/<int:record_id>/edit")
@role_required(['admin', 'manager'])
def edit_supplier(record_id):
    conn = get_connection()
    tenant_id = require_tenant_id()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM suppliers WHERE id = ? AND tenant_id = ?", (record_id, tenant_id))
    supplier = cursor.fetchone()
    
    search = request.args.get("search", "").strip()
    suppliers_list = _fetch_suppliers(conn, tenant_id, search)
    
    cursor.execute("SELECT COUNT(*) as total FROM suppliers WHERE tenant_id = ?", (tenant_id,))
    total_suppliers = cursor.fetchone()["total"]
    
    conn.close()

    return render_template(
        "suppliers/suppliers.html",
        suppliers=suppliers_list,
        total_suppliers=total_suppliers,
        search=search,
        edit_supplier=dict(supplier) if supplier else None,
    )

@suppliers_bp.route("/suppliers/<int:record_id>/update", methods=["POST"])
@role_required(['admin', 'manager'])
def update_supplier(record_id):
    conn = get_connection()
    tenant_id = require_tenant_id()
    
    data = _supplier_form_data()
    if not data["supplier_name"]:
        flash("Supplier name is required.", "danger")
        return redirect(url_for("suppliers.edit_supplier", record_id=record_id))

    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE suppliers
        SET supplier_name = ?, contact_person = ?, email = ?, phone = ?, address = ?
        WHERE id = ? AND tenant_id = ?
        """,
        (data["supplier_name"], data["contact_person"], data["email"], data["phone"], data["address"], record_id, tenant_id),
    )
    conn.commit()
    conn.close()
    flash("Supplier updated successfully.", "success")
    return redirect(url_for("suppliers.suppliers"))

@suppliers_bp.route("/suppliers/<int:record_id>/delete", methods=["POST"])
@role_required(['admin'])
def delete_supplier(record_id):
    conn = get_connection()
    tenant_id = require_tenant_id()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM suppliers WHERE id = ? AND tenant_id = ?", (record_id, tenant_id))
    conn.commit()
    conn.close()
    flash("Supplier deleted successfully.", "success")
    return redirect(url_for("suppliers.suppliers"))
