import requests
import telegram
from datetime import datetime

# === CONFIG ===
FOOTYSTATS_API_KEY = "972183dce49bfd4d567da3d61e8ab389b2e04334728101dcc4ba28f9d4f4d19e"
TELEGRAM_CHAT_ID = 6146221712
TELEGRAM_BOT_TOKEN = "7912248885:AAFwOdg0rX3weVr6NXzW1adcUorvlRY8LyI"
OVER_05_HT_THRESHOLD = 85  # soglia minima per considerare una partita

# === AVVIO TELEGRAM ===
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

def invia_messaggio(msg):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode=telegram.ParseMode.MARKDOWN)
    except Exception as e:
        print("Errore invio messaggio Telegram:", e)

def ottieni_partite_oggi():
    url = "https://api.footystats.org/api/v1/fixtures"
    params = {
        "key": FOOTYSTATS_API_KEY,
        "date": datetime.today().strftime('%Y-%m-%d'),
        "timezone": "Europe/Rome"
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
            probabilita = float(partita.get("ht_over05", 0) or 0)
            if probabilita >= OVER_05_HT_THRESHOLD:
                partite_valide.append(partita)
        except Exception:
            continue
    return partite_valide

def invia_notifiche():
    print("✅ SCRIPT AVVIATO – controllo partite prematch")
    partite = ottieni_partite_oggi()
    if not partite:
        print("⚠️ Nessuna partita trovata.")
        return

    partite_valide = filtra_partite_valide(partite)
    if not partite_valide:
        print(f"⚠️ Nessuna partita supera la soglia del {OVER_05_HT_THRESHOLD}%")
        return

    for p in partite_valide:
        home = p.get("home_name", "")
        away = p.get("away_name", "")
        start_time = p.get("time", "")
        league = p.get("league_name", "")
        percentuale = p.get("ht_over05", "0")

        messaggio = (
            f"⚽ *PARTITA CONSIGLIATA – OVER 0.5 HT*\n"
            f"🏆 {league}\n"
            f"🕒 {start_time}\n"
            f"📊 Percentuale: *{percentuale}%*\n"
            f"📌 {home} vs {away}"
        )
        invia_messaggio(messaggio)

if __name__ == "__main__":
    invia_notifiche()
