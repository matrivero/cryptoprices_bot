import os

from dotenv import load_dotenv

# Clear env variables
for var in ["TOKEN", "ADMINS"]:
    os.environ.pop(var, None)

# Your Telegram bot API token
load_dotenv(override=True)
TOKEN = os.getenv("TOKEN")
ADMINS = {
    int(admin_id.strip()) for admin_id in os.getenv("ADMINS", "").split(",") if admin_id.strip()
}
ALERT_INTERVAL = 30  # seconds
VALID_SYMBOLS: set[str] = set()
