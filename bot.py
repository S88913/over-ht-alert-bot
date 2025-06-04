import csv
import requests
import os
import time
from datetime import datetime
import pytz
import hashlib

# === CONFIG ===
BOT_TOKEN = "7912248885:AAFwOdg0rX3weVr6NXzW1adcUorvlRY8LyI"
CHAT_ID = "6146221712"
FILE_NOTIFICATI = "notificati.txt"
CSV_FILE = "matches.csv"
HASH_FILE = "over25_hash.txt"

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
    # Support both formats
    try:
        match_utc = parse_datetime(orario_str)
        if match_utc is None:
            return False
        now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        delta = abs((match_utc - now_utc).total_seconds())
        return delta <= 90
    except Exception as e:
        print("❌ Errore parsing orario:", e)
        return False

def partita_oggi(orario_str):
    try:
        match_utc = parse_datetime(orario_str)
        if match_utc is None:
            return False
        today_utc = datetime.utcnow().date()
        # Confronto la data UTC del match con oggi (UTC)
        return match_utc.date() == today_utc
    except Exception as e:
        print("❌ Errore parsing orario (oggi):", e)
        return False

def parse_datetime(orario_str):
    # Prova formati: "Jun 05 2025 - 01:00AM" e "05/06/2025,01:00"
    try:
        # vecchio formato
        if "-" in orario_str and ":" in orario_str and orario_str[0].isalpha():
            return pytz.utc.localize(datetime.strptime(orario_str, "%b %d %Y - %I:%M%p"))
        # nuovo formato: data,ora   esempio "05/06/2025,01:00"
        elif "/" in orario_str and "," in orario_str:
            data, ora = orario_str.split(",")
            giorno, mese, anno = data.strip().split("/")
            # Costruisce il datetime UTC
            dt = datetime(int(anno), int(mese), int(giorno), int(ora.split(":")[0]), int(ora.split(":")[1]))
            return pytz.utc.localize(dt)
    except Exception as e:
        print(f"❌ Errore parse_datetime: {e}")
    return None

def converti_orario_a_locale(orario_str):
    try:
        match_utc = parse_datetime(orario_str)
        if match_utc is None:
            return orario_str
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

def file_hash(filepath):
    # Hash veloce del contenuto del file (usato per l'anti-duplicazione)
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        while True:
            data = f.read(4096)
            if not data: break
            h.update(data)
    return h.hexdigest()

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
                # Formato orario adattivo
                if len(riga) > 1 and ":" in riga[1]:
                    orario = f"{riga[0]},{riga[1]}"
                else:
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
                if partita_oggi(orario) and over25 >= 85:
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

    # File hash anti-duplicazione
    if os.path.exists(CSV_FILE):
        current_hash = file_hash(CSV_FILE)
    else:
        current_hash = ""

    hash_sent = ""
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r") as f:
            hash_sent = f.read().strip()

    if partite_over25 and current_hash != hash_sent:
        filename = scrivi_txt_over25(partite_over25)
        send_telegram_file(filename, caption="📄 Over 2.5 prematch del giorno (≥85%) – APRI IL FILE")
        with open(HASH_FILE, "w") as f:
            f.write(current_hash)
        os.remove(filename)  # elimina il file locale dopo invio

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
