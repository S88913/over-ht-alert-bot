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
TXT_FILE = "over25_output.txt"
DATA_OGGI = datetime.now(pytz.timezone("Europe/Rome")).strftime("%d/%m/%Y")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        print("✅ Inviato:", message.splitlines()[0])
    except Exception as e:
        print("❌ Errore invio:", e)

def send_telegram_file(file_path, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(file_path, "rb") as file:
        files = {"document": file}
        data = {"chat_id": CHAT_ID, "caption": caption}
        try:
            response = requests.post(url, data=data, files=files)
            response.raise_for_status()
            print("✅ File inviato:", file_path)
        except Exception as e:
            print("❌ Errore invio file:", e)

def partita_appena_iniziata(orario_str):
    try:
        match_utc = datetime.strptime(orario_str, "%b %d %Y - %I:%M%p")
        match_utc = pytz.utc.localize(match_utc)
        now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        delta = abs((match_utc - now_utc).total_seconds())
        return delta <= 90
    except Exception as e:
        print("❌ Errore parsing orario:", e)
        return False

def partita_tra_poco(orario_str, minuti_offset=10):
    try:
        match_utc = datetime.strptime(orario_str, "%b %d %Y - %I:%M%p")
        match_utc = pytz.utc.localize(match_utc)
        now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        delta = (match_utc - now_utc).total_seconds()
        return 60 <= delta <= 60 * minuti_offset
    except Exception as e:
        print("❌ Errore parsing orario:", e)
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
                id_over25 = f"{base_id}-over25"
                # Notifica Over 0.5 HT appena inizia, solo se non già notificato
                if partita_appena_iniziata(orario) and over05ht >= 85 and id_05ht not in notificati:
                    partite_05ht.append((id_05ht, nazione, campionato, home, away, orario, over05ht))
                # Over 2.5 per file txt: almeno 85%, una sola volta al giorno
                if over25 >= 85:
                    partite_over25.append((orario, nazione, campionato, home, away, over25, btts))
            except Exception as e:
                print("❌ Riga saltata:", e)
                continue
    return partite_05ht, partite_over25

def scrivi_file_over25(partite_over25):
    with open(TXT_FILE, "w", encoding="utf-8") as f:
        f.write(f"OVER 2.5 PREMATCH DEL GIORNO (≥85%) - {DATA_OGGI}\n")
        f.write("-" * 40 + "\n")
        if not partite_over25:
            f.write("Nessuna partita trovata.\n")
        else:
            for p in partite_over25:
                orario, nazione, campionato, home, away, over25, btts = p
                orario_locale = orario
                f.write(f"{orario_locale} | {nazione} | {campionato}\n")
                f.write(f"{home} vs {away} | O2.5: {round(float(over25),1)}% | BTTS: {round(float(btts),1)}%\n")
                f.write("-" * 40 + "\n")

def main():
    print("🚀 Bot prematch attivo...")
    notificati = carica_notificati()
    partite_05ht, partite_over25 = leggi_partite(notificati)

    # 1. Notifiche OVER 0.5 HT (realtime, funzionano come sempre)
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

    # 2. File OVER 2.5 inviato solo UNA volta al giorno
    # Usa un flag temporaneo per non inviare più volte nella stessa giornata
    file_flag = f"file_sent_{DATA_OGGI}.flag"
    if not os.path.exists(file_flag):
        scrivi_file_over25(partite_over25)
        send_telegram_file(TXT_FILE, f"📄 Over 2.5 prematch del giorno (≥85%) - {DATA_OGGI}")
        open(file_flag, "w").close()  # Crea un file vuoto come flag per evitare invii ripetuti

if __name__ == "__main__":
    main()
