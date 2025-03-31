import aiohttp
import os
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application
from dotenv import load_dotenv

# Your Telegram bot API token
load_dotenv()
TOKEN = os.getenv("TOKEN")

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Initialize the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Crypto Prices Bot! Use /help to see available commands.")


# Command handler for the /help command
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Available commands:\n"
                                      "/start - Start the bot\n"
                                      "/help - Show this help message\n"
                                      "/price <coin> - Get the price of a cryptocurrency\n"
                                      "/addalert <crypto> <above/below> <target_price> - Set an alert for a cryptocurrency price\n"
                                      "/listalerts - List all your active alerts\n"
                                      "/removealert <crypto> <above/below> <target_price> - Remove an alert\n"
                                      "/clearalerts - Clear all your alerts\n"
                                      "/listusers - List all users with alerts")


# Async function to get the price of a cryptocurrency from Binance API
async def get_crypto_price(crypto_id):
    url = f'https://api.binance.com/api/v3/ticker/price?symbol={crypto_id}EUR'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            return float(data['price'])


# Command handler for the /price command
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        crypto_id = context.args[0].upper()  # Get the coin from user input
        crypto_price = await get_crypto_price(crypto_id)
        await update.message.reply_text(f"The current price of {crypto_id} is €{round(crypto_price, 2)}")
    except IndexError:
        await update.message.reply_text("Please provide a cryptocurrency symbol. Usage: /price <coin>")
    except Exception as e:
        await update.message.reply_text(f"An error -{e}- occurred while fetching the price.")


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


# Function to check if the alert condition is met
async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    price_alert = context.job.data
    crypto = price_alert['crypto']
    target_price = price_alert['target_price']
    direction = price_alert['direction']
    price = await get_crypto_price(crypto.upper())
    # Check if the alert condition is met
    if (direction == 'above' and price >= target_price) or (direction == 'below' and price <= target_price):
        await context.bot.send_message(chat_id=context.job.chat_id, text=f"Alert: {crypto.upper()} is now {'above' if direction == 'above' else 'below'} €{target_price} (current price: €{price}).")


# Command handler for the /listalerts command
async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.username
    jobs = context.job_queue.get_jobs_by_name(update.effective_user.username)
    if not jobs:
        await update.message.reply_text(f"Hey {user_name}, you have no active alerts.")
        return

    job_list = "\n".join([f"{job.data}" for job in jobs])
    await update.message.reply_text(f"Hey {user_name}, your active alerts are:\n{job_list}")


# Command handler for the /removealert command
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


# Command handler for the /clearalerts command
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


# Command handler for the /listusers command
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not price_alerts:
        await update.message.reply_text("No users have set any alerts.")
        return

    user_ids = list(price_alerts.keys())
    user_ids_list = "\n".join([str(user_id) for user_id in user_ids])
    await update.message.reply_text(f"Users with price alerts:\n{user_ids_list}")


# Function to set the bot's commands and chat menu button
async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([('start', 'Starts the bot'), 
                                            ('help', 'Show some help'),
                                            ('price', 'Get the price of a cryptocurrency'),
                                            ('addalert', 'Add an alert for a cryptocurrency price'),
                                            ('listalerts', 'List all your active alerts'),
                                            ('removealert', 'Remove an alert'),
                                            ('clearalerts', 'Clear all your alerts'),
                                            ('listusers', 'List all users with alerts')])
    await application.bot.set_chat_menu_button()


# Main function to run the bot
if __name__ == '__main__':
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help))
    application.add_handler(CommandHandler('price', price))
    application.add_handler(CommandHandler("addalert", add_alert))
    application.add_handler(CommandHandler("listalerts", list_alerts))
    application.add_handler(CommandHandler("removealert", remove_alert))  
    application.add_handler(CommandHandler("clearalerts", clear_alerts))
    application.add_handler(CommandHandler("listusers", list_users))

    application.run_polling()