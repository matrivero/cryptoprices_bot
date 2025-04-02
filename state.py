from models import Alert

# Dictionary to store user alerts
price_alerts: dict[int, list[Alert]] = {}  # int = user_id