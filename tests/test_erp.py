import pytest
from database import get_connection
from unittest.mock import patch
from werkzeug.security import check_password_hash
import io

# 1. Authentication Tests
def test_register_company(client):
    response = client.post("/register", data={
        "company_name": "Test Company",
        "company_email": "test@company.com",
        "admin_name": "Test Admin",
        "admin_email": "admin@test.com",
        "password": "AdminSecurePassword123!",
        "confirm_password": "AdminSecurePassword123!"
    })
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tenants WHERE company_name = 'Test Company'")
    tenant = cursor.fetchone()
    assert tenant is not None
    
    cursor.execute("SELECT * FROM users WHERE email = 'admin@test.com'")
    user = cursor.fetchone()
    assert user is not None
    assert user["role"] == "admin"
    assert check_password_hash(user["password_hash"], "AdminSecurePassword123!")
    conn.close()

def test_register_mismatched_password(client):
    response = client.post("/register", data={
        "company_name": "Mismatched Company",
        "company_email": "mis@company.com",
        "admin_name": "Mis Admin",
        "admin_email": "mis@test.com",
        "password": "AdminSecurePassword123!",
        "confirm_password": "WrongConfirm!"
    })
    assert response.status_code == 200
    assert b"Passwords do not match" in response.data

def test_login_success(client):
    response = client.post("/login", data={
        "email": "gokul@abc.com",
        "password": "AdminSecurePassword123!"
    })
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]

def test_login_failure(client):
    response = client.post("/login", data={
        "email": "gokul@abc.com",
        "password": "WrongPassword!"
    })
    assert response.status_code == 200
    assert b"Invalid Email or Password" in response.data

def test_logout(auth_client):
    response = auth_client.get("/logout")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# 2. Dashboard Tests
def test_dashboard_view(auth_client):
    response = auth_client.get("/dashboard")
    assert response.status_code == 200
    assert b"Acme Enterprise Solutions" in response.data
    assert b"Employees" in response.data
    assert b"Products" in response.data


# 3. Employees Module CRUD Tests
def test_employee_view(auth_client):
    response = auth_client.get("/employees")
    assert response.status_code == 200
    assert b"Employee Directory" in response.data

def test_create_employee_success(auth_client):
    response = auth_client.post("/employees", data={
        "employee_id": "EMP-999",
        "name": "Jane Doe",
        "email": "jane@acme.com",
        "phone": "555-9999",
        "department": "HR",
        "designation": "Manager",
        "join_date": "2026-06-01"
    })
    assert response.status_code == 302
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE employee_id = 'EMP-999'")
    emp = cursor.fetchone()
    assert emp is not None
    assert emp["name"] == "Jane Doe"
    conn.close()

def test_create_employee_missing_fields(auth_client):
    response = auth_client.post("/employees", data={
        "employee_id": "",
        "name": "",
        "email": "invalid@acme.com"
    })
    assert response.status_code == 200
    assert b"Employee ID and name are required." in response.data

def test_create_employee_duplicate_id(auth_client):
    response = auth_client.post("/employees", data={
        "employee_id": "EMP-001",
        "name": "Duplicate Gokul",
        "email": "gokul2@abc.com",
        "phone": "555-0100",
        "department": "Executive",
        "designation": "COO",
        "join_date": "2025-01-15"
    })
    assert response.status_code == 200
    assert b"An employee with this Employee ID already exists." in response.data

def test_edit_employee_not_found(auth_client):
    response = auth_client.get("/employees/9999/edit")
    assert response.status_code == 302

def test_update_employee_success(auth_client):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM employees WHERE employee_id = 'EMP-002'")
    emp_id = cursor.fetchone()["id"]
    conn.close()
    
    response = auth_client.post(f"/employees/{emp_id}/update", data={
        "employee_id": "EMP-002",
        "name": "Emma Watson (Updated)",
        "email": "emma_new@acme.com",
        "phone": "555-8888",
        "department": "Operations",
        "designation": "Director",
        "join_date": "2025-03-20"
    })
    assert response.status_code == 302
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE id = ?", (emp_id,))
    emp = cursor.fetchone()
    assert emp["name"] == "Emma Watson (Updated)"
    conn.close()

def test_delete_employee(auth_client):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM employees WHERE employee_id = 'EMP-003'")
    emp_id = cursor.fetchone()["id"]
    conn.close()
    
    response = auth_client.post(f"/employees/{emp_id}/delete")
    assert response.status_code == 302
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE id = ?", (emp_id,))
    emp = cursor.fetchone()
    assert emp is None
    conn.close()


# 4. Inventory Module CRUD Tests
def test_inventory_view(auth_client):
    response = auth_client.get("/inventory")
    assert response.status_code == 200
    assert b"Product Catalog" in response.data

def test_create_product_success(auth_client):
    response = auth_client.post("/inventory", data={
        "product_name": "Test Wireless Mouse",
        "sku": "SKU-MS-99",
        "category": "Electronics",
        "quantity": "50",
        "unit_price": "29.99",
        "reorder_level": "5"
    })
    assert response.status_code == 302
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE sku = 'SKU-MS-99'")
    prod = cursor.fetchone()
    assert prod is not None
    assert prod["product_name"] == "Test Wireless Mouse"
    conn.close()

def test_create_product_duplicate_sku(auth_client):
    response = auth_client.post("/inventory", data={
        "product_name": "Duplicate Mac",
        "sku": "SKU-MBP-16",
        "category": "Electronics",
        "quantity": "5",
        "unit_price": "2499.00",
        "reorder_level": "5"
    })
    assert response.status_code == 200
    assert b"already exists" in response.data

def test_edit_product_not_found(auth_client):
    response = auth_client.get("/inventory/9999/edit")
    assert response.status_code == 302

def test_update_product(auth_client):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM products WHERE sku = 'SKU-MBP-16'")
    prod_id = cursor.fetchone()["id"]
    conn.close()
    
    response = auth_client.post(f"/inventory/{prod_id}/update", data={
        "product_name": "MacBook Pro 16 M3 Max",
        "sku": "SKU-MBP-16",
        "category": "Electronics",
        "quantity": "12",
        "unit_price": "2999.00",
        "reorder_level": "3"
    })
    assert response.status_code == 302
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (prod_id,))
    prod = cursor.fetchone()
    assert prod["product_name"] == "MacBook Pro 16 M3 Max"
    conn.close()

def test_delete_product(auth_client):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM products WHERE sku = 'SKU-CHR-01'")
    prod_id = cursor.fetchone()["id"]
    conn.close()
    
    response = auth_client.post(f"/inventory/{prod_id}/delete")
    assert response.status_code == 302
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (prod_id,))
    prod = cursor.fetchone()
    assert prod is None
    conn.close()


# 5. Suppliers Module CRUD Tests
def test_suppliers_view(auth_client):
    response = auth_client.get("/suppliers")
    assert response.status_code == 200
    assert b"Suppliers Directory" in response.data

def test_create_supplier_success(auth_client):
    response = auth_client.post("/suppliers", data={
        "supplier_name": "Test Supplier Ltd",
        "contact_person": "Charlie",
        "email": "charlie@test.com",
        "phone": "555-4400",
        "address": "789 Pine Rd, Boston, MA"
    })
    assert response.status_code == 302
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM suppliers WHERE supplier_name = 'Test Supplier Ltd'")
    supp = cursor.fetchone()
    assert supp is not None
    conn.close()

def test_edit_supplier(auth_client):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM suppliers WHERE supplier_name = 'Global Logistics Corp'")
    supp_id = cursor.fetchone()["id"]
    conn.close()
    
    response = auth_client.get(f"/suppliers/{supp_id}/edit")
    assert response.status_code == 200
    assert b"Edit Supplier" in response.data

def test_update_supplier(auth_client):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM suppliers WHERE supplier_name = 'Global Logistics Corp'")
    supp_id = cursor.fetchone()["id"]
    conn.close()
    
    response = auth_client.post(f"/suppliers/{supp_id}/update", data={
        "supplier_name": "Global Logistics Corp (Updated)",
        "contact_person": "Alice Smith",
        "email": "alice_updated@global.com",
        "phone": "555-2200",
        "address": "123 Logistics Blvd, New York, NY"
    })
    assert response.status_code == 302
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT supplier_name FROM suppliers WHERE id = ?", (supp_id,))
    assert cursor.fetchone()["supplier_name"] == "Global Logistics Corp (Updated)"
    conn.close()

def test_delete_supplier(auth_client):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM suppliers WHERE supplier_name = 'Prime Tech Parts Ltd'")
    supp_id = cursor.fetchone()["id"]
    conn.close()
    
    response = auth_client.post(f"/suppliers/{supp_id}/delete")
    assert response.status_code == 302
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM suppliers WHERE id = ?", (supp_id,))
    assert cursor.fetchone() is None
    conn.close()


# 6. Sales Orders & Revenue Tests
def test_sales_view(auth_client):
    response = auth_client.get("/sales")
    assert response.status_code == 200
    assert b"Sales Orders Register" in response.data

def test_create_sales_order_success(auth_client):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, quantity, unit_price FROM products WHERE sku = 'SKU-MON-34'")
    prod = cursor.fetchone()
    prod_id = prod["id"]
    old_qty = prod["quantity"]
    conn.close()
    
    response = auth_client.post("/sales", data={
        "order_number": "ORD-TEST-001",
        "customer_name": "Test Retailer",
        "product_id": str(prod_id),
        "quantity": "5",
        "order_date": "2026-06-17",
        "status": "completed"
    })
    assert response.status_code == 302
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sales_orders WHERE order_number = 'ORD-TEST-001'")
    order = cursor.fetchone()
    assert order is not None
    assert order["total_amount"] == round(prod["unit_price"] * 5, 2)
    
    cursor.execute("SELECT quantity FROM products WHERE id = ?", (prod_id,))
    assert cursor.fetchone()["quantity"] == old_qty - 5
    conn.close()

def test_create_sales_order_insufficient_stock(auth_client):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, quantity FROM products WHERE sku = 'SKU-MBP-16'")
    prod = cursor.fetchone()
    prod_id = prod["id"]
    old_qty = prod["quantity"]
    conn.close()
    
    response = auth_client.post("/sales", data={
        "order_number": "ORD-TEST-002",
        "customer_name": "Failed Buyer",
        "product_id": str(prod_id),
        "quantity": str(old_qty + 10),
        "order_date": "2026-06-17",
        "status": "pending"
    })
    assert response.status_code == 302
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sales_orders WHERE order_number = 'ORD-TEST-002'")
    assert cursor.fetchone() is None
    conn.close()

def test_edit_sales_order(auth_client):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM sales_orders WHERE order_number = 'ORD-2026-001'")
    order_id = cursor.fetchone()["id"]
    conn.close()
    
    response = auth_client.get(f"/sales/{order_id}/edit")
    assert response.status_code == 200
    assert b"Edit Sales Order" in response.data

def test_update_sales_order(auth_client):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM sales_orders WHERE order_number = 'ORD-2026-001'")
    order_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM products WHERE sku = 'SKU-MBP-16'")
    prod_id = cursor.fetchone()["id"]
    conn.close()
    
    response = auth_client.post(f"/sales/{order_id}/update", data={
        "order_number": "ORD-2026-001",
        "customer_name": "TechStart Inc (Updated)",
        "product_id": str(prod_id),
        "quantity": "1",
        "order_date": "2026-06-10",
        "status": "completed"
    })
    assert response.status_code == 302
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT customer_name FROM sales_orders WHERE id = ?", (order_id,))
    assert cursor.fetchone()["customer_name"] == "TechStart Inc (Updated)"
    conn.close()

def test_update_sales_order_status(auth_client):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM sales_orders WHERE order_number = 'ORD-2026-002'")
    order_id = cursor.fetchone()["id"]
    conn.close()
    
    response = auth_client.post(f"/sales/{order_id}/status", data={"status": "completed"})
    assert response.status_code == 302
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM sales_orders WHERE id = ?", (order_id,))
    assert cursor.fetchone()["status"] == "completed"
    conn.close()

def test_delete_sales_order(auth_client):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM sales_orders WHERE order_number = 'ORD-2026-003'")
    order_id = cursor.fetchone()["id"]
    conn.close()
    
    response = auth_client.post(f"/sales/{order_id}/delete")
    assert response.status_code == 302
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sales_orders WHERE id = ?", (order_id,))
    assert cursor.fetchone() is None
    conn.close()


# 7. Reports Module Tests
def test_reports_dashboard(auth_client):
    response = auth_client.get("/reports")
    assert response.status_code == 200
    assert b"Reports Center" in response.data
    assert b"Inventory Report" in response.data

def test_reports_exports(auth_client):
    types = ["inventory", "sales", "employees", "suppliers"]
    formats = ["csv", "excel", "pdf"]
    
    for t in types:
        for f in formats:
            response = auth_client.get(f"/reports/export?type={t}&format={f}")
            assert response.status_code == 200
            if f == "csv":
                assert response.mimetype == "text/csv"
            elif f == "excel":
                assert response.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            elif f == "pdf":
                assert response.mimetype == "application/pdf"


# 8. Notifications Tests
def test_notifications_endpoint(auth_client):
    response = auth_client.get("/notifications")
    assert response.status_code == 200
    assert isinstance(response.json, list)
    
def test_notifications_mark_read(auth_client):
    response = auth_client.post("/notifications/mark-read")
    assert response.status_code == 200
    assert response.json["status"] == "success"


# 9. AI Assistant Tests

@patch("utils.ai_utils.generate_ai_response")
def test_ai_assistant_logging(mock_generate_ai_response, auth_client):

    mock_generate_ai_response.return_value = (
        "This is a mock AI response showing low stock products."
    )

    response = auth_client.post(
        "/ai-assistant/chat",
        json={
            "message": "Show low stock products"
        }
    )

    assert response.status_code == 200
    assert response.json["response"] == (
        "This is a mock AI response showing low stock products."
    )
    # Verify DB logging
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ai_logs ORDER BY id DESC LIMIT 1")
    log = cursor.fetchone()
    assert log is not None
    assert log["query"] == "Show low stock products"
    assert log["response"] == "This is a mock AI response showing low stock products."
    conn.close()


# 10. Role-Based Access Control Restrictions
def test_rbac_restrictions_for_employee(employee_client):
    # Employees cannot delete employees
    response = employee_client.post("/employees/1/delete")
    assert response.status_code == 302 # Redirected
    
    # Employees cannot edit inventory
    response = employee_client.post("/inventory/1/update", data={"product_name": "Hack"})
    assert response.status_code == 302 # Redirected
    
    # Employees cannot delete inventory
    response = employee_client.post("/inventory/1/delete")
    assert response.status_code == 302
    
    # Employees can view inventory, dashboard, reports, AI
    assert employee_client.get("/inventory").status_code == 200
    assert employee_client.get("/dashboard").status_code == 200
    assert employee_client.get("/reports").status_code == 200
    assert employee_client.get("/ai-assistant").status_code == 200
