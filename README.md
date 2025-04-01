# 🪙 Crypto Price Alert Bot

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Dockerized](https://img.shields.io/badge/docker-ready-blueviolet)](https://www.docker.com/)
[![Made with ❤️](https://img.shields.io/badge/made%20with-%E2%9D%A4-red)](#)

A production-ready **Telegram Bot** to get cryptocurrency prices and receive real-time price alerts via the Binance API.

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
- python-telegram-bot[job-queue]
- A Telegram Bot Token from [BotFather](https://t.me/botfather)
- No Binance API key required (public endpoints)