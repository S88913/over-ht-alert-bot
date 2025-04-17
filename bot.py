import csv
import time
import requests
import datetime
import os

BOT_TOKEN = "7912248885:AAFwOdg0rX3weVr6NXzW1adcUorvlRY8LyI"
CHANNEL_ID = "6146221712"  # o tuo user se vuoi ricevere i messaggi in privato

MIN_ODDS = 1.80
MAX_ODDS = 10.00

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": message}
    requests.post(url, data=data)

def leggi_partite():
    partite = []
    with open("matches.csv", newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                perc = float(row["First Half Goals Over 0.5 Probability"].replace("%", "").strip())
                if perc >= 85:
                    partita = {
                        "match": f"{row['Home Team']} vs {row['Away Team']}",
                        "league": row["League"],
                        "time": row["Time"],
                        "over05ht_prob": perc
                    }
                    partite.append(partita)
            except:
                continue
    return partite

def controlla_quote_live(partite):
    # Simulazione quote live - da sostituire con API reali
    for p in partite:
        simulated_odds = round(1.5 + (3 * time.time()) % 3, 2)
        if MIN_ODDS <= simulated_odds <= MAX_ODDS:
            msg = (
                f"⚽ {p['match']} ({p['league']})\n"
                f"🕒 Orario: {p['time']}\n"
                f"🔥 Probabilità Over 0.5 HT: {p['over05ht_prob']}%\n"
                f"📈 Quota LIVE: {simulated_odds}"
            )
            send_telegram_message(msg)

def main():
    while True:
        print(f"[{datetime.datetime.now()}] Controllo partite...")
        partite = leggi_partite()
        controlla_quote_live(partite)
        time.sleep(60)  # ogni 60 secondi

if __name__ == "__main__":
    main()
send_telegram_message("✅ TEST: Il bot è attivo e funzionante!")
