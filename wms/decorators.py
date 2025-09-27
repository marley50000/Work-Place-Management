from functools import wraps
from flask_login import current_user
from flask import abort

def roles_required(*roles):
    def wrapper(f):
        @wraps(f)
        def wrapped_view(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)  # Forbidden
            return f(*args, **kwargs)
        return wrapped_view
    return wrapper