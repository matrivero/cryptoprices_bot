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
        'direction': direction,
        'target_price': target_price
    })
    
    await update.message.reply_text(f"Alert set for {crypto.upper()} to be {'above' if direction == 'above' else 'below'} €{target_price}.")

    context.job_queue.run_repeating(check_alerts, interval=30, data=price_alerts[user_id][-1], name=user_name, chat_id=chat_id, user_id=user_id)


async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    price_alert = context.job.data
    crypto = price_alert['crypto']
    target_price = price_alert['target_price']
    direction = price_alert['direction']
    price = get_crypto_price(crypto.upper())
    # Check if the alert condition is met
    if (direction == 'above' and price >= target_price) or (direction == 'below' and price <= target_price):
        await context.bot.send_message(chat_id=context.job.chat_id, text=f"Alert: {crypto.upper()} is now {'above' if direction == 'above' else 'below'} €{target_price} (current price: €{price}).")


async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.username
    jobs = context.job_queue.get_jobs_by_name(update.effective_user.username)
    if not jobs:
        await update.message.reply_text(f"Hey {user_name}, you have no active alerts.")
        return

    job_list = "\n".join([f"{job.data}" for job in jobs])
    await update.message.reply_text(f"Hey {user_name}, your active alerts are:\n{job_list}")


async def remove_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in price_alerts:
        await update.message.reply_text("You have no alerts to remove.")
        return

    if len(context.args) < 3:
        await update.message.reply_text("Usage: /removealert <crypto> <above/below> <target_price> ")
        return
    
    crypto = context.args[0].upper()
    direction = context.args[1].lower()
    target_price = float(context.args[2])
    
    try:
        jobs = context.job_queue.get_jobs_by_name(update.effective_user.username)
        flag_removed = False
        for job in jobs:
            if job.data['crypto'] == crypto and job.data['direction'] == direction and job.data['target_price'] == target_price:
                job.schedule_removal()
                flag_removed = True  
        if flag_removed:
            await update.message.reply_text(f"Removed job for {crypto} to be {direction} €{target_price}.")
        else:
            await update.message.reply_text("Job not found.")
    except:
        await update.message.reply_text("Job couldn't be removed.")

    try:
        for index, d in enumerate(price_alerts[user_id]):
            if d.get('crypto') == crypto and d.get('direction') == direction and d.get('target_price') == target_price:
                break
        
        if index < len(price_alerts[user_id]):
            removed_alert = price_alerts[user_id].pop(index)
            await update.message.reply_text(f"Removed alert for {removed_alert['crypto'].upper()} to be {'above' if removed_alert['direction'] == 'above' else 'below'} €{removed_alert['target_price']}.")            
            await list_alerts(update, context)  # Call list_alerts to show remaining alerts
        else:
            await update.message.reply_text("Alert not found.")
            
        # If there are no alerts left, remove the user entry
        if not price_alerts[user_id]:
            del price_alerts[user_id]
    except:
        await update.message.reply_text("Alert couldn't be removed.")


async def clear_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.username
    if user_id not in price_alerts or len(price_alerts[user_id]) == 0:
        await update.message.reply_text(f"Hey {user_name}, you have no alerts to clear.")
        return

    try:
        for job in context.job_queue.get_jobs_by_name(user_name):
            job.schedule_removal()
        del price_alerts[user_id]  
        await update.message.reply_text(f"Hey {user_name}, all your alerts have been cleared.")
    except:
        await update.message.reply_text("Couldn't clear alerts.")


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
    application.add_handler(CommandHandler("removealert", remove_alert))  
    application.add_handler(CommandHandler("clearalerts", clear_alerts))
    application.add_handler(CommandHandler("listusers", list_users))

    application.run_polling()