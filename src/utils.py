import asyncio
import logging

import aiohttp
from telegram import Bot, Update
from telegram.ext import ContextTypes


async def safe_send(bot: Bot, chat_id: int, text: str) -> str:
    try:
        await bot.send_message(chat_id=chat_id, text=text)
        return "Message sent successfully"
    except Exception as e:
        logging.warning(f"Failed to send message to {chat_id}: {e}")
        return f"Failed to send message: {e}"


def get_chat_id(
    update: Update | None = None, context: ContextTypes.DEFAULT_TYPE | None = None
) -> int:
    if context and hasattr(context, "job") and context.job and hasattr(context.job, "chat_id"):
        if context.job.chat_id is not None:
            return context.job.chat_id
        else:
            raise ValueError("context.job.chat_id is None")
    elif update and update.effective_chat:
        return update.effective_chat.id
    else:
        raise ValueError("Unable to determine chat_id")


# Async function to get the price of a cryptocurrency from Binance API
async def get_crypto_price(crypto_id: str, retries: int = 3, delay: int = 1) -> float | None:
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={crypto_id}EUR"
    for attempt in range(1, retries + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logging.warning(
                            f"Binance API responded with {response.status} for {crypto_id} (Attempt {attempt})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    data = await response.json()
                    return float(data.get("price", 0))
        except aiohttp.ClientError as e:
            logging.warning(f"Network error on attempt {attempt} for {crypto_id}: {e}")
            await asyncio.sleep(delay)
        except (KeyError, ValueError, TypeError) as e:
            logging.error(f"Error parsing price for {crypto_id}: {e}")
            return None
    logging.error(f"Failed to get price for {crypto_id} after {retries} attempts")
    return None
