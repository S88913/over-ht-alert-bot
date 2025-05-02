import csv
import requests
import os
import time
from datetime import datetime, timedelta

# === CONFIG ===
BOT_TOKEN = "7912248885:AAFwOdg0rX3weVr6NXzW1adcUorvlRY8LyI"
CHAT_ID = "-1002522593547"  # Canale Telegram

# === FUNZIONI ===

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

def partita_ora_inizio(orario_str):
    try:
        # Esempio orario: "May 02 2025 - 5:30pm"
        orario = datetime.strptime(orario_str, "%b %d %Y - %I:%M%p")
        ora_attuale = datetime.now()

        # Confronta: invia solo se è entro ±3 minuti rispetto a ora
        return abs((ora_attuale - orario).total_seconds()) <= 180
    except Exception as e:
        print("❌ Errore orario:", e)
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
                over05_ht = float(riga[12])

                if over05_ht >= 85 and partita_ora_inizio(orario):
                    partite.append((home_team, away_team, orario, over05_ht))
            except Exception as e:
                print("❌ Riga saltata:", e)
                continue
    return partite

def main():
    print("🚀 Bot attivo – invia solo partite che stanno per iniziare (±3 minuti)")
    partite = leggi_partite_attive()
    print(f"⏰ Partite in orario adesso: {len(partite)}")

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
