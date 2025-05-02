import csv
import requests
import os
import time
from datetime import datetime

# === CONFIGURAZIONE ===
BOT_TOKEN = "7912248885:AAFwOdg0rX3weVr6NXzW1adcUorvlRY8LyI"
CHAT_ID = "-1002522593547"  # Canale: POTYPOTY OVER 0.5 HT

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=data)
        print("✅ Inviato:", response.text)
    except Exception as e:
        print("❌ Errore invio:", e)

def partita_è_iniziata(orario_stringa):
    try:
        orario_match = datetime.strptime(orario_stringa, "%b %d %Y - %I:%M%p")
        adesso = datetime.now()
        return adesso >= orario_match
    except Exception as e:
        print("❌ Errore conversione orario:", e)
        return False

def leggi_partite_attive():
    partite = []
    if not os.path.exists("matches.csv"):
        print("⚠️ File matches.csv non trovato.")
        return partite

    with open("matches.csv", newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        for riga in reader:
            try:
                home_team = riga[4]
                away_team = riga[5]
                orario = riga[1]
                over05_ht = float(riga[12])  # colonna 13 (index 12)

                if over05_ht >= 85 and partita_è_iniziata(orario):
                    partite.append((home_team, away_team, orario, over05_ht))
            except Exception as e:
                print("❌ Errore su riga:", e)
                continue

    return partite

def main():
    print("🚀 Bot attivo su Render – modalità PREMATCH filtrata per orario")
    send_telegram_message("✅ Bot attivo – invierò solo *le partite che stanno per iniziare*")

    partite = leggi_partite_attive()
    print(f"⏰ Partite in partenza: {len(partite)}")

    for home, away, orario, over in partite:
        messaggio = (
            f"⚠️ *PARTITA APPENA INIZIATA*\n"
            f"{home} vs {away}\n"
            f"🕒 Orario: {orario}\n"
            f"🔥 Over 0.5 HT: *{over}%*"
        )
        send_telegram_message(messaggio)
        time.sleep(1.5)

if __name__ == "__main__":
    main()
