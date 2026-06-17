from functools import wraps
from flask import session, redirect, url_for, flash

def role_required(allowed_roles):
    """
    Decorator to restrict access to routes based on user roles.
    allowed_roles: List of roles that can access the route (e.g., ['admin', 'manager'])
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = session.get('role')
            
            if user_role not in allowed_roles:
                flash("You do not have permission to perform this action.", "danger")
                return redirect(url_for('dashboard.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
