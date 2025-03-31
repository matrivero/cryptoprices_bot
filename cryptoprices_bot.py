import os
import logging
import aiohttp
import asyncio
import functools
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


def command_error_handler(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            return await func(update, context)
        except Exception as e:
            logging.exception(f"Unhandled error in command {func.__name__}: {e}")
            if update.message:
                await update.message.reply_text("⚠️ An unexpected error occurred. Please try again later.")
    return wrapper


def alert_job(func):
    @functools.wraps(func)
    async def wrapper(context: ContextTypes.DEFAULT_TYPE):
        try:
            await func(context)
        except Exception as e:
            logging.exception(f"Error inside scheduled alert job {func.__name__}: {e}")
    return wrapper


VALID_SYMBOLS = set()
async def load_valid_symbols():
    global VALID_SYMBOLS
    url = 'https://api.binance.com/api/v3/exchangeInfo'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logging.error(f"Could not fetch symbols: {response.status}")
                    return
                data = await response.json()
                VALID_SYMBOLS = {s['symbol'].replace("EUR", "") for s in data['symbols'] if s['symbol'].endswith("EUR")}
                logging.info(f"Loaded {len(VALID_SYMBOLS)} valid symbols")
    except Exception as e:
        logging.exception(f"Error loading valid symbols: {e}")


# Initialize the bot
@command_error_handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Crypto Prices Bot! Use /help to see available commands.")


# Command handler for the /help command
@command_error_handler
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
async def get_crypto_price(crypto_id, retries=3, delay=1):
    url = f'https://api.binance.com/api/v3/ticker/price?symbol={crypto_id}EUR'
    for attempt in range(1, retries + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logging.warning(f"Binance API responded with {response.status} for {crypto_id} (Attempt {attempt})")
                        await asyncio.sleep(delay)
                        continue
                    data = await response.json()
                    return float(data.get('price', 0))
        except aiohttp.ClientError as e:
            logging.warning(f"Network error on attempt {attempt} for {crypto_id}: {e}")
            await asyncio.sleep(delay)
        except (KeyError, ValueError, TypeError) as e:
            logging.error(f"Error parsing price for {crypto_id}: {e}")
            return None
    logging.error(f"Failed to get price for {crypto_id} after {retries} attempts")
    return None


# Command handler for the /price command
@command_error_handler
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a cryptocurrency symbol. Usage: /price <coin>")
        return

    crypto_id = context.args[0].upper()
    crypto_price = await get_crypto_price(crypto_id)
    if crypto_price is None or crypto_price <= 0:
        await update.message.reply_text("Couldn't retrieve price. Please check the symbol and try again later.")
    else:
        await update.message.reply_text(f"The current price of {crypto_id} is €{round(crypto_price, 2)}")



# Dictionary to store user alerts
price_alerts = {}
@command_error_handler
async def add_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /addalert <crypto> <above/below> <target_price>")
        return

    crypto = context.args[0].upper()
    direction = context.args[1].lower()
    try:
        target_price = float(context.args[2])
    except ValueError:
        await update.message.reply_text("Target price must be a valid number.")
        return

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
@alert_job
async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    try:
        price_alert = context.job.data
        user_id = str(context.job.user_id)
        crypto = price_alert['crypto']
        target_price = price_alert['target_price']
        direction = price_alert['direction']
        price = await get_crypto_price(crypto.upper())
        if price is None:
            logging.warning(f"Skipping alert check due to missing price for {crypto}")
            return
        if (direction == 'above' and price >= target_price) or (direction == 'below' and price <= target_price):
            await context.bot.send_message(chat_id=context.job.chat_id, 
                                           text=f"Alert: {crypto.upper()} is now {'above' if direction == 'above' else 'below'} €{target_price} (current price: €{round(price,2)}).")
            # Auto-remove
            if user_id in price_alerts:
                price_alerts[user_id] = [a for a in price_alerts[user_id] if a != price_alert]
                if not price_alerts[user_id]:
                    del price_alerts[user_id]
            context.job.schedule_removal()
    except Exception as e:
        logging.exception(f"Error during alert check: {e}")


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
    await load_valid_symbols()
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