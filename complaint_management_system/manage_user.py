"""Small admin helper.

Usage (from this folder, with the virtual environment active):
    python manage_user.py role <username> <admin|staff|user>
    python manage_user.py password <username> <new_password>
"""
import sys

from app import app, db, User

if len(sys.argv) != 4:
    sys.exit(__doc__)

action, username, value = sys.argv[1], sys.argv[2], sys.argv[3]

with app.app_context():
    user = User.query.filter(db.func.lower(User.username) == username.lower()).first()
    if not user:
        sys.exit('User not found')

    if action == 'role':
        if value not in ('admin', 'staff', 'user'):
            sys.exit('Role must be admin, staff or user')
        user.role = value
    elif action == 'password':
        user.set_password(value)
    else:
        sys.exit('Action must be "role" or "password"')

    db.session.commit()
    print('Done')
