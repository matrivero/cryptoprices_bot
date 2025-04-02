import functools
import logging
from collections.abc import Awaitable, Callable

from config import ADMINS
from telegram import Update
from telegram.ext import ContextTypes
from utils import get_chat_id, safe_send


def command_error_handler(
    func: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]],
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]:
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            await func(update, context)
        except Exception as e:
            logging.exception(f"Unhandled error in command {func.__name__}: {e}")
            if update.effective_chat:
                await safe_send(
                    context.bot,
                    update.effective_chat.id,
                    "An unexpected error occurred. Please try again later.",
                )

    return wrapper


def admin_only(
    func: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]],
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]:
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None:
            return
        user_id = update.effective_user.id
        chat_id = get_chat_id(update, context)

        if user_id not in ADMINS:
            await safe_send(context.bot, chat_id, "You are not authorized to use this command.")
            return

        await func(update, context)

    return wrapper


def alert_job(
    func: Callable[[ContextTypes.DEFAULT_TYPE], Awaitable[None]],
) -> Callable[[ContextTypes.DEFAULT_TYPE], Awaitable[None]]:
    @functools.wraps(func)
    async def wrapper(context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            await func(context)
        except Exception as e:
            logging.exception(f"Error inside scheduled alert job {func.__name__}: {e}")

    return wrapper
