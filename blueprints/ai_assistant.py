from flask import Blueprint, render_template, request, jsonify, session
from utils.auth_utils import role_required
from utils.db_utils import require_tenant_id
from database import get_connection
from utils.ai_utils import generate_ai_response

ai_assistant_bp = Blueprint("ai_assistant", __name__)

@ai_assistant_bp.route("/ai-assistant")
@role_required(['admin', 'manager', 'employee'])
def chat_page():
    tenant_id = require_tenant_id()
    return render_template("ai_assistant/chat.html")

@ai_assistant_bp.route("/ai-assistant/chat", methods=["POST"])
@role_required(['admin', 'manager', 'employee'])
def chat():
    tenant_id = require_tenant_id()
    user_id = session.get("user_id")
    user_message = request.json.get("message")
    
    if not user_message:
        return jsonify({"response": "Please type a message."})
    
    # Generate response
    response = generate_ai_response(tenant_id, user_message)
    
    # Log query and response in ai_logs
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO ai_logs (tenant_id, user_id, query, response)
            VALUES (?, ?, ?, ?)
            """,
            (tenant_id, user_id, user_message, response)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error writing to ai_logs: {e}")
    finally:
        conn.close()
    
    return jsonify({"response": response})
