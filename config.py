import os
from dotenv import load_dotenv

# Your Telegram bot API token
load_dotenv(override=True)
TOKEN = os.getenv("TOKEN")
ADMINS = set(int(admin_id.strip()) for admin_id in os.getenv("ADMINS").split(",") if admin_id.strip())
ALERT_INTERVAL = 30  # seconds
VALID_SYMBOLS = set()
