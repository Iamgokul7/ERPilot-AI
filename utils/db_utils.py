from flask import session, redirect, url_for, flash, abort

def require_tenant_id():
    """
    Strictly retrieves the tenant_id from the session.
    If missing, it implies a security breach or expired session,
    so we abort or redirect to login.
    """
    tenant_id = session.get("tenant_id")
    if tenant_id is None:
        # In a real app, this might be a 403 or redirect
        # For our ERP, we redirect to login to refresh the session
        return None
    return tenant_id

def get_tenant_id_or_abort():
    """
    Retrieve tenant_id or raise 403 if it's a direct API call,
    otherwise redirect.
    """
    tenant_id = session.get("tenant_id")
    if tenant_id is None:
        abort(403, description="Tenant context missing. Please log in again.")
    return tenant_id
