import sys
from wms import create_app, db
from wms.models import User

def make_admin(email):
    """
    Finds a user by email and updates their role to 'Admin'.
    """
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user:
            user.role = 'Admin'
            db.session.commit()
            print(f"Success: User '{email}' has been promoted to Admin.")
        else:
            print(f"Error: User with email '{email}' not found.")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python make_admin.py <email>")
        sys.exit(1)

    email_arg = sys.argv[1]
    make_admin(email_arg)