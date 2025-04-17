import csv
import time
import requests
import datetime

BOT_TOKEN = "7912248885:AAFwOdg0rX3weVr6NXzW1adcUorvlRY8LyI"
CHANNEL_ID = "6146221712"  # <-- tuo ID personale da @userinfobot

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": message}
    response = requests.post(url, data=data)
    print(response.text)  # <-- per debug nei logs
