import csv
import requests
import os
import time
from datetime import datetime

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

def partita_tra_poco(data_str, ora_str, minuti_offset=10):
    try:
        orario_str = f"{data_str} {ora_str}"
        match_locale = datetime.strptime(orario_str, "%d/%m/%Y %H:%M")
        now_locale = datetime.now()
        delta = (match_locale - now_locale).total_seconds()
        return 60 <= delta <= 60 * minuti_offset
    except Exception as e:
        print("❌ Errore parsing orario:", e)
        return False

def carica_notificati():
    if not os.path.exists(FILE_NOTIFICATI):
        return set()
    with open(FILE_NOTIFICATI, "r") as f:
        return set(line.strip() for line in f if line.strip())

def salva_notificato(match_id):
    with open(FILE_NOTIFICATI, "a") as f:
        f.write(f"{match_id}\n")

def main():
    notificati = carica_notificati()
    if not os.path.exists(CSV_FILE):
        print("⚠️ File matches.csv non trovato.")
        return

    with open(CSV_FILE, newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        header = next(reader, None)
        for riga in reader:
            try:
                # Indici: [0]Data, [1]Ora, [2]Nazione, [3]Campionato, [4]Home, [5]Away, [6]BTTS, [7]Over 0.5HT, [8]Over 2.5
                data = riga[0]
                ora = riga[1]
                nazione = riga[2]
                campionato = riga[3]
                home = riga[4]
                away = riga[5]
                btts = float(riga[6])
                over05ht = float(riga[7])
                over25 = float(riga[8])
                match_id_ht = f"{data}_{ora}_{home}_{away}_05HT"
                match_id_25 = f"{data}_{ora}_{home}_{away}_25"
                # Filtro solo calcio vero (no esports)
                if "esport" in nazione.lower() or "esoccer" in campionato.lower():
                    continue

                # OVER 0.5 HT: appena la partita inizia (entro i primi 90 secondi)
                if over05ht >= 85 and match_id_ht not in notificati:
                    orario_match = f"{data} {ora}"
                    match_locale = datetime.strptime(orario_match, "%d/%m/%Y %H:%M")
                    now_locale = datetime.now()
                    delta = (match_locale - now_locale).total_seconds()
                    if -90 <= delta <= 90:  # Partita appena iniziata
                        messaggio = (
                            f"⚡️ *OVER 0.5 PRIMO TEMPO*\n"
                            f"🌍 {nazione} | {campionato}\n"
                            f"⚽ {home} vs {away}\n"
                            f"🕒 Ore: *{ora}*\n"
                            f"📊 Over 0.5 HT: *{round(over05ht, 1)}%*"
                        )
                        send_telegram_message(messaggio)
                        salva_notificato(match_id_ht)
                        time.sleep(1.5)
                # OVER 2.5 prematch (entro 10 minuti dall'inizio)
                if over25 >= 80 and match_id_25 not in notificati:
                    if partita_tra_poco(data, ora, minuti_offset=10):
                        # Indicatore di forza
                        if over25 >= 90 and btts >= 90:
                            forza = "🔴 Massima Forza"
                        elif over25 >= 85 and btts >= 85:
                            forza = "🟠 Alta Forza"
                        else:
                            forza = "🟡 Buona Forza"
                        messaggio = (
                            f"🔥 *SEGNALAZIONE OVER 2.5*\n"
                            f"🌍 {nazione} | {campionato}\n"
                            f"⚽ {home} vs {away}\n"
                            f"🕒 Ore: *{ora}*\n"
                            f"📈 O2.5: *{round(over25,1)}%* | BTTS: *{round(btts,1)}%*\n"
                            f"{forza}"
                        )
                        send_telegram_message(messaggio)
                        salva_notificato(match_id_25)
                        time.sleep(1.5)
            except Exception as e:
                print("❌ Riga saltata:", e)
                continue

if __name__ == "__main__":
    main()
