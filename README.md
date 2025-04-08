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
7. [📜 License](#-license)

---

## ✨ Features

✅ Real-time crypto prices using Binance  
✅ Set customizable price alerts  
✅ Automatic alert notifications via Telegram  
✅ Persistent or in-memory alerts (optional)  
✅ Alert rescheduling after bot restarts  
✅ Command-based alert management  
✅ Configurable via `.env` and `config.yaml`  
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
2. Create a `.env` file with your Telegram Bot Token and the list of admin users:
    ```bash
    TELEGRAM_TOKEN=your_telegram_bot_token
    ADMINS=ADMIN_ID_1,ADMIN_ID_2,...
3. Build and run the Docker container
    ```bash
    docker build -t cryptoprices-bot .
    docker run --env-file .env cryptoprices-bot

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

## 📜 License

This project is licensed under the MIT License.