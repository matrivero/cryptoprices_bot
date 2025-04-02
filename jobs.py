from decorators import alert_job
from utils import safe_send, get_chat_id, get_crypto_price
from models import Alert
from telegram.ext import ContextTypes
import logging
from state import price_alerts


# Function to check if the alert condition is met
@alert_job
async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    try:
        alert: Alert = context.job.data
        user_id = str(context.job.user_id)
        price = await get_crypto_price(alert.crypto)
        if price is None:
            logging.warning(f"Skipping alert check due to missing price for {alert.crypto}")
            return
        if alert.matches(price):
            chat_id = get_chat_id(None, context)
            await safe_send(context.bot, chat_id, 
                            text=f"Alert: {alert.crypto} is now {'above' if alert.direction == 'above' else 'below'} €{alert.target_price} (current price: €{round(price,2)}).")
            # Auto-remove
            if user_id in price_alerts:
                price_alerts[user_id] = [a for a in price_alerts[user_id] if a != alert]
                if not price_alerts[user_id]:
                    del price_alerts[user_id]
            context.job.schedule_removal()
    except Exception as e:
        logging.exception(f"Error during alert check: {e}")
