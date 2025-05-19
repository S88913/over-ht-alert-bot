import csv
import requests
import os
import time
from datetime import datetime
import pytz

# === CONFIG ===
BOT_TOKEN = "7912248885:AAFwOdg0rX3weVr6NXzW1adcUorvlRY8LyI"
CHAT_ID = "6146221712"
FILE_NOTIFICATI = "notificati.txt"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=data)
        print("✅ Inviato:", response.text)
    except Exception as e:
        print("❌ Errore invio:", e)

def partita_ora_inizio(orario_str):
    try:
        match_utc = datetime.strptime(orario_str, "%b %d %Y - %I:%M%p")
        match_utc = pytz.utc.localize(match_utc)
        now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        return abs((now_utc - match_utc).total_seconds()) <= 180
    except Exception as e:
        print("❌ Errore orario:", e)
        return False

def converti_orario_a_locale(orario_str):
    try:
        match_utc = datetime.strptime(orario_str, "%b %d %Y - %I:%M%p")
        match_utc = pytz.utc.localize(match_utc)
        italy = pytz.timezone("Europe/Rome")
        match_locale = match_utc.astimezone(italy)
        return match_locale.strftime("%H:%M")
    except Exception as e:
        print("❌ Errore conversione orario:", e)
        return orario_str

def carica_notificati():
    if not os.path.exists(FILE_NOTIFICATI):
        return set()
    with open(FILE_NOTIFICATI, "r") as f:
        return set(line.strip() for line in f)

def salva_notificato(match_id):
    with open(FILE_NOTIFICATI, "a") as f:
        f.write(f"{match_id}\n")

def leggi_partite_attive(notificati):
    partite = []
    if not os.path.exists("matches.csv"):
        print("⚠️ File matches.csv non trovato.")
        return partite

    with open("matches.csv", newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)

        for riga in reader:
            try:
                nazione = riga[2]
                campionato = riga[3]
                home_team = riga[4]
                away_team = riga[5]
                orario = riga[1]
                over05_ht = float(riga[17])

                # Crea ID unico della partita
                match_id = f"{home_team}_{away_team}_{orario}"

                if over05_ht >= 85 and partita_ora_inizio(orario) and match_id not in notificati:
                    partite.append((match_id, nazione, campionato, home_team, away_team, orario, over05_ht))
            except Exception as e:
                print("❌ Riga saltata:", e)
                continue
    return partite

def main():
    print("🚀 Bot attivo – con filtro 85% e blocco duplicati")
    notificati = carica_notificati()
    partite = leggi_partite_attive(notificati)
    print(f"⏰ Partite valide da inviare: {len(partite)}")

    for match_id, nazione, campionato, home, away, orario, over in partite:
        orario_locale = converti_orario_a_locale(orario)
        messaggio = (
            f"⚠️ *PARTITA APPENA INIZIATA*\n"
            f"{nazione} – {campionato}\n"
            f"{home} vs {away}\n"
            f"🕒 Orario: {orario_locale}\n"
            f"🔥 Over 0.5 HT: *{round(over, 1)}%*"
        )
        send_telegram_message(messaggio)
        salva_notificato(match_id)
        time.sleep(1.5)

if __name__ == "__main__":
    main()
