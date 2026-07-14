import argparse
import getpass
import os

from backend.auth import service
from backend.common.database import Base, SessionLocal, engine


def read_password() -> str:
    environment_password = os.getenv("MINI_CICD_ADMIN_PASSWORD")
    if environment_password:
        return environment_password

    password = getpass.getpass("Admin password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise ValueError("Passwords do not match")
    return password


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update the Mini CI/CD admin account")
    parser.add_argument(
        "--username",
        default=os.getenv("MINI_CICD_ADMIN_USERNAME", "admin"),
        help="Admin username (default: admin)",
    )
    args = parser.parse_args()

    try:
        password = read_password()
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            admin, created = service.create_or_update_admin(db, args.username, password)
    except ValueError as exc:
        parser.error(str(exc))

    action = "created" if created else "updated"
    print(f"Admin account '{admin.username}' {action} successfully.")


if __name__ == "__main__":
    main()
