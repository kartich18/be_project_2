import sys
import os

# Add the parent directory to the path so we can import 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.user import User

def create_user(username, password, role="viewer"):
    app = create_app()
    with app.app_context():
        # Check if user already exists
        if db.session.query(User).filter_by(username=username).first():
            print(f"Error: Username '{username}' already exists.")
            return

        user = User(username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"Success: User '{username}' created with role '{role}'.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_user.py <username> <password> [role]")
        print("Role defaults to 'viewer' (can also be 'admin')")
        sys.exit(1)
        
    username = sys.argv[1]
    password = sys.argv[2]
    role = sys.argv[3] if len(sys.argv) > 3 else "viewer"
    
    if len(password) < 8:
        print("Error: password must be at least 8 characters")
        sys.exit(1)
        
    if role not in ["admin", "viewer"]:
        print("Error: role must be either 'admin' or 'viewer'")
        sys.exit(1)
        
    create_user(username, password, role)
