from flask import Blueprint, render_template, session
from utils.db_utils import require_tenant_id
from database import get_connection

dashboard_bp = Blueprint("dashboard", __name__)

def _count_records(cursor, table_name, tenant_id):
    cursor.execute(
        f"SELECT COUNT(*) AS total FROM {table_name} WHERE tenant_id = ?",
        (tenant_id,),
    )
    return cursor.fetchone()["total"]

@dashboard_bp.route("/dashboard")
def dashboard():
    tenant_id = require_tenant_id()
    conn = get_connection()
    cursor = conn.cursor()

    company_name = "Acme Enterprise Solutions"
    if tenant_id is not None:
        cursor.execute("SELECT company_name FROM tenants WHERE id = ?", (tenant_id,))
        tenant = cursor.fetchone()
        if tenant:
            company_name = tenant["company_name"]

    # 1. Base Metrics
    metrics = {
        "employee_count": _count_records(cursor, "employees", tenant_id),
        "product_count": _count_records(cursor, "products", tenant_id),
        "supplier_count": _count_records(cursor, "suppliers", tenant_id),
        "order_count": _count_records(cursor, "sales_orders", tenant_id),
    }

    # 2. Revenue calculation
    cursor.execute("SELECT SUM(total_amount) AS revenue FROM sales_orders WHERE tenant_id = ? AND status = 'completed'", (tenant_id,))
    total_rev = cursor.fetchone()["revenue"] or 0.0
    metrics["total_revenue"] = f"${total_rev:,.2f}"

    # 3. Low stock items
    cursor.execute("SELECT COUNT(*) AS low_stock FROM products WHERE tenant_id = ? AND quantity <= reorder_level", (tenant_id,))
    metrics["low_stock_count"] = cursor.fetchone()["low_stock"]

    # 4. Alert notifications count
    cursor.execute("SELECT COUNT(*) AS total FROM notifications WHERE tenant_id = ? AND is_read = 0", (tenant_id,))
    metrics["alert_count"] = cursor.fetchone()["total"]

    # 5. Monthly Revenue Trends
    cursor.execute("""
        SELECT order_date, total_amount
        FROM sales_orders
        WHERE tenant_id = ? AND status = 'completed'
    """, (tenant_id,))
    orders_data = cursor.fetchall()
    monthly_sales = {i: 0.0 for i in range(1, 13)}
    months_abbr = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    for row in orders_data:
        try:
            dt_str = row["order_date"]
            month = int(dt_str.split("-")[1])
            monthly_sales[month] += row["total_amount"]
        except Exception:
            pass
            
    sales_labels = months_abbr
    sales_values = [monthly_sales[i] for i in range(1, 13)]
    any_sales = len(orders_data) > 0

    # 6. Product Stock distribution by category
    cursor.execute("""
        SELECT category, SUM(quantity) as total_qty
        FROM products
        WHERE tenant_id = ?
        GROUP BY category
    """, (tenant_id,))
    cat_data = cursor.fetchall()
    inventory_labels = [row["category"] or "Uncategorized" for row in cat_data]
    inventory_values = [row["total_qty"] for row in cat_data]

    # 7. Recent Orders
    cursor.execute("""
        SELECT o.*, p.product_name
        FROM sales_orders o
        LEFT JOIN products p ON o.product_id = p.id
        WHERE o.tenant_id = ?
        ORDER BY o.id DESC
        LIMIT 5
    """, (tenant_id,))
    recent_sales = [dict(row) for row in cursor.fetchall()]

    # 8. Activity Timeline
    activities = []
    # Recent sales orders
    cursor.execute("""
        SELECT 'order' as type, order_number, customer_name, total_amount, order_date as activity_date
        FROM sales_orders
        WHERE tenant_id = ?
        ORDER BY id DESC LIMIT 5
    """, (tenant_id,))
    for row in cursor.fetchall():
        activities.append({
            "type": "order",
            "message": f"Sales Order {row['order_number']} created for {row['customer_name']} (${row['total_amount']:,.2f})",
            "date": row["activity_date"]
        })
    # Recent notifications
    cursor.execute("""
        SELECT 'notification' as type, message, created_at as activity_date
        FROM notifications
        WHERE tenant_id = ?
        ORDER BY id DESC LIMIT 5
    """, (tenant_id,))
    for row in cursor.fetchall():
        activities.append({
            "type": "notification",
            "message": row["message"],
            "date": row["activity_date"]
        })
    # Sort activities by date descending
    activities.sort(key=lambda x: x["date"], reverse=True)
    activities = activities[:8]

    conn.close()

    return render_template(
        "dashboard/dashboard.html",
        company_name=company_name,
        sales_labels=sales_labels,
        sales_values=sales_values,
        inventory_labels=inventory_labels,
        inventory_values=inventory_values,
        recent_sales=recent_sales,
        any_sales=any_sales,
        activities=activities,
        **metrics,
    )
