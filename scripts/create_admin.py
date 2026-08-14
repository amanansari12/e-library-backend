import argparse
import getpass
import sys
from pathlib import Path

# Add project root to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import hash_password

def promote_existing_user(db, email: str) -> bool:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False
    
    if user.role == "ADMIN":
        print(f"User {email} is already an Administrator.")
        return True
        
    user.role = "ADMIN"
    db.commit()
    print(f"User {email} promoted to Administrator successfully.")
    return True

def create_admin_user(db, email: str, full_name: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if user:
        print(f"Error: A user with email {email} already exists.")
        sys.exit(1)
        
    # Also check username to avoid uniqueness constraint failures
    username = email.split('@')[0]
    suffix = 1
    original_username = username
    while db.query(User).filter(User.username == username).first():
        username = f"{original_username}{suffix}"
        suffix += 1
        
    new_user = User(
        email=email,
        username=username,
        full_name=full_name,
        hashed_password=hash_password(password),
        role="ADMIN"
    )
    db.add(new_user)
    db.commit()
    print("User created successfully.")
    print("Administrator role assigned.")

def main():
    parser = argparse.ArgumentParser(description="Bootstrap a local Admin user.")
    parser.add_argument("--email", type=str, help="Email of the user to promote or create.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.email:
            # Try to promote existing
            if promote_existing_user(db, args.email):
                sys.exit(0)
            
            print(f"User {args.email} not found. Creating a new admin user.")
            email = args.email
            full_name = input("Name: ")
            password = getpass.getpass("Password: ")
        else:
            print("Interactive Admin Creation")
            full_name = input("Name: ")
            email = input("Email: ")
            password = getpass.getpass("Password: ")
            
        if not email or not password or not full_name:
            print("Error: Name, email, and password are required.")
            sys.exit(1)
            
        create_admin_user(db, email, full_name, password)

    finally:
        db.close()

if __name__ == "__main__":
    main()
