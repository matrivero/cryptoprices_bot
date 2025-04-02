import logging

import aiohttp
from decorators import command_error_handler
from telegram import Update
from telegram.ext import Application, ContextTypes
from utils import get_chat_id, get_crypto_price, safe_send

valid_symbols: set[str] = set()


async def load_valid_symbols() -> None:
    url = "https://api.binance.com/api/v3/exchangeInfo"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logging.error(f"Could not fetch symbols: {response.status}")
                    return
                data = await response.json()
                valid_symbols = {
                    s["symbol"].replace("EUR", "")
                    for s in data["symbols"]
                    if s["symbol"].endswith("EUR")
                }
                logging.info(f"Loaded {len(valid_symbols)} valid symbols")
    except Exception as e:
        logging.exception(f"Error loading valid symbols: {e}")


# Initialize the bot
@command_error_handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = get_chat_id(update, context)
    await safe_send(
        context.bot,
        chat_id,
        "Welcome to the Crypto Prices Bot! Use /help to see available commands.",
    )


# Command handler for the /help command
@command_error_handler
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = get_chat_id(update, context)
    await safe_send(
        context.bot,
        chat_id,
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/price <coin> - Get the price of a cryptocurrency\n"
        "/addalert <crypto> <above/below> <target_price> - Set an alert for a cryptocurrency price\n"
        "/listalerts - List all your active alerts\n"
        "/removealert <crypto> <above/below> <target_price> - Remove an alert\n"
        "/clearalerts - Clear all your alerts\n"
        "/listusers - List all users with alerts",
    )


# Function to set the bot's commands and chat menu button
async def post_init(application: Application) -> None:
    await load_valid_symbols()
    await application.bot.set_my_commands(
        [
            ("start", "Starts the bot"),
            ("help", "Show some help"),
            ("price", "Get the price of a cryptocurrency"),
            ("addalert", "Add an alert for a cryptocurrency price"),
            ("listalerts", "List all your active alerts"),
            ("removealert", "Remove an alert"),
            ("clearalerts", "Clear all your alerts"),
            ("listusers", "List all users with alerts"),
        ]
    )
    await application.bot.set_chat_menu_button()


# Command handler for the /price command
@command_error_handler
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = get_chat_id(update, context)
    if not context.args:
        await safe_send(
            context.bot, chat_id, "Please provide a cryptocurrency symbol. Usage: /price <coin>"
        )
        return

    crypto_id = context.args[0].upper()
    crypto_price = await get_crypto_price(crypto_id)
    if crypto_price is None or crypto_price <= 0:
        await safe_send(
            context.bot,
            chat_id,
            "Couldn't retrieve price. Please check the symbol and try again later.",
        )
    else:
        await safe_send(
            context.bot, chat_id, f"The current price of {crypto_id} is €{round(crypto_price, 2)}"
        )
