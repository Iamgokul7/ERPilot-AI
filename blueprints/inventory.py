from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from utils.auth_utils import role_required
from utils.db_utils import require_tenant_id
from database import get_connection
from utils.notification_utils import add_notification

inventory_bp = Blueprint("inventory", __name__)

def _product_form_data():
    return {
        "product_name": request.form.get("product_name", "").strip(),
        "sku": request.form.get("sku", "").strip(),
        "category": request.form.get("category", "").strip(),
        "quantity": int(request.form.get("quantity", 0)),
        "unit_price": float(request.form.get("unit_price", 0.0)),
        "reorder_level": int(request.form.get("reorder_level", 10)),
    }

def _fetch_products(conn, tenant_id, search=""):
    query = "SELECT * FROM products"
    params = []
    filters = []

    if tenant_id is not None:
        filters.append("tenant_id = ?")
        params.append(tenant_id)

    if search:
        filters.append("(product_name LIKE ? OR sku LIKE ? OR category LIKE ?)")
        search_value = f"%{search}%"
        params.extend([search_value] * 3)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY id DESC"
    cursor = conn.cursor()
    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]

def _get_product(conn, tenant_id, record_id):
    query = "SELECT * FROM products WHERE id = ?"
    params = [record_id]

    if tenant_id is not None:
        query += " AND tenant_id = ?"
        params.append(tenant_id)

    cursor = conn.cursor()
    cursor.execute(query, params)
    product = cursor.fetchone()
    return dict(product) if product else None

def _inventory_stats(conn, tenant_id):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM products WHERE tenant_id = ?", (tenant_id,))
    total_products = cursor.fetchone()["total"]

    cursor.execute("SELECT SUM(quantity * unit_price) as total_val FROM products WHERE tenant_id = ?", (tenant_id,))
    total_val = cursor.fetchone()["total_val"] or 0.0

    cursor.execute("SELECT COUNT(*) as low_stock FROM products WHERE tenant_id = ? AND quantity <= reorder_level", (tenant_id,))
    low_stock = cursor.fetchone()["low_stock"]

    return {
        "total_products": total_products,
        "total_inventory_value": f"${total_val:,.2f}",
        "low_stock_count": low_stock,
    }

@inventory_bp.route("/inventory", methods=["GET", "POST"])
@role_required(['admin', 'manager', 'employee'])
def inventory():
    conn = get_connection()
    tenant_id = require_tenant_id()

    if request.method == "POST":
        if session.get('role') not in ['admin', 'manager']:
            flash("You do not have permission to modify inventory.", "danger")
            return redirect(url_for("inventory.inventory"))

        data = _product_form_data()
        if not data["product_name"] or not data["sku"]:
            flash("Product name and SKU are required.", "danger")
        else:
            # Check SKU uniqueness for tenant
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM products WHERE tenant_id = ? AND sku = ?", (tenant_id, data["sku"]))
            existing = cursor.fetchone()
            if existing:
                flash(f"SKU '{data['sku']}' already exists.", "danger")
            else:
                cursor.execute(
                    """
                    INSERT INTO products
                    (tenant_id, product_name, sku, category, quantity, unit_price, reorder_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tenant_id,
                        data["product_name"],
                        data["sku"],
                        data["category"],
                        data["quantity"],
                        data["unit_price"],
                        data["reorder_level"],
                    ),
                )
                conn.commit()
                
                # Check low-stock alert
                if data["quantity"] <= data["reorder_level"]:
                    add_notification(
                        tenant_id, 
                        f"Low Stock Alert: {data['product_name']} (Stock: {data['quantity']}, Reorder Level: {data['reorder_level']})", 
                        "warning"
                    )
                
                flash("Product added successfully.", "success")
                return redirect(url_for("inventory.inventory"))

    search = request.args.get("search", "").strip()
    products_list = _fetch_products(conn, tenant_id, search)
    stats = _inventory_stats(conn, tenant_id)

    conn.close()

    return render_template(
        "inventory/inventory.html",
        products=products_list,
        search=search,
        edit_product=None,
        **stats,
    )

@inventory_bp.route("/inventory/<int:record_id>/edit")
@role_required(['admin', 'manager'])
def edit_product(record_id):
    conn = get_connection()
    tenant_id = require_tenant_id()
    product = _get_product(conn, tenant_id, record_id)

    if not product:
        conn.close()
        flash("Product not found.", "danger")
        return redirect(url_for("inventory.inventory"))

    search = request.args.get("search", "").strip()
    products_list = _fetch_products(conn, tenant_id, search)
    stats = _inventory_stats(conn, tenant_id)

    conn.close()

    return render_template(
        "inventory/inventory.html",
        products=products_list,
        search=search,
        edit_product=product,
        **stats,
    )

@inventory_bp.route("/inventory/<int:record_id>/update", methods=["POST"])
@role_required(['admin', 'manager'])
def update_product(record_id):
    conn = get_connection()
    tenant_id = require_tenant_id()
    
    data = _product_form_data()
    if not data["product_name"] or not data["sku"]:
        flash("Product name and SKU are required.", "danger")
        return redirect(url_for("inventory.edit_product", record_id=record_id))

    cursor = conn.cursor()
    
    # Check SKU uniqueness for other products
    cursor.execute("SELECT id FROM products WHERE tenant_id = ? AND sku = ? AND id != ?", (tenant_id, data["sku"], record_id))
    existing = cursor.fetchone()
    if existing:
        flash(f"SKU '{data['sku']}' is already in use by another product.", "danger")
        return redirect(url_for("inventory.edit_product", record_id=record_id))

    query = """
        UPDATE products
        SET product_name = ?,
            sku = ?,
            category = ?,
            quantity = ?,
            unit_price = ?,
            reorder_level = ?
        WHERE id = ? AND tenant_id = ?
    """
    cursor.execute(query, (
        data["product_name"],
        data["sku"],
        data["category"],
        data["quantity"],
        data["unit_price"],
        data["reorder_level"],
        record_id,
        tenant_id,
    ))
    conn.commit()

    # Check low-stock alert
    if data["quantity"] <= data["reorder_level"]:
        add_notification(
            tenant_id, 
            f"Low Stock Alert: {data['product_name']} (Stock: {data['quantity']}, Reorder Level: {data['reorder_level']})", 
            "warning"
        )

    conn.close()

    flash("Product updated successfully.", "success")
    return redirect(url_for("inventory.inventory"))

@inventory_bp.route("/inventory/<int:record_id>/delete", methods=["POST"])
@role_required(['admin'])
def delete_product(record_id):
    conn = get_connection()
    tenant_id = require_tenant_id()

    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ? AND tenant_id = ?", (record_id, tenant_id))
    conn.commit()
    conn.close()

    flash("Product deleted successfully.", "success")
    return redirect(url_for("inventory.inventory"))
