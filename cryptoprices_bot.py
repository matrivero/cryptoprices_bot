import requests
import time
import os
import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, Application
from dotenv import load_dotenv

# Your Telegram bot API token
load_dotenv()
TOKEN = os.getenv("TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Function to get the price of a cryptocurrency from Binance API
def get_crypto_price(crypto_id):
    url = f'https://api.binance.com/api/v3/ticker/price?symbol={crypto_id}EUR'
    response = requests.get(url)
    data = response.json()
    return float(data['price'])


# Command handler for the /price command
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        crypto_id = context.args[0].upper()  # Get the coin from user input
        crypto_price = get_crypto_price(crypto_id)
        await update.message.reply_text(f"The current price of {crypto_id} is €{round(crypto_price, 2)}")
    except:
        await update.message.reply_text("Please provide a cryptocurrency symbol. Usage: /price <coin>")


# Dictionary to store user alerts
price_alerts = {}
async def add_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /alert <crypto> <above/below> <target_price> ")
        return
    
    crypto = context.args[0].upper()
    direction = context.args[1].lower()
    target_price = float(context.args[2])
    
    if direction not in ['above', 'below']:
        await update.message.reply_text("Direction must be 'above' or 'below'.")
        return
    
    user_name = update.effective_user.username
    chat_id = update.message.chat_id
    user_id = update.effective_user.id
    if user_id not in price_alerts:
        price_alerts[user_id] = []
    
    price_alerts[user_id].append({
        'crypto': crypto,
        'target_price': target_price,
        'direction': direction
    })
    
    await update.message.reply_text(f"Alert set for {crypto.upper()} to be {'above' if direction == 'above' else 'below'} €{target_price}.")

    context.job_queue.run_repeating(check_alerts, interval=30, data=price_alerts[user_id][-1], name=user_name, chat_id=chat_id, user_id=user_id)


async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    price_alert = context.job.data
    crypto = price_alert['crypto']
    target_price = price_alert['target_price']
    direction = price_alert['direction']
    price = get_crypto_price(crypto.upper())
    #await context.bot.send_message(chat_id=context.job.chat_id, text=f"Alert: when {crypto.upper()} is {direction} than €{target_price} (current price: €{price}).")

    """
    if price is not None:
        # Check if the alert condition is met
        if (direction == 'above' and price >= target_price) or (direction == 'below' and price <= target_price):
            await app.bot.send_message(chat_id=user_id, text=f"Alert: {crypto.upper()} is now {'above' if direction == 'above' else 'below'} €{target_price} (current price: €{price}).")
            # Remove the alert after notifying the user
            alerts.remove(alert)
    """

async def list_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = context.job_queue.get_jobs_by_name(update.effective_user.username)
    if not jobs:
        await update.message.reply_text("You have no active alerts.")
        return

    job_list = "\n".join([f"{job.name}: {job.data}" for job in jobs])
    await update.message.reply_text(f"Your active alerts:\n{job_list}")


async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    alerts = price_alerts.get(user_id, [])
    user_name = update.effective_user.username

    if not alerts:
        await update.message.reply_text(f"Hey {user_name}, you have no active alerts.")
        return

    alert_list = "\n".join(
        [f"{alert['crypto'].upper()}: {'above' if alert['direction'] == 'above' else 'below'} €{alert['target_price']}" for alert in alerts]
    )
    await update.message.reply_text(f"Hey {user_name}, your active alerts:\n{alert_list}")


async def remove_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in price_alerts or len(price_alerts[user_id]) == 0:
        await update.message.reply_text("You have no alerts to remove.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Usage: /remove_alert <alert_index>")
        return
    
    try:
        index = int(context.args[0])
        if index < 1 or index >= len(price_alerts[user_id])+1:
            await update.message.reply_text("Invalid alert index.")
            return
        
        removed_alert = price_alerts[user_id].pop(index-1)
        await update.message.reply_text(f"Removed alert for {removed_alert['crypto'].upper()} to be {'above' if removed_alert['direction'] == 'above' else 'below'} ${removed_alert['target_price']} USD.")
        
        # Notify the user of the remaining alerts
        await list_alerts(update, context)  # Call list_alerts to show remaining alerts
        
        # If there are no alerts left, remove the user entry
        if not price_alerts[user_id]:
            del price_alerts[user_id]
    except ValueError:
        await update.message.reply_text("Please provide a valid integer for the alert index.")


async def remove_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in price_alerts:
        await update.message.reply_text("You have no alerts to remove.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Usage: /removejob <job_index>")
        return
    
    try:
        index = int(context.args[0])
        if index < 1 or index >= len(price_alerts[user_id])+1:
            await update.message.reply_text("Invalid job index.")
            return
        
        job = context.job_queue.get_jobs_by_name(update.effective_user.username)[index-1]
        # get the index of the job in the job queue by its content
        

        job.schedule_removal()
        await update.message.reply_text(f"Removed job {job.name}.")
    except ValueError:
        await update.message.reply_text("Please provide a valid integer for the job index.")


async def clear_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.username
    if user_id not in price_alerts or len(price_alerts[user_id]) == 0:
        await update.message.reply_text(f"Hey {user_name}, you have no alerts to clear.")
        return

    del price_alerts[user_id]  # Clear all alerts for the user
    await update.message.reply_text(f"Hey {user_name}, all your alerts have been cleared.")


async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not price_alerts:
        await update.message.reply_text("No users have set any alerts.")
        return

    user_ids = list(price_alerts.keys())
    user_ids_list = "\n".join([str(user_id) for user_id in user_ids])
    await update.message.reply_text(f"Users with price alerts:\n{user_ids_list}")


if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('price', price))
    application.add_handler(CommandHandler("addalert", add_alert))
    application.add_handler(CommandHandler("listalerts", list_alerts))
    application.add_handler(CommandHandler("listjobs", list_jobs))
    application.add_handler(CommandHandler("removealert", remove_alert))  
    application.add_handler(CommandHandler("removejob", remove_job))
    application.add_handler(CommandHandler("clearalerts", clear_alerts))
    application.add_handler(CommandHandler("listusers", list_users))


    # Start the application
    application.run_polling()