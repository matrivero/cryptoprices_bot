from config import ALERT_INTERVAL
from decorators import command_error_handler
from jobs import check_alerts
from models import Alert
from state import price_alerts
from telegram import Update
from telegram.ext import ContextTypes, JobQueue
from utils import get_chat_id, safe_send


@command_error_handler
async def add_alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.username if update.effective_user else "Unknown"
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = get_chat_id(update, context)

    if not context.args or len(context.args) < 3:
        await safe_send(
            context.bot, chat_id, "Usage: /addalert <crypto> <above/below> <target_price>"
        )
        return

    crypto = context.args[0].upper()
    direction = context.args[1].lower()
    try:
        target_price = float(context.args[2])
    except ValueError:
        await safe_send(context.bot, chat_id, "Target price must be a valid number.")
        return

    if direction not in ["above", "below"]:
        await safe_send(context.bot, chat_id, "Direction must be 'above' or 'below'.")
        return

    alert = Alert(crypto=crypto, direction=direction, target_price=target_price)

    price_alerts.setdefault(user_id, []).append(alert)

    await safe_send(
        context.bot,
        chat_id,
        f"Alert set for {crypto} to be {'above' if direction == 'above' else 'below'} €{target_price}.",
    )

    if isinstance(context.job_queue, JobQueue):
        context.job_queue.run_repeating(
            check_alerts,
            interval=ALERT_INTERVAL,
            data=alert,
            name=user_name,
            chat_id=chat_id,
            user_id=user_id,
        )
    else:
        await safe_send(context.bot, chat_id, "Job queue is not properly initialized.")


# Command handler for the /listalerts command
async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.username if update.effective_user else "Unknown"
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = get_chat_id(update, context)
    if user_id not in price_alerts or not price_alerts[user_id]:
        await safe_send(context.bot, chat_id, f"Hey {user_name}, you have no active alerts.")
        return

    alerts = price_alerts[user_id]
    alert_list = "\n".join(
        [f"{alert.crypto} | {alert.direction} | €{alert.target_price}" for alert in alerts]
    )
    await safe_send(context.bot, chat_id, f"Hey {user_name}, your active alerts are:\n{alert_list}")


# Command handler for the /removealert command
async def remove_alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = get_chat_id(update, context)
    if user_id not in price_alerts:
        await safe_send(context.bot, chat_id, "You have no alerts to remove.")
        return

    if not context.args or len(context.args) < 3:
        await safe_send(
            context.bot, chat_id, "Usage: /removealert <crypto> <above/below> <target_price> "
        )
        return

    crypto = context.args[0].upper()
    direction = context.args[1].lower()
    try:
        target_price = float(context.args[2])
    except ValueError:
        await safe_send(context.bot, chat_id, "Target price must be a number.")
        return

    try:
        user_name = update.effective_user.username if update.effective_user else "Unknown"
        if context.job_queue is None or not hasattr(context.job_queue, "get_jobs_by_name"):
            await safe_send(context.bot, chat_id, "Job queue is not properly initialized.")
            return
        jobs: list = []
        if context.job_queue and hasattr(context.job_queue, "get_jobs_by_name"):
            jobs = context.job_queue.get_jobs_by_name(user_name)
        flag_removed = False
        for job in jobs:
            alert: Alert = job.data
            if (
                alert.crypto == crypto
                and alert.direction == direction
                and alert.target_price == target_price
            ):
                job.schedule_removal()
                flag_removed = True
        if flag_removed:
            await safe_send(
                context.bot, chat_id, f"Removed job for {crypto} to be {direction} €{target_price}."
            )
        else:
            await safe_send(context.bot, chat_id, "Job not found.")
    except ValueError:
        await safe_send(context.bot, chat_id, "Job couldn't be removed.")

    # ---------- Remove Alert ----------
    try:
        removed_alert = None
        for alert in price_alerts.get(user_id, []):
            if (
                alert.crypto == crypto
                and alert.direction == direction
                and alert.target_price == target_price
            ):
                removed_alert = alert
                break

        if removed_alert:
            price_alerts[user_id].remove(removed_alert)
            await safe_send(
                context.bot,
                chat_id,
                f"Removed alert for {removed_alert.crypto} to be {'above' if removed_alert.direction == 'above' else 'below'} €{removed_alert.target_price}.",
            )
            await list_alerts(update, context)  # Call list_alerts to show remaining alerts
            # If there are no alerts left, remove the user entry
            if not price_alerts[user_id]:  # Cleanup if empty
                del price_alerts[user_id]
        else:
            await safe_send(context.bot, chat_id, "Alert not found.")

    except ValueError:
        await safe_send(context.bot, chat_id, "Alert couldn't be removed.")


# Command handler for the /clearalerts command
async def clear_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.username if update.effective_user else "Unknown"
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = get_chat_id(update, context)
    if user_id not in price_alerts or len(price_alerts[user_id]) == 0:
        await safe_send(context.bot, chat_id, f"Hey {user_name}, you have no alerts to clear.")
        return

    try:
        if context.job_queue is not None:
            if context.job_queue and hasattr(context.job_queue, "get_jobs_by_name"):
                for job in context.job_queue.get_jobs_by_name(user_name):
                    job.schedule_removal()
        del price_alerts[user_id]
        await safe_send(
            context.bot, chat_id, f"Hey {user_name}, all your alerts have been cleared."
        )
    except ValueError:
        await safe_send(context.bot, chat_id, "Couldn't clear alerts.")
