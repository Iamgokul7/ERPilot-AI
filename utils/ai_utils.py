from google import genai
from google.genai import types
from database import get_connection
import json
import os
from dotenv import load_dotenv
import time

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

client = None
if api_key:
    client = genai.Client(api_key=api_key)


def get_tenant_context(tenant_id):
    conn = get_connection()
    cursor = conn.cursor()

    # Fetch employees
    cursor.execute("""
        SELECT employee_id, name, department, designation, email, phone, join_date, status
        FROM employees
        WHERE tenant_id = ?
    """, (tenant_id,))
    employees = [dict(row) for row in cursor.fetchall()]

    # Fetch products
    cursor.execute("""
        SELECT product_name, sku, category, quantity, unit_price, reorder_level
        FROM products
        WHERE tenant_id = ?
    """, (tenant_id,))
    products = [dict(row) for row in cursor.fetchall()]

    # Fetch suppliers
    cursor.execute("""
        SELECT supplier_name, contact_person, email, phone, address
        FROM suppliers
        WHERE tenant_id = ?
    """, (tenant_id,))
    suppliers = [dict(row) for row in cursor.fetchall()]

    # Fetch sales orders
    cursor.execute("""
        SELECT o.order_number,
               o.customer_name,
               p.product_name,
               o.quantity,
               o.total_amount,
               o.order_date,
               o.status
        FROM sales_orders o
        LEFT JOIN products p ON o.product_id = p.id
        WHERE o.tenant_id = ?
    """, (tenant_id,))
    sales_orders = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "employees": employees,
        "products_inventory": products,
        "suppliers": suppliers,
        "sales_orders": sales_orders
    }


def generate_ai_response(tenant_id, user_message):

    if client is None:
        return "AI Assistant is unavailable because GEMINI_API_KEY is not configured."

    context = get_tenant_context(tenant_id)

    system_instruction = f"""You are the ERPilot AI Assistant, an expert ERP Business Analyst.

You help managers and employees analyze company operations including employee details, inventory stock levels, suppliers, and sales order revenues.

You are given the company's live ERP database in JSON:

ERP Operations Context:
{json.dumps(context, indent=2)}

Guidelines:

1. Format your replies in clean HTML or Markdown. Use lists, tables, and bold tags.

2. If the user asks about low stock products, identify products where quantity <= reorder_level.

3. If they ask about sales, revenue, or monthly sales, analyze and summarize sales_orders.

4. If they ask about employee count or details, count or filter the employees list.

5. If they ask about suppliers, reference the suppliers list.

6. Keep the tone helpful, professional, and concise. Do not expose that you received a JSON text context.
"""

    last_error = None

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2,
                )
            )

            return response.text

        except Exception as e:
            last_error = e

            if (
                "503" in str(e)
                or "demand" in str(e).lower()
                or "limit" in str(e).lower()
                or "429" in str(e)
                or "unavailable" in str(e).lower()
            ):
                time.sleep(2)
                continue

            break

    return f"Error communicating with AI Core: {str(last_error)}"