import functools
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMINS
from utils import safe_send, get_chat_id


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