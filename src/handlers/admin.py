from decorators import admin_only
from state import price_alerts
from telegram import Update
from telegram.ext import ContextTypes
from utils import get_chat_id, safe_send


# Command handler for the /listusers command
@admin_only
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = get_chat_id(update, context)
    if not price_alerts:
        await safe_send(context.bot, chat_id, "No users have set any alerts.")
        return

    user_ids = list(price_alerts.keys())
    user_ids_list = "\n".join([str(user_id) for user_id in user_ids])
    await safe_send(context.bot, chat_id, f"Users with price alerts:\n{user_ids_list}")
