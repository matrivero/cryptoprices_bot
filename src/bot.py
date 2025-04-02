import logging

from config import TOKEN
from handlers.admin import list_users
from handlers.alerts import add_alert, clear_alerts, list_alerts, remove_alert
from handlers.base import help, post_init, price, start
from telegram.ext import Application, CommandHandler

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )

    application = Application.builder().token(TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("price", price))
    application.add_handler(CommandHandler("addalert", add_alert))
    application.add_handler(CommandHandler("listalerts", list_alerts))
    application.add_handler(CommandHandler("removealert", remove_alert))
    application.add_handler(CommandHandler("clearalerts", clear_alerts))
    application.add_handler(CommandHandler("listusers", list_users))

    application.run_polling()
