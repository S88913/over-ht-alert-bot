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

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        print("✅ Inviato:", message.splitlines()[0])
    except Exception as e:
        print("❌ Errore invio:", e)

def partita_appena_iniziata(orario_str):
    # Prova con più formati
    for fmt in ["%d/%m/%Y,%H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M"]:
        try:
            match_locale = datetime.strptime(orario_str, fmt)
            now_locale = datetime.now()
            delta = (match_locale - now_locale).total_seconds()
            # Notifica se la partita è appena iniziata (entro 90 secondi)
            return 0 <= delta <= 90
        except Exception:
            continue
    return False

def partita_tra_poco(orario_str, minuti_offset=10):
    for fmt in ["%d/%m/%Y,%H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M"]:
        try:
            match_locale = datetime.strptime(orario_str, fmt)
            now_locale = datetime.now()
            delta = (match_locale - now_locale).total_seconds()
            return 60 <= delta <= 60 * minuti_offset
        except Exception:
            continue
    return False

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
    # Leggiamo solo partite di calcio (esclude eSports e altro)
    if not os.path.exists(CSV_FILE):
        print("⚠️ File matches.csv non trovato.")
        return [], []

    with open(CSV_FILE, newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                nazione = row.get("Nazione", "")
                campionato = row.get("Campionato", "")
                home = row.get("Home", "")
                away = row.get("Away", "")
                orario = f'{row.get("Data","")},{row.get("Ora","")}'
                over25 = float(row.get("Over 2.5", 0))
                btts = float(row.get("BTTS", 0))
                # Leggi Over 0.5 HT se c'è la colonna (se non c'è, skippa)
                over05ht = float(row.get("Over 0.5 HT", 0)) if "Over 0.5 HT" in row else None

                # Escludi tutto ciò che NON è calcio
                if nazione.lower() == "esports":
                    continue

                base_id = f"{home}_{away}_{orario}"

                # OVER 0.5 HT APPENA INIZIA
                if over05ht is not None and over05ht >= 85 and partita_appena_iniziata(orario) and (base_id + "-over05ht") not in notificati:
                    partite_05ht.append((base_id + "-over05ht", nazione, campionato, home, away, orario, over05ht))

                # OVER 2.5 SOLO SE >=80%
                forza = ""
                if over25 >= 90:
                    forza = "💪"
                elif over25 >= 85:
                    forza = "✅"
                elif over25 >= 80:
                    forza = "⚠️"
                if over25 >= 80 and partita_tra_poco(orario, 15) and (base_id + "-over25") not in notificati:
                    partite_over25.append((base_id + "-over25", nazione, campionato, home, away, orario, over25, btts, forza))

            except Exception as e:
                print("❌ Riga saltata:", e)
                continue

    return partite_05ht, partite_over25

def main():
    print("🚀 Bot prematch attivo...")
    notificati = carica_notificati()
    partite_05ht, partite_over25 = leggi_partite(notificati)

    # NOTIFICA OVER 0.5 HT APPENA INIZIA
    for match in partite_05ht:
        match_id, nazione, campionato, home, away, orario, over = match
        messaggio = (
            f"⚡️ *OVER 0.5 PRIMO TEMPO*\n"
            f"🌍 {nazione} | {campionato}\n"
            f"⚽ {home} vs {away}\n"
            f"🕒 Ore: *{row['Ora']}*\n"
            f"📊 Over 0.5 HT: *{round(over, 1)}%*"
        )
        send_telegram_message(messaggio)
        salva_notificato(match_id)
        time.sleep(1.5)

    # NOTIFICA OVER 2.5 SOLO SE >=80% + indicatore forza
    for match in partite_over25:
        match_id, nazione, campionato, home, away, orario, over25, btts, forza = match
        ora = orario.split(",")[1] if "," in orario else orario
        messaggio = (
            f"🔥 *SEGNALAZIONE OVER 2.5* {forza}\n"
            f"🌍 {nazione} | {campionato}\n"
            f"⚽ {home} vs {away}\n"
            f"🕒 Ore: *{ora}*\n"
            f"📈 O2.5: *{round(over25,1)}%* | BTTS: *{round(btts,1)}%*"
        )
        send_telegram_message(messaggio)
        salva_notificato(match_id)
        time.sleep(1.5)

if __name__ == "__main__":
    main()
