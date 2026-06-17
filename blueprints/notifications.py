from flask import Blueprint, jsonify, session, request
from utils.db_utils import require_tenant_id
from database import get_connection
from utils.auth_utils import role_required

notifications_bp = Blueprint("notifications", __name__)

@notifications_bp.route("/notifications")
@role_required(['admin', 'manager', 'employee'])
def get_notifications():
    tenant_id = require_tenant_id()
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM notifications 
        WHERE tenant_id = ? 
        ORDER BY created_at DESC 
        LIMIT 10
    """, (tenant_id,))
    
    notifications = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(notifications)

@notifications_bp.route("/notifications/mark-read", methods=["POST"])
@role_required(['admin', 'manager', 'employee'])
def mark_read():
    tenant_id = require_tenant_id()
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE tenant_id = ?", (tenant_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success"})
