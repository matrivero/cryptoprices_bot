import os


def running_in_docker() -> bool:
    return os.path.exists("/.dockerenv")


# Only load .env file if not running in Docker container
if not running_in_docker():
    from dotenv import load_dotenv

    load_dotenv(override=True)

TOKEN = os.getenv("TOKEN")
ADMINS = {
    int(admin_id.strip()) for admin_id in os.getenv("ADMINS", "").split(",") if admin_id.strip()
}
ALERT_INTERVAL = 30  # seconds
VALID_SYMBOLS: set[str] = set()
