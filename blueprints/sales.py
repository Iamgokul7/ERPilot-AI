from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from database import get_connection
from utils.db_utils import require_tenant_id
from utils.notification_utils import add_notification
from utils.auth_utils import role_required
from datetime import date

sales_bp = Blueprint("sales", __name__)

def _fetch_sales_orders(conn, tenant_id, search=""):
    query = """
        SELECT o.*, p.product_name, p.sku
        FROM sales_orders o
        LEFT JOIN products p ON o.product_id = p.id
    """
    params = []
    filters = []

    if tenant_id is not None:
        filters.append("o.tenant_id = ?")
        params.append(tenant_id)

    if search:
        filters.append("(o.order_number LIKE ? OR o.customer_name LIKE ? OR p.product_name LIKE ?)")
        search_val = f"%{search}%"
        params.extend([search_val] * 3)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY o.id DESC"
    cursor = conn.cursor()
    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]

@sales_bp.route("", methods=["GET", "POST"])
@role_required(['admin', 'manager', 'employee'])
def sales():
    conn = get_connection()
    tenant_id = require_tenant_id()

    if request.method == "POST":
        if session.get('role') not in ['admin', 'manager']:
            flash("You do not have permission to create sales orders.", "danger")
            return redirect(url_for("sales.sales"))
        
        order_number = request.form.get("order_number", "").strip()
        customer_name = request.form.get("customer_name", "").strip()
        product_id = request.form.get("product_id")
        quantity = int(request.form.get("quantity", 1))
        order_date = request.form.get("order_date", date.today().isoformat()).strip()
        status = request.form.get("status", "pending").strip()

        if not order_number or not customer_name or not product_id:
            flash("Order number, customer name, and product are required.", "danger")
            return redirect(url_for("sales.sales"))
        else:
            cursor = conn.cursor()
            
            # Fetch product for price and stock verification
            cursor.execute("SELECT * FROM products WHERE id = ? AND tenant_id = ?", (product_id, tenant_id))
            product = cursor.fetchone()
            
            if not product:
                flash("Selected product not found.", "danger")
                return redirect(url_for("sales.sales"))
            elif product["quantity"] < quantity:
                flash(f"Insufficient stock. Only {product['quantity']} available for '{product['product_name']}'.", "danger")
                return redirect(url_for("sales.sales"))
            else:
                total_amount = round(product["unit_price"] * quantity, 2)
                
                # Insert order
                cursor.execute("""
                    INSERT INTO sales_orders (tenant_id, order_number, customer_name, product_id, quantity, total_amount, order_date, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (tenant_id, order_number, customer_name, product_id, quantity, total_amount, order_date, status))
                
                # Deduct inventory stock
                new_qty = product["quantity"] - quantity
                cursor.execute("UPDATE products SET quantity = ? WHERE id = ?", (new_qty, product_id))
                
                conn.commit()

                # Add notifications
                add_notification(tenant_id, f"New Order Created: {order_number} for {customer_name}", "success")
                
                if new_qty <= product["reorder_level"]:
                    add_notification(
                        tenant_id, 
                        f"Low Stock Alert: {product['product_name']} (Stock: {new_qty}, Reorder Level: {product['reorder_level']})", 
                        "warning"
                    )
                
                flash("Sales order created successfully.", "success")
                return redirect(url_for("sales.sales"))

    search = request.args.get("search", "").strip()
    orders_list = _fetch_sales_orders(conn, tenant_id, search)
    
    # Calculate stats
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM sales_orders WHERE tenant_id = ?", (tenant_id,))
    total_orders = cursor.fetchone()["total"] or 0
    
    cursor.execute("SELECT SUM(total_amount) as total_rev FROM sales_orders WHERE tenant_id = ? AND status = 'completed'", (tenant_id,))
    total_rev = cursor.fetchone()["total_rev"] or 0.0

    cursor.execute("SELECT COUNT(*) as pending FROM sales_orders WHERE tenant_id = ? AND status = 'pending'", (tenant_id,))
    pending_count = cursor.fetchone()["pending"] or 0

    stats = {
        "total_orders": total_orders,
        "total_revenue": f"${total_rev:,.2f}",
        "pending_orders": pending_count,
    }

    # Fetch products for selection
    cursor.execute("SELECT id, product_name, sku, quantity, unit_price FROM products WHERE tenant_id = ? ORDER BY product_name", (tenant_id,))
    products_list = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return render_template(
        "sales/sales.html",
        sales=orders_list,
        products=products_list,
        search=search,
        today=date.today().isoformat(),
        edit_order=None,
        **stats,
    )

@sales_bp.route("/<int:record_id>/edit")
@role_required(['admin', 'manager'])
def edit_order(record_id):
    conn = get_connection()
    tenant_id = require_tenant_id()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM sales_orders WHERE id = ? AND tenant_id = ?", (record_id, tenant_id))
    order = cursor.fetchone()
    if not order:
        conn.close()
        flash("Order not found.", "danger")
        return redirect(url_for("sales.sales"))

    search = request.args.get("search", "").strip()
    orders_list = _fetch_sales_orders(conn, tenant_id, search)
    
    # Calculate stats
    cursor.execute("SELECT COUNT(*) as total FROM sales_orders WHERE tenant_id = ?", (tenant_id,))
    total_orders = cursor.fetchone()["total"] or 0
    cursor.execute("SELECT SUM(total_amount) as total_rev FROM sales_orders WHERE tenant_id = ? AND status = 'completed'", (tenant_id,))
    total_rev = cursor.fetchone()["total_rev"] or 0.0
    cursor.execute("SELECT COUNT(*) as pending FROM sales_orders WHERE tenant_id = ? AND status = 'pending'", (tenant_id,))
    pending_count = cursor.fetchone()["pending"] or 0

    stats = {
        "total_orders": total_orders,
        "total_revenue": f"${total_rev:,.2f}",
        "pending_orders": pending_count,
    }

    cursor.execute("SELECT id, product_name, sku, quantity, unit_price FROM products WHERE tenant_id = ? ORDER BY product_name", (tenant_id,))
    products_list = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return render_template(
        "sales/sales.html",
        sales=orders_list,
        products=products_list,
        search=search,
        today=date.today().isoformat(),
        edit_order=dict(order),
        **stats,
    )

@sales_bp.route("/<int:record_id>/update", methods=["POST"])
@role_required(['admin', 'manager'])
def update_order(record_id):
    conn = get_connection()
    tenant_id = require_tenant_id()
    cursor = conn.cursor()
    
    # Get current order details to restore stock before validation
    cursor.execute("SELECT * FROM sales_orders WHERE id = ? AND tenant_id = ?", (record_id, tenant_id))
    current_order = cursor.fetchone()
    if not current_order:
        conn.close()
        flash("Order not found.", "danger")
        return redirect(url_for("sales.sales"))
        
    order_number = request.form.get("order_number", "").strip()
    customer_name = request.form.get("customer_name", "").strip()
    product_id = request.form.get("product_id")
    quantity = int(request.form.get("quantity", 1))
    order_date = request.form.get("order_date").strip()
    status = request.form.get("status", "pending").strip()

    # Get target product
    cursor.execute("SELECT * FROM products WHERE id = ? AND tenant_id = ?", (product_id, tenant_id))
    product = cursor.fetchone()
    
    if not product:
        flash("Product not found.", "danger")
        conn.close()
        return redirect(url_for("sales.edit_order", record_id=record_id))
        
    # Available stock calculation
    # Add back the previous order quantity if product is the same
    available_stock = product["quantity"]
    if current_order["product_id"] == int(product_id):
        available_stock += current_order["quantity"]
        
    if available_stock < quantity:
        flash(f"Insufficient stock. Only {available_stock} available for '{product['product_name']}'.", "danger")
        conn.close()
        return redirect(url_for("sales.edit_order", record_id=record_id))
        
    # Revert stock on the original product
    cursor.execute("UPDATE products SET quantity = quantity + ? WHERE id = ?", (current_order["quantity"], current_order["product_id"]))
    # Deduct stock on the new product
    cursor.execute("UPDATE products SET quantity = quantity - ? WHERE id = ?", (quantity, product_id))
    
    # Recalculate total_amount
    total_amount = round(product["unit_price"] * quantity, 2)
    
    cursor.execute("""
        UPDATE sales_orders
        SET order_number = ?,
            customer_name = ?,
            product_id = ?,
            quantity = ?,
            total_amount = ?,
            order_date = ?,
            status = ?
        WHERE id = ? AND tenant_id = ?
    """, (order_number, customer_name, product_id, quantity, total_amount, order_date, status, record_id, tenant_id))
    
    conn.commit()
    conn.close()
    
    flash("Sales order updated successfully.", "success")
    return redirect(url_for("sales.sales"))

@sales_bp.route("/<int:record_id>/status", methods=["POST"])
@role_required(['admin', 'manager'])
def update_status(record_id):
    new_status = request.form.get("status")
    conn = get_connection()
    tenant_id = require_tenant_id()
    cursor = conn.cursor()

    cursor.execute("UPDATE sales_orders SET status = ? WHERE id = ? AND tenant_id = ?", (new_status, record_id, tenant_id))
    conn.commit()
    conn.close()
    flash(f"Order status updated to {new_status}.", "success")
    return redirect(url_for("sales.sales"))

@sales_bp.route("/<int:record_id>/delete", methods=["POST"])
@role_required(['admin'])
def delete_order(record_id):
    conn = get_connection()
    tenant_id = require_tenant_id()
    cursor = conn.cursor()
    
    # Get order to restore stock
    cursor.execute("SELECT * FROM sales_orders WHERE id = ? AND tenant_id = ?", (record_id, tenant_id))
    order = cursor.fetchone()
    if order:
        cursor.execute("UPDATE products SET quantity = quantity + ? WHERE id = ?", (order["quantity"], order["product_id"]))
        cursor.execute("DELETE FROM sales_orders WHERE id = ? AND tenant_id = ?", (record_id, tenant_id))
        conn.commit()
        
    conn.close()
    flash("Sales order deleted and inventory restored.", "success")
    return redirect(url_for("sales.sales"))
