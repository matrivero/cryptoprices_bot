import logging

from decorators import alert_job
from models import Alert
from state import price_alerts
from telegram.ext import ContextTypes
from utils import get_chat_id, get_crypto_price, safe_send


# Function to check if the alert condition is met
@alert_job
async def check_alerts(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if context.job is None:
            logging.error("Job is None, cannot proceed with alert check.")
            return
        if context.job.data is None:
            logging.error("Job data is None, cannot proceed with alert check.")
            return
        alert: Alert = context.job.data
        user_id = context.job.user_id
        price = await get_crypto_price(alert.crypto)
        if price is None:
            logging.warning(f"Skipping alert check due to missing price for {alert.crypto}")
            return
        if alert.matches(price):
            chat_id = get_chat_id(None, context)
            await safe_send(
                context.bot,
                chat_id,
                text=f"Alert: {alert.crypto} is now {'above' if alert.direction == 'above' else 'below'} €{alert.target_price} (current price: €{round(price,2)}).",
            )

            # Auto-remove
            user_alerts = price_alerts.get(user_id, [])
            if alert in user_alerts:
                user_alerts.remove(alert)
                await safe_send(
                    context.bot,
                    chat_id,
                    text=f"Alert {alert.crypto} | {alert.direction} | €{alert.target_price} has been removed.",
                )
                if not user_alerts:
                    del price_alerts[user_id]
                else:
                    price_alerts[user_id] = user_alerts

            context.job.schedule_removal()

    except Exception as e:
        logging.exception(f"Error during alert check: {e}")
