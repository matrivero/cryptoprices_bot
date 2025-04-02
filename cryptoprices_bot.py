import os
import logging
import aiohttp
import asyncio
import functools
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application
from dotenv import load_dotenv
from dataclasses import dataclass

alert_interval = 30  # seconds

# Your Telegram bot API token
load_dotenv(override=True)
TOKEN = os.getenv("TOKEN")
ADMINS = set(int(admin_id.strip()) for admin_id in os.getenv("ADMINS").split(",") if admin_id.strip())

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


@dataclass
class Alert:
    crypto: str
    direction: str
    target_price: float

    def matches(self, price: float) -> bool:
        return (self.direction == 'above' and price >= self.target_price) or \
               (self.direction == 'below' and price <= self.target_price)

    def __str__(self):
        return f"{self.crypto} {self.direction} €{self.target_price}"


def command_error_handler(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            return await func(update, context)
        except Exception as e:
            logging.exception(f"Unhandled error in command {func.__name__}: {e}")
            if update.effective_chat:
                await safe_send(context.bot, update.effective_chat.id, 
                                "An unexpected error occurred. Please try again later.")
    return wrapper


def admin_only(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_id = get_chat_id(update, context)
        if user_id not in ADMINS:
            await safe_send(context.bot, chat_id,"You are not authorized to use this command.")
            return
        return await func(update, context)
    return wrapper


def alert_job(func):
    @functools.wraps(func)
    async def wrapper(context: ContextTypes.DEFAULT_TYPE):
        try:
            await func(context)
        except Exception as e:
            logging.exception(f"Error inside scheduled alert job {func.__name__}: {e}")
    return wrapper


async def safe_send(bot, chat_id, text):
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logging.warning(f"Failed to send message to {chat_id}: {e}")


def get_chat_id(update: Update = None, context: ContextTypes.DEFAULT_TYPE = None) -> int:
    if context and hasattr(context, 'job') and context.job and hasattr(context.job, 'chat_id'):
        return context.job.chat_id
    elif update and update.effective_chat:
        return update.effective_chat.id
    else:
        raise ValueError("Unable to determine chat_id")


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
    chat_id = get_chat_id(update, context)
    await safe_send(context.bot, chat_id, "Welcome to the Crypto Prices Bot! Use /help to see available commands.")


# Command handler for the /help command
@command_error_handler
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_chat_id(update, context)
    await safe_send(context.bot, chat_id, "Available commands:\n"
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
    chat_id = get_chat_id(update, context)
    if not context.args:
        await safe_send(context.bot, chat_id, "Please provide a cryptocurrency symbol. Usage: /price <coin>")
        return

    crypto_id = context.args[0].upper()
    crypto_price = await get_crypto_price(crypto_id)
    if crypto_price is None or crypto_price <= 0:
        await safe_send(context.bot, chat_id, "Couldn't retrieve price. Please check the symbol and try again later.")
    else:
        await safe_send(context.bot, chat_id, f"The current price of {crypto_id} is €{round(crypto_price, 2)}")


# Dictionary to store user alerts
price_alerts: dict[int, list[Alert]] = {}  # int = user_id
@command_error_handler
async def add_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.username
    chat_id = get_chat_id(update, context)
    user_id = update.effective_user.id

    if len(context.args) < 3:
        await safe_send(context.bot, chat_id, "Usage: /addalert <crypto> <above/below> <target_price>")
        return

    crypto = context.args[0].upper()
    direction = context.args[1].lower()
    try:
        target_price = float(context.args[2])
    except ValueError:
        await safe_send(context.bot, chat_id, "Target price must be a valid number.")
        return

    if direction not in ['above', 'below']:
        await safe_send(context.bot, chat_id, "Direction must be 'above' or 'below'.")
        return
    
    alert = Alert(crypto=crypto, direction=direction, target_price=target_price)

    price_alerts.setdefault(user_id, []).append(alert)
    
    await safe_send(context.bot, chat_id, f"Alert set for {crypto} to be {'above' if direction == 'above' else 'below'} €{target_price}.")

    context.job_queue.run_repeating(check_alerts, interval=alert_interval, data=alert, name=user_name, chat_id=chat_id, user_id=user_id)


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


# Command handler for the /listalerts command
async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.username
    user_id = update.effective_user.id
    chat_id = get_chat_id(update, context)
    if user_id not in price_alerts or not price_alerts[user_id]:
        await safe_send(context.bot, chat_id, f"Hey {user_name}, you have no active alerts.")
        return

    alerts = price_alerts[user_id]
    alert_list = "\n".join(
        [f"{alert.crypto.upper()} | {alert.direction} | €{alert.target_price}" for alert in alerts]
    )
    await safe_send(context.bot, chat_id, f"Hey {user_name}, your active alerts are:\n{alert_list}")


# Command handler for the /removealert command
async def remove_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = get_chat_id(update, context)
    if user_id not in price_alerts:
        await safe_send(context.bot, chat_id, "You have no alerts to remove.")
        return

    if len(context.args) < 3:
        await safe_send(context.bot, chat_id, "Usage: /removealert <crypto> <above/below> <target_price> ")
        return
    
    crypto = context.args[0].upper()
    direction = context.args[1].lower()
    try:
        target_price = float(context.args[2])
    except ValueError:
        await safe_send(context.bot, chat_id, "Target price must be a number.")
        return
    
    try:
        jobs = context.job_queue.get_jobs_by_name(update.effective_user.username)
        flag_removed = False
        for job in jobs:
            alert: Alert = job.data
            if alert.crypto == crypto and alert.direction == direction and alert.target_price == target_price:
                job.schedule_removal()
                flag_removed = True  
        if flag_removed:
            await safe_send(context.bot, chat_id, f"Removed job for {crypto} to be {direction} €{target_price}.")
        else:
            await safe_send(context.bot, chat_id, "Job not found.")
    except:
        await safe_send(context.bot, chat_id, "Job couldn't be removed.")

    # ---------- Remove Alert ----------
    try:
        removed_alert = None
        for alert in price_alerts.get(user_id, []):
            if alert.crypto == crypto and alert.direction == direction and alert.target_price == target_price:
                removed_alert = alert
                break
        
        if removed_alert:
            price_alerts[user_id].remove(removed_alert)
            await safe_send(context.bot, chat_id, f"Removed alert for {removed_alert.crypto} to be {'above' if removed_alert.direction == 'above' else 'below'} €{removed_alert.target_price}.")            
            await list_alerts(update, context)  # Call list_alerts to show remaining alerts
            # If there are no alerts left, remove the user entry
            if not price_alerts[user_id]: # Cleanup if empty
                del price_alerts[user_id]
        else:
            await safe_send(context.bot, chat_id, "Alert not found.")
            
    except:
        await safe_send(context.bot, chat_id, "Alert couldn't be removed.")


# Command handler for the /clearalerts command
async def clear_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.username
    chat_id = get_chat_id(update, context)
    if user_id not in price_alerts or len(price_alerts[user_id]) == 0:
        await safe_send(context.bot, chat_id, f"Hey {user_name}, you have no alerts to clear.")
        return

    try:
        for job in context.job_queue.get_jobs_by_name(user_name):
            job.schedule_removal()
        del price_alerts[user_id]  
        await safe_send(context.bot, chat_id, f"Hey {user_name}, all your alerts have been cleared.")
    except:
        await safe_send(context.bot, chat_id, "Couldn't clear alerts.")


# Command handler for the /listusers command
@admin_only
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_chat_id(update, context)
    if not price_alerts:
        await safe_send(context.bot, chat_id, "No users have set any alerts.")
        return

    user_ids = list(price_alerts.keys())
    user_ids_list = "\n".join([str(user_id) for user_id in user_ids])
    await safe_send(context.bot, chat_id, f"Users with price alerts:\n{user_ids_list}")


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