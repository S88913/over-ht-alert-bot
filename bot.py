import csv
import requests
import os
import time
from datetime import datetime, timedelta
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

def partita_ora_inizio(orario_str, minuti_offset=0):
    try:
        match_utc = datetime.strptime(orario_str, "%b %d %Y - %I:%M%p")
        match_utc = pytz.utc.localize(match_utc)
        now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        delta = (match_utc - now_utc).total_seconds()
        return -60 * minuti_offset <= delta <= 60  # tra -offset e +1 minuto
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

def leggi_partite(notificati):
    partite_05ht = []
    partite_over25 = []
    partite_bonus_multipla = []

    if not os.path.exists("matches.csv"):
        print("⚠️ File matches.csv non trovato.")
        return [], [], []

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
                over05ht = float(riga[17])
                btts = float(riga[14])
                over25 = float(riga[15])

                match_id = f"{home_team}_{away_team}_{orario}"

                if match_id in notificati:
                    continue

                # Over 0.5 HT - al fischio d'inizio
                if partita_ora_inizio(orario) and over05ht >= 85:
                    partite_05ht.append((match_id, nazione, campionato, home_team, away_team, orario, over05ht))

                # Over 2.5 – solo 5 min prima del calcio d’inizio
                elif partita_ora_inizio(orario, minuti_offset=5) and (over25 >= 70 or btts >= 75):
                    partite_over25.append((match_id, nazione, campionato, home_team, away_team, orario, over25, btts))

                # Multipla: tutti e tre sopra soglia
                if over05ht >= 85 and over25 >= 70 and btts >= 75 and partita_ora_inizio(orario, minuti_offset=5):
                    partite_bonus_multipla.append((match_id, nazione, campionato, home_team, away_team, orario, over05ht, over25, btts))

            except Exception as e:
                print("❌ Riga saltata:", e)
                continue

    return partite_05ht, partite_over25, partite_bonus_multipla

def main():
    print("🚀 Bot prematch aggiornato in esecuzione...")
    notificati = carica_notificati()
    partite_05ht, partite_over25, partite_bonus_multipla = leggi_partite(notificati)

    # Over 0.5 HT
    for match in partite_05ht:
        match_id, nazione, campionato, home, away, orario, over = match
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

    # Over 2.5 (singole)
    for match in partite_over25:
        match_id, nazione, campionato, home, away, orario, over25, btts = match
        orario_locale = converti_orario_a_locale(orario)
        messaggio = (
            f"💣 *SEGNALAZIONE OVER 2.5*\n"
            f"{nazione} – {campionato}\n"
            f"{home} vs {away}\n"
            f"🕒 Orario: {orario_locale}\n"
            f"📊 Over 2.5: *{round(over25,1)}%* – BTTS: *{round(btts,1)}%*"
        )
        send_telegram_message(messaggio)
        salva_notificato(match_id)
        time.sleep(1.5)

    # Multipla
    if partite_bonus_multipla:
        messaggio_multi = "*🎯 MULTIPLA BONUS GIORNALIERA*\nConsigliata per valore e % elevate:\n"
        for match in partite_bonus_multipla[:3]:
            match_id, nazione, campionato, home, away, orario, over05, over25, btts = match
            orario_locale = converti_orario_a_locale(orario)
            messaggio_multi += (
                f"\n▫️ {home} vs {away} – {nazione} ({campionato})\n"
                f"🕒 {orario_locale} | 0.5HT: *{round(over05,1)}%* – O2.5: *{round(over25,1)}%* – BTTS: *{round(btts,1)}%*\n"
            )
            salva_notificato(match_id)
        send_telegram_message(messaggio_multi)

if __name__ == "__main__":
    main()
