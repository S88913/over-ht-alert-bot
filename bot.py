import requests
import telegram
from datetime import datetime

# === CONFIG ===
FOOTYSTATS_API_KEY = "972183dce49bfd4d567da3d61e8ab389b2e04334728101dcc4ba28f9d4f4d19e"
TELEGRAM_CHAT_ID = 6146221712
TELEGRAM_BOT_TOKEN = "7912248885:AAFwOdg0rX3weVr6NXzW1adcUorvlRY8LyI"
OVER_05_HT_THRESHOLD = 85  # Soglia percentuale

# === AVVIO TELEGRAM ===
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

def invia_messaggio(msg):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode=telegram.constants.ParseMode.MARKDOWN)
    except Exception as e:
        print("Errore invio messaggio Telegram:", e)

def ottieni_partite_oggi():
    url = "https://api.footystats.org/api/v1/fixtures"
    params = {
        "key": FOOTYSTATS_API_KEY,
        "date": datetime.today().strftime('%Y-%m-%d')
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except Exception as e:
        print("Errore durante la richiesta API FootyStats:", e)
        return []

def filtra_partite_valide(partite):
    partite_valide = []
    for partita in partite:
        try:
            probabilita = f
