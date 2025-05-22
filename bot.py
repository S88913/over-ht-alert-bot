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
    try:
        match_utc = datetime.strptime(orario_str, "%b %d %Y - %I:%M%p")
        match_utc = pytz.utc.localize(match_utc)
        now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        delta = abs((match_utc - now_utc).total_seconds())
        return delta <= 90  # entro 90 secondi dal fischio d'inizio
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
    partite_multipla = []

    if not os.path.exists(CSV_FILE):
        print("⚠️ File matches.csv non trovato.")
        return [], [], []

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

                base_id = f"{home}_{away}_{orario}"
                id_05ht = f"{base_id}-over05ht"
                id_over25 = f"{base_id}-over25"
                id_multipla = f"{base_id}-multipla"

                if partita_appena_iniziata(orario) and over05ht >= 85 and id_05ht not in notificati:
                    partite_05ht.append((id_05ht, nazione, campionato, home, away, orario, over05ht))

                if partita_tra_poco(orario, 5) and over25 >= 80 and id_over25 not in notificati:
                    partite_over25.append((id_over25, nazione, campionato, home, away, orario, over25, btts))

                if partita_tra_poco(orario, 10) and over05ht >= 85 and over25 >= 80 and btts >= 75 and id_multipla not in notificati:
                    partite_multipla.append((id_multipla, nazione, campionato, home, away, orario, over05ht, over25, btts))

            except Exception as e:
                print("❌ Riga saltata:", e)
                continue

    return partite_05ht, partite_over25, partite_multipla


def main():
    print("🚀 Bot prematch attivo...")
    notificati = carica_notificati()
    partite_05ht, partite_over25, partite_multipla = leggi_partite(notificati)

    for match in partite_05ht:
        match_id, nazione, campionato, home, away, orario, over = match
        orario_locale = converti_orario_a_locale(orario)
        messaggio = (
            f"⚡️ *OVER 0.5 PRIMO TEMPO*\n"
            f"🌍 {nazione} | {campionato}\n"
            f"⚽ {home} vs {away}\n"
            f"🕒 Ore: *{orario_locale}*\n"
            f"📊 Over 0.5 HT: *{round(over, 1)}%*\n"
        )
        send_telegram_message(messaggio)
        salva_notificato(match_id)
        time.sleep(1.5)

    for match in partite_over25:
        match_id, nazione, campionato, home, away, orario, over25, btts = match
        orario_locale = converti_orario_a_locale(orario)
        messaggio = (
            f"🔥 *SEGNALAZIONE OVER 2.5*\n"
            f"🌍 {nazione} | {campionato}\n"
            f"⚽ {home} vs {away}\n"
            f"🕒 Ore: *{orario_locale}*\n"
            f"📈 O2.5: *{round(over25,1)}%* | BTTS: *{round(btts,1)}%*\n"
        )
        send_telegram_message(messaggio)
        salva_notificato(match_id)
        time.sleep(1.5)

    if partite_multipla:
        messaggio_multi = "💎 *MULTIPLA DEL GIORNO*\nTre partite ad alto valore:\n"
        for match in partite_multipla[:3]:
            match_id, nazione, campionato, home, away, orario, over05, over25, btts = match
            orario_locale = converti_orario_a_locale(orario)
            messaggio_multi += (
                f"\n🔹 *{home} vs {away}* ({nazione} - {campionato})\n"
                f"🕒 {orario_locale} | 0.5HT: *{round(over05,1)}%*, O2.5: *{round(over25,1)}%*, BTTS: *{round(btts,1)}%*\n"
            )
            salva_notificato(match_id)
        send_telegram_message(messaggio_multi)


if __name__ == "__main__":
    main()
