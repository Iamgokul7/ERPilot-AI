from database import get_connection

def add_notification(tenant_id, message, msg_type="info"):
    """
    Adds a notification for a specific tenant.
    msg_type can be 'info', 'warning', 'error', 'success'
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO notifications (tenant_id, message, type)
        VALUES (?, ?, ?)
    """, (tenant_id, message, msg_type))
    conn.commit()
    conn.close()

def check_low_stock(tenant_id):
    """
    Checks for products where quantity is below reorder_level.
    Returns a list of low stock items and creates notifications if they don't exist? 
    Actually, let's just make it return the items for now.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT product_name, quantity, reorder_level 
        FROM products 
        WHERE tenant_id = ? AND quantity <= reorder_level
    """, (tenant_id,))
    low_stock_items = cursor.fetchall()
    conn.close()
    return low_stock_items
