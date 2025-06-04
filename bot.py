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
CSV_FILE = "matches_expanded-1749075255-potipoti.csv"   # <-- il nome esatto del file caricato!
OVER25_FILE = "over25_prematch.txt"
OVER25_SENT_FLAG = "over25_sent.flag"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        print("✅ Inviato:", message.splitlines()[0])
    except Exception as e:
        print("❌ Errore invio:", e)

def send_telegram_file(filepath, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(filepath, "rb") as doc:
        data = {"chat_id": CHAT_ID, "caption": caption}
        files = {"document": doc}
        try:
            response = requests.post(url, data=data, files=files)
            response.raise_for_status()
            print(f"✅ File inviato: {filepath}")
        except Exception as e:
            print("❌ Errore invio file:", e)

def partita_appena_iniziata(orario_str):
    try:
        match_utc = datetime.strptime(orario_str, "%d/%m/%Y,%H:%M")
        match_utc = pytz.timezone("Europe/Rome").localize(match_utc)
        now_utc = datetime.now(pytz.timezone("Europe/Rome"))
        delta = abs((match_utc - now_utc).total_seconds())
        return delta <= 90
    except Exception as e:
        print("❌ Errore parsing orario:", e)
        return False

def partita_tra_poco(orario_str, minuti_offset=10):
    try:
        match_utc = datetime.strptime(orario_str, "%d/%m/%Y,%H:%M")
        match_utc = pytz.timezone("Europe/Rome").localize(match_utc)
        now_utc = datetime.now(pytz.timezone("Europe/Rome"))
        delta = (match_utc - now_utc).total_seconds()
        return 60 <= delta <= 60 * minuti_offset
    except Exception as e:
        print("❌ Errore parsing orario:", e)
        return False

def converti_orario_a_locale(orario_str):
    try:
        dt = datetime.strptime(orario_str, "%d/%m/%Y,%H:%M")
        return dt.strftime("%H:%M")
    except Exception:
        return orario_str.split(",")[1] if "," in orario_str else orario_str

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
        print("⚠️ File CSV non trovato.")
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
                orario_data = f"{riga[0]},{riga[1]}"
                over25 = float(riga[6].replace(",", "."))
                btts = float(riga[7].replace(",", "."))
                over05ht = float(riga[8].replace(",", ".")) if len(riga) > 8 else 0.0
                if "esport" in nazione.lower() or "esoccer" in campionato.lower():
                    continue
                base_id = f"{home}_{away}_{orario_data}"
                id_05ht = f"{base_id}-over05ht"
                id_over25 = f"{base_id}-over25"
                if partita_appena_iniziata(orario_data) and over05ht >= 85 and id_05ht not in notificati:
                    partite_05ht.append((id_05ht, nazione, campionato, home, away, orario_data, over05ht))
                if over25 >= 85:
                    partite_over25.append((id_over25, nazione, campionato, home, away, orario_data, over25, btts))
            except Exception as e:
                print("❌ Riga saltata:", e)
                continue
    return partite_05ht, partite_over25

def esporta_over25(partite_over25):
    if not partite_over25:
        return None
    oggi = datetime.now(pytz.timezone("Europe/Rome")).strftime("%d/%m/%Y")
    with open(OVER25_FILE, "w", encoding="utf-8") as f:
        f.write(f"OVER 2.5 PREMATCH DEL GIORNO (≥85%) - {oggi}\n")
        f.write("-" * 40 + "\n")
        for match in partite_over25:
            _, nazione, campionato, home, away, orario_data, over25, btts = match
            orario = converti_orario_a_locale(orario_data)
            f.write(f"{orario} | {nazione} | {campionato}\n")
            f.write(f"{home} vs {away} | O2.5: {over25}% | BTTS: {btts}%\n")
            f.write("-" * 40 + "\n")
    return OVER25_FILE

def main():
    print("🚀 Bot prematch attivo...")
    notificati = carica_notificati()
    partite_05ht, partite_over25 = leggi_partite(notificati)

    # 1. Notifiche Over 0.5 HT, come sempre
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

    # 2. Invio file txt Over 2.5 SOLO una volta!
    today = datetime.now(pytz.timezone("Europe/Rome")).strftime("%Y-%m-%d")
    flagfile = OVER25_SENT_FLAG + today
    if partite_over25 and not os.path.exists(flagfile):
        filepath = esporta_over25(partite_over25)
        if filepath:
            send_telegram_file(filepath, "📄 Over 2.5 prematch del giorno (≥85%)")
            with open(flagfile, "w") as f:
                f.write("sent")
            print("✅ File OVER 2.5 inviato una sola volta.")

if __name__ == "__main__":
    main()
