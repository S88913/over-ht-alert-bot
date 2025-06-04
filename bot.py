import csv
import requests
import os
import time
from datetime import datetime
import pytz

# CONFIG
BOT_TOKEN = "7912248885:AAFwOdg0rX3weVr6NXzW1adcUorvlRY8LyI"
CHAT_ID = "6146221712"
FILE_NOTIFICATI = "notificati.txt"
CSV_FILE = "matches.csv"
OUTPUT_TXT = "over25_output.txt"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, data=data)

def send_telegram_document(file_path, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(file_path, 'rb') as file:
        data = {"chat_id": CHAT_ID, "caption": caption}
        files = {"document": file}
        requests.post(url, data=data, files=files)

def partita_appena_iniziata(orario_str):
    try:
        match_utc = datetime.strptime(orario_str, "%b %d %Y - %I:%M%p")
        match_utc = pytz.utc.localize(match_utc)
        now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        delta = abs((match_utc - now_utc).total_seconds())
        return delta <= 90
    except:
        return False

def converti_orario_a_locale(orario_str):
    try:
        match_utc = datetime.strptime(orario_str, "%b %d %Y - %I:%M%p")
        match_utc = pytz.utc.localize(match_utc)
        match_locale = match_utc.astimezone(pytz.timezone("Europe/Rome"))
        return match_locale.strftime("%H:%M")
    except:
        return orario_str

def carica_notificati():
    if not os.path.exists(FILE_NOTIFICATI):
        return set()
    with open(FILE_NOTIFICATI, "r") as f:
        return set(line.strip() for line in f if line.strip())

def salva_notificato(match_id):
    with open(FILE_NOTIFICATI, "a") as f:
        f.write(f"{match_id}\n")

def leggi_partite(notificati):
    partite_05ht = []
    partite_over25 = []

    if not os.path.exists(CSV_FILE):
        print("⚠️ File matches.csv non trovato.")
        return [], []

    with open(CSV_FILE, newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader, None)
        for riga in reader:
            try:
                nazione = riga[2]
                campionato = riga[3]
                home = riga[4]
                away = riga[5]
                orario = riga[1]
                over05ht = float(riga[17])
                btts = float(riga[14])
                over25 = float(riga[15])
                if "esport" in nazione.lower() or "esoccer" in campionato.lower():
                    continue
                base_id = f"{home}_{away}_{orario}"
                id_05ht = f"{base_id}-over05ht"
                id_over25 = f"{base_id}-over25"
                if partita_appena_iniziata(orario) and over05ht >= 85 and id_05ht not in notificati:
                    partite_05ht.append((id_05ht, nazione, campionato, home, away, orario, over05ht))
                if over25 >= 85:
                    partite_over25.append((id_over25, nazione, campionato, home, away, orario, over25, btts))
            except Exception as e:
                continue
    return partite_05ht, partite_over25

def crea_file_over25(partite_over25):
    today_str = datetime.now(pytz.timezone("Europe/Rome")).strftime("%d/%m/%Y")
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        f.write(f"🔥 SEGNALI OVER 2.5 DEL {today_str}\n")
        f.write("="*32+"\n\n")
        for match in partite_over25:
            _, nazione, campionato, home, away, orario, over25, btts = match
            orario_locale = converti_orario_a_locale(orario)
            f.write(
                f"{orario_locale} | {home} vs {away} ({nazione}, {campionato})\n"
                f"   O2.5: {round(over25,1)}%   BTTS: {round(btts,1)}%\n"
            )
            f.write("-"*26 + "\n")
    return OUTPUT_TXT

def main():
    print("🚀 Bot prematch attivo...")
    notificati = carica_notificati()
    partite_05ht, partite_over25 = leggi_partite(notificati)

    # Notifiche live solo Over 0.5 HT
    for match in partite_05ht:
        match_id, nazione, campionato, home, away, orario, over = match
        orario_locale = converti_orario_a_locale(orario)
        messaggio = (
            f"⚡️ *OVER 0.5 PRIMO TEMPO*\n"
            f"🌍 {nazione} | {campionato}\n"
            f"⚽ {home} vs {away}\n"
            f"🕒 Ore: *{orario_locale}*\n"
            f"📊 Over 0.5 HT: *{round(over, 1)}%*"
        )
        send_telegram_message(messaggio)
        salva_notificato(match_id)
        time.sleep(1.5)

    # Invio file SOLO se non esiste già oggi
    today_str = datetime.now(pytz.timezone("Europe/Rome")).strftime("%d-%m-%Y")
    output_today = f"over25_{today_str}.txt"
    if not os.path.exists(output_today):
        path = crea_file_over25(partite_over25)
        os.rename(path, output_today)
        send_telegram_document(output_today, caption=f"📄 Tutte le Over 2.5 (≥85%) del {today_str}")

if __name__ == "__main__":
    main()
