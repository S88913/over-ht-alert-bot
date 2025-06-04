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
CSV_FILE = "matches.csv"
FILE_SENT_OVER25 = "over25_sent.txt"   # Serve per inviare solo una volta il file

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        print("✅ Inviato:", message.splitlines()[0])
    except Exception as e:
        print("❌ Errore invio:", e)

def send_telegram_file(filepath, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(filepath, "rb") as f:
        files = {"document": f}
        data = {"chat_id": CHAT_ID, "caption": caption}
        try:
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            print(f"✅ File inviato: {filepath}")
        except Exception as e:
            print("❌ Errore invio file:", e)

def partita_appena_iniziata(orario_str):
    try:
        match_utc = datetime.strptime(orario_str, "%b %d %Y - %I:%M%p")
        match_utc = pytz.utc.localize(match_utc)
        now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        delta = abs((match_utc - now_utc).total_seconds())
        return delta <= 90  # entro 90 secondi dal fischio d'inizio
    except Exception as e:
        print("❌ Errore parsing orario:", e)
        return False

def partita_tra_oggi(orario_str):
    try:
        match_utc = datetime.strptime(orario_str, "%b %d %Y - %I:%M%p")
        match_utc = pytz.utc.localize(match_utc)
        today_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        return match_utc.date() == today_utc.date()
    except Exception as e:
        print("❌ Errore parsing orario (tra_oggi):", e)
        return False

def converti_orario_a_locale(orario_str):
    try:
        match_utc = datetime.strptime(orario_str, "%b %d %Y - %I:%M%p")
        match_utc = pytz.utc.localize(match_utc)
        match_locale = match_utc.astimezone(pytz.timezone("Europe/Rome"))
        return match_locale.strftime("%H:%M")
    except Exception as e:
        print("❌ Errore conversione orario:", e)
        return orario_str

def carica_notificati():
    if not os.path.exists(FILE_NOTIFICATI):
        return set()
    with open(FILE_NOTIFICATI, "r") as f:
        return set(line.strip() for line in f if line.strip())

def salva_notificato(match_id):
    with open(FILE_NOTIFICATI, "a") as f:
        f.write(f"{match_id}\n")

def over25_file_sent_today():
    today = datetime.now(pytz.timezone("Europe/Rome")).strftime("%Y-%m-%d")
    if not os.path.exists(FILE_SENT_OVER25):
        return False
    with open(FILE_SENT_OVER25, "r") as f:
        last_sent = f.read().strip()
        return last_sent == today

def set_over25_file_sent():
    today = datetime.now(pytz.timezone("Europe/Rome")).strftime("%Y-%m-%d")
    with open(FILE_SENT_OVER25, "w") as f:
        f.write(today)

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
                # Solo calcio
                if "esport" in nazione.lower() or "esoccer" in campionato.lower():
                    continue
                base_id = f"{home}_{away}_{orario}"
                id_05ht = f"{base_id}-over05ht"
                if partita_appena_iniziata(orario) and over05ht >= 85 and id_05ht not in notificati:
                    partite_05ht.append((id_05ht, nazione, campionato, home, away, orario, over05ht))
                # Solo match di oggi per il file over 2.5
                if partita_tra_oggi(orario) and over25 >= 85:
                    partite_over25.append((nazione, campionato, home, away, orario, over25, btts))
            except Exception as e:
                print("❌ Riga saltata:", e)
                continue
    return partite_05ht, partite_over25

def scrivi_txt_over25(partite_over25, filename="over25_prematch.txt"):
    righe = []
    today = datetime.now(pytz.timezone("Europe/Rome")).strftime("%d/%m/%Y")
    righe.append(f"OVER 2.5 PREMATCH DEL GIORNO (≥85%) - {today}")
    righe.append("-" * 40)
    if not partite_over25:
        righe.append("Nessun match trovato.")
    else:
        for match in partite_over25:
            nazione, campionato, home, away, orario, over25, btts = match
            ora = converti_orario_a_locale(orario)
            righe.append(
                f"{ora} | {nazione} | {campionato}\n"
                f"{home} vs {away} | O2.5: {round(over25,1)}% | BTTS: {round(btts,1)}%\n"
            )
            righe.append("-" * 40)
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(righe))
    return filename

def main():
    print("🚀 Bot prematch attivo...")
    notificati = carica_notificati()
    partite_05ht, partite_over25 = leggi_partite(notificati)

    # INVIARE FILE SOLO UNA VOLTA AL GIORNO
    if not over25_file_sent_today():
        filename = scrivi_txt_over25(partite_over25)
        send_telegram_file(filename, caption="📄 Over 2.5 prematch del giorno (≥85%) – APRI IL FILE")
        set_over25_file_sent()
        os.remove(filename)  # elimina il file locale dopo invio

    # Notifiche over 0.5 HT come sempre
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

if __name__ == "__main__":
    main()
