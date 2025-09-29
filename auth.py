from functools import wraps
from flask import session, redirect, url_for

def login_required(f):
    """Decoratore per richiedere login admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('logged_in') != True:
            return redirect(url_for('admin'))
        return f(*args, **kwargs)
    return decorated_function

def check_admin_credentials(username, password):
    """Verifica credenziali admin"""
    from config import ADMIN_USER, ADMIN_PASSWORD
    return username == ADMIN_USER and password == ADMIN_PASSWORD