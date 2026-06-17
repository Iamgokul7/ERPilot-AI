from flask import Flask, render_template
from blueprints.auth import auth_bp
from blueprints.dashboard import dashboard_bp
from blueprints.employees import employees_bp
from blueprints.inventory import inventory_bp
from blueprints.suppliers import suppliers_bp
from blueprints.sales import sales_bp
from blueprints.ai_assistant import ai_assistant_bp
from blueprints.notifications import notifications_bp
from blueprints.reports import reports_bp

from datetime import timedelta
from flask import session, redirect, url_for, request

app = Flask(__name__)
app.secret_key = "erpilot_super_secret_key"
app.permanent_session_lifetime = timedelta(days=7)

@app.before_request
def protect_routes():
    public_endpoints = ['auth.login', 'auth.register', 'home', 'static']
    if request.endpoint in public_endpoints:
        return
    if not session.get('user_id') or not session.get('tenant_id'):
        return redirect(url_for('auth.login'))

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(employees_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(suppliers_bp)
app.register_blueprint(sales_bp, url_prefix="/sales")
app.register_blueprint(ai_assistant_bp)
app.register_blueprint(notifications_bp)
app.register_blueprint(reports_bp)


@app.route("/")
def home():
    return render_template("home.html")


if __name__ == "__main__":
    app.run(debug=True)
