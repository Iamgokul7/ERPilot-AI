import os
import sys
import pytest
import sqlite3
from flask import session
from werkzeug.security import generate_password_hash

# Add project root to Python path
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
)

# Import database after path fix
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

    # Cleanup
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
    """Admin session"""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["tenant_id"] = 1
        sess["user_name"] = "Gokul (Admin)"
        sess["role"] = "admin"

    return client


@pytest.fixture
def employee_client(client):
    """Employee session"""
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["tenant_id"] = 1
        sess["user_name"] = "Engineer Employee"
        sess["role"] = "employee"

    return client