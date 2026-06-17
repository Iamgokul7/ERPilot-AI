import os
import tempfile
import pytest
import sqlite3
from flask import session
from werkzeug.security import generate_password_hash

# Override database path for testing before importing app
import database
TEST_DB_PATH = os.path.join("instance", "test_erpilot.db")
database.DATABASE_PATH = TEST_DB_PATH

from app import app as flask_app

@pytest.fixture
def app():
    # Setup test database
    database.initialize_database()
    database.seed_database()
    
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test_secret_key"
    })
    
    yield flask_app
    
    # Teardown test database
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    """Logs in as admin by default."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["tenant_id"] = 1
        sess["user_name"] = "Gokul (Admin)"
        sess["role"] = "admin"
    return client

@pytest.fixture
def employee_client(client):
    """Logs in as an employee."""
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["tenant_id"] = 1
        sess["user_name"] = "Engineer Employee"
        sess["role"] = "employee"
    return client
