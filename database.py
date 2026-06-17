import sqlite3
import psycopg2
from psycopg2.extras import DictCursor
import os
from werkzeug.security import generate_password_hash

DATABASE_PATH = os.path.join("instance", "erpilot.db")

def get_connection():
    db_url = os.environ.get("DATABASE_URL")
    if db_url and (db_url.startswith("postgres://") or db_url.startswith("postgresql://")):
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(db_url, cursor_factory=DictCursor)
        return conn
    else:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def initialize_database():
    db_url = os.environ.get("DATABASE_URL")
    is_postgres = db_url and (db_url.startswith("postgres://") or db_url.startswith("postgresql://"))

    os.makedirs("instance", exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()

    if is_postgres:
        print("Initializing PostgreSQL database...")
        # PostgreSQL Schema
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id SERIAL PRIMARY KEY,
            company_name VARCHAR(255) NOT NULL,
            company_email VARCHAR(255) UNIQUE NOT NULL,
            slug VARCHAR(255) UNIQUE NOT NULL,
            plan VARCHAR(50) DEFAULT 'free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
            employee_id VARCHAR(100) NOT NULL,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            phone VARCHAR(50),
            department VARCHAR(100),
            designation VARCHAR(100),
            join_date DATE,
            status VARCHAR(50) DEFAULT 'active'
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
            product_name VARCHAR(255) NOT NULL,
            sku VARCHAR(100) NOT NULL,
            category VARCHAR(100),
            quantity INTEGER DEFAULT 0,
            unit_price NUMERIC(12,2) DEFAULT 0.0,
            reorder_level INTEGER DEFAULT 10
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
            supplier_name VARCHAR(255) NOT NULL,
            contact_person VARCHAR(255),
            email VARCHAR(255),
            phone VARCHAR(50),
            address TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales_orders (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
            order_number VARCHAR(100) NOT NULL,
            customer_name VARCHAR(255) NOT NULL,
            product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
            quantity INTEGER DEFAULT 1,
            total_amount NUMERIC(12,2) DEFAULT 0.0,
            order_date DATE,
            status VARCHAR(50) DEFAULT 'pending'
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
            message TEXT NOT NULL,
            type VARCHAR(50) DEFAULT 'info',
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_logs (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            query TEXT NOT NULL,
            response TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
    else:
        print("Initializing SQLite database...")
        cursor.execute("PRAGMA foreign_keys = ON")

        # SQLite Schema
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            company_email TEXT UNIQUE NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            plan TEXT DEFAULT 'free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER,
            employee_id TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            department TEXT,
            designation TEXT,
            join_date DATE,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER,
            product_name TEXT NOT NULL,
            sku TEXT NOT NULL,
            category TEXT,
            quantity INTEGER DEFAULT 0,
            unit_price REAL DEFAULT 0.0,
            reorder_level INTEGER DEFAULT 10,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER,
            supplier_name TEXT NOT NULL,
            contact_person TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER,
            order_number TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            product_id INTEGER,
            quantity INTEGER DEFAULT 1,
            total_amount REAL DEFAULT 0.0,
            order_date DATE,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER,
            user_id INTEGER,
            query TEXT NOT NULL,
            response TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        )
        """)

    # Indexes (Supported on both PostgreSQL and SQLite)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_employees_tenant ON employees(tenant_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_tenant ON products(tenant_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_suppliers_tenant ON suppliers(tenant_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_orders_tenant ON sales_orders(tenant_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_tenant ON notifications(tenant_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_logs_tenant ON ai_logs(tenant_id)")
    
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_products_sku_tenant ON products(tenant_id, sku)")

    conn.commit()
    conn.close()
    print("Database Schema Initialized Successfully.")

def seed_database():
    conn = get_connection()
    cursor = conn.cursor()

    db_url = os.environ.get("DATABASE_URL")
    is_postgres = db_url and (db_url.startswith("postgres://") or db_url.startswith("postgresql://"))

    # TRUNCATE tables (using CASCADE for Postgres, DELETE for SQLite)
    tables = ["ai_logs", "notifications", "sales_orders", "suppliers", "products", "employees", "users", "tenants"]
    for table in tables:
        try:
            if is_postgres:
                cursor.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            else:
                cursor.execute(f"DELETE FROM {table}")
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
        except Exception:
            pass

    # Seed Tenant
    if is_postgres:
        cursor.execute("""
            INSERT INTO tenants (company_name, company_email, slug, plan) 
            VALUES ('Acme Enterprise Solutions', 'admin@acme.com', 'acme-enterprise-solutions', 'enterprise')
        """)
    else:
        cursor.execute("""
            INSERT INTO tenants (id, company_name, company_email, slug, plan) 
            VALUES (1, 'Acme Enterprise Solutions', 'admin@acme.com', 'acme-enterprise-solutions', 'enterprise')
        """)
    
    # Seed Users
    admin_hash = generate_password_hash("AdminSecurePassword123!")
    engi_hash = generate_password_hash("EngiTelemetryPass456!")
    
    cursor.execute("""
        INSERT INTO users (tenant_id, name, email, password_hash, role) 
        VALUES (1, 'Gokul (Admin)', 'gokul@abc.com', ?, 'admin')
    """, (admin_hash,))
    
    cursor.execute("""
        INSERT INTO users (tenant_id, name, email, password_hash, role) 
        VALUES (1, 'Engineer Employee', 'engineer@abc.com', ?, 'employee')
    """, (engi_hash,))

    # Seed Employees
    cursor.execute("""
        INSERT INTO employees (tenant_id, employee_id, name, email, phone, department, designation, join_date, status) 
        VALUES (1, 'EMP-001', 'Gokul', 'gokul@abc.com', '555-0100', 'Executive', 'Chief Operating Officer', '2025-01-15', 'active')
    """)
    cursor.execute("""
        INSERT INTO employees (tenant_id, employee_id, name, email, phone, department, designation, join_date, status) 
        VALUES (1, 'EMP-002', 'Emma Watson', 'emma@acme.com', '555-0188', 'Operations', 'Inventory Manager', '2025-03-20', 'active')
    """)
    cursor.execute("""
        INSERT INTO employees (tenant_id, employee_id, name, email, phone, department, designation, join_date, status) 
        VALUES (1, 'EMP-003', 'John Doe', 'john@acme.com', '555-0199', 'Sales', 'Sales Representative', '2025-04-10', 'active')
    """)

    # Seed Suppliers
    if is_postgres:
        cursor.execute("""
            INSERT INTO suppliers (tenant_id, supplier_name, contact_person, email, phone, address) 
            VALUES (1, 'Global Logistics Corp', 'Alice Smith', 'alice@globalcorps.com', '555-2200', '123 Logistics Blvd, New York, NY')
        """)
        cursor.execute("""
            INSERT INTO suppliers (tenant_id, supplier_name, contact_person, email, phone, address) 
            VALUES (1, 'Prime Tech Parts Ltd', 'Bob Johnson', 'bob@primetech.com', '555-3300', '456 Innovation Way, San Jose, CA')
        """)
    else:
        cursor.execute("""
            INSERT INTO suppliers (id, tenant_id, supplier_name, contact_person, email, phone, address) 
            VALUES (1, 1, 'Global Logistics Corp', 'Alice Smith', 'alice@globalcorps.com', '555-2200', '123 Logistics Blvd, New York, NY')
        """)
        cursor.execute("""
            INSERT INTO suppliers (id, tenant_id, supplier_name, contact_person, email, phone, address) 
            VALUES (2, 1, 'Prime Tech Parts Ltd', 'Bob Johnson', 'bob@primetech.com', '555-3300', '456 Innovation Way, San Jose, CA')
        """)

    # Seed Products
    if is_postgres:
        cursor.execute("""
            INSERT INTO products (tenant_id, product_name, sku, category, quantity, unit_price, reorder_level) 
            VALUES (1, 'MacBook Pro 16', 'SKU-MBP-16', 'Electronics', 15, 2499.00, 5)
        """)
        cursor.execute("""
            INSERT INTO products (tenant_id, product_name, sku, category, quantity, unit_price, reorder_level) 
            VALUES (1, 'Ergonomic Office Chair', 'SKU-CHR-01', 'Furniture', 4, 349.50, 10)
        """)
        cursor.execute("""
            INSERT INTO products (tenant_id, product_name, sku, category, quantity, unit_price, reorder_level) 
            VALUES (1, 'UltraWide 34 Monitor', 'SKU-MON-34', 'Electronics', 25, 599.99, 8)
        """)
    else:
        cursor.execute("""
            INSERT INTO products (id, tenant_id, product_name, sku, category, quantity, unit_price, reorder_level) 
            VALUES (1, 1, 'MacBook Pro 16', 'SKU-MBP-16', 'Electronics', 15, 2499.00, 5)
        """)
        cursor.execute("""
            INSERT INTO products (id, tenant_id, product_name, sku, category, quantity, unit_price, reorder_level) 
            VALUES (2, 1, 'Ergonomic Office Chair', 'SKU-CHR-01', 'Furniture', 4, 349.50, 10)
        """)
        cursor.execute("""
            INSERT INTO products (id, tenant_id, product_name, sku, category, quantity, unit_price, reorder_level) 
            VALUES (3, 1, 'UltraWide 34 Monitor', 'SKU-MON-34', 'Electronics', 25, 599.99, 8)
        """)

    # Seed Sales Orders
    cursor.execute("""
        INSERT INTO sales_orders (tenant_id, order_number, customer_name, product_id, quantity, total_amount, order_date, status) 
        VALUES (1, 'ORD-2026-001', 'TechStart Inc', 1, 2, 4998.00, '2026-06-10', 'completed')
    """)
    cursor.execute("""
        INSERT INTO sales_orders (tenant_id, order_number, customer_name, product_id, quantity, total_amount, order_date, status) 
        VALUES (1, 'ORD-2026-002', 'Modern Office Corp', 2, 6, 2097.00, '2026-06-12', 'pending')
    """)
    cursor.execute("""
        INSERT INTO sales_orders (tenant_id, order_number, customer_name, product_id, quantity, total_amount, order_date, status) 
        VALUES (1, 'ORD-2026-003', 'Hobbyist Shop', 3, 1, 599.99, '2026-06-15', 'completed')
    """)

    # Seed Notifications
    cursor.execute("""
        INSERT INTO notifications (tenant_id, message, type) 
        VALUES (1, 'Low Stock Alert: Ergonomic Office Chair (Stock: 4, Reorder Level: 10)', 'warning')
    """)
    cursor.execute("""
        INSERT INTO notifications (tenant_id, message, type) 
        VALUES (1, 'New Employee Added: John Doe', 'success')
    """)
    
    conn.commit()
    conn.close()
    print("Database seeded successfully.")

if __name__ == '__main__':
    initialize_database()
    seed_database()