# 🪙 Crypto Price Alert Bot

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Dockerized](https://img.shields.io/badge/docker-ready-blueviolet)](https://www.docker.com/)
[![Made with ❤️](https://img.shields.io/badge/made%20with-%E2%9D%A4-red)](#)

A production-ready **Telegram Bot** to get cryptocurrency prices and receive real-time price alerts via the Binance API.

---

## 📖 Table of Contents

1. [✨ Features](#-features)  
2. [💡 Commands Overview](#-commands-overview)  
3. [📦 Requirements](#-requirements)  
4. [🚀 Setup](#-setup)  
5. [📋 Example Usage](#-example-usage)  
6. [🤝 Contributing](#-contributing) 
8. [🛠 Development](#-development)
9. [📜 License](#-license)

---

## ✨ Features

✅ Real-time crypto prices using Binance  
✅ Set customizable price alerts  
✅ Automatic alert notifications via Telegram  
✅ Command-based alert management  
✅ Configurable via `.env`  
✅ Fully Dockerized  
✅ Error-handling and retries included

---

## 💡 Commands Overview

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Show available commands |
| `/price <symbol>` | Get the latest price (e.g., `/price BTC`) |
| `/addalert <symbol> <above/below> <target_price>` | Add a price alert |
| `/listalerts` | List your active alerts |
| `/removealert <symbol> <above/below> <target_price>` | Remove a specific alert |
| `/clearalerts` | Clear all your alerts |
| `/listusers` | List users with active alerts |

---

## 📦 Requirements

- Python 3.11+
- A Telegram Bot Token from [BotFather](https://t.me/botfather)
- Docker

---

## 🚀 Setup

1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/cryptoprices_bot.git
    cd cryptoprices_bot
2. Create a `.env` file with your Telegram Bot Token and the list of user_id that will be able to run admin-specific commands:
    ```bash
    TOKEN=your_telegram_bot_token
    ADMINS=ADMIN_ID_1,ADMIN_ID_2,... # OPTIONAL    
3. Build and run the Docker container
    ```bash
    docker build -t cryptoprices-bot .
    docker run -d --env-file .env cryptoprices-bot  
---

## 📋 Example Usage

- To check the price of Bitcoin:
    ```bash
    /price BTC
- To set an alert when Ethereum goes above 2500:
    ```bash
    /addalert ETH above 2500
---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues, create pull requests, or suggest features.

---

## 🛠 Development

This project includes a `Makefile` to simplify common development tasks. Make sure you have [Poetry](https://python-poetry.org/) installed.

✅ Available Make Commands

| Command                | Description                                         |
|------------------------|-----------------------------------------------------|
| `make install`         | Install dependencies with Poetry, including dev dependencies |
| `make lint`            | Run `ruff` to check for linting issues             |
| `make format`          | Auto-format code using `ruff`                      |
| `make typecheck`       | Run static type checks using `mypy`                |
| `make check`           | Run linting, formatting, and type checks all together |
| `make run`             | Run the bot (`src/bot.py`)                         |
| `make tests`           | Run unit tests using `pytest`                      |
| `make setup-pre-commit`| Install pre-commit hooks                           |


🧪 Example Usage

- To install dependencies and run the bot:
    ```bash
    make install
    make run
- To check code quality before pushing:
    ```bash
    make check
---

## 📜 License

This project is licensed under the [MIT License](https://opensource.org/license/mit).