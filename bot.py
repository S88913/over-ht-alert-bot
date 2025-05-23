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
CSV_FILE = "matches_expanded-1747982406-potipoti.csv"  # <-- aggiorna nome file se serve

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

def indicatore_forza(prob):
    # Restituisce una barra visiva della forza del segnale
    forza = int(round(prob / 20))  # 0-5 barre
    return "▌" * forza + " " * (5 - forza) + f" {round(prob,1)}%"

def leggi_partite(notificati):
    partite_05ht = []
    partite_over25 = []
    # Detect columns
    with open(CSV_FILE, newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        intestazione = next(reader)
        idx = {k: i for i, k in enumerate(intestazione)}
        for riga in reader:
            try:
                nazione = riga[idx['Nazione']] if 'Nazione' in idx else riga[2]
                campionato = riga[idx['Campionato']] if 'Campionato' in idx else riga[3]
                home = riga[idx['Home']] if 'Home' in idx else riga[4]
                away = riga[idx['Away']] if 'Away' in idx else riga[5]
                orario = riga[idx['Ora']] if 'Ora' in idx else riga[1]
                over05ht = float(riga[idx.get('Over 0.5 HT', idx.get('Over 0.5 HT %', 17))])
                over25 = float(riga[idx.get('Over 2.5', 6)])
                btts = float(riga[idx.get('BTTS', 7)])

                if nazione.lower().startswith("esport") or "virtual" in nazione.lower():
                    continue

                base_id = f"{home}_{away}_{orario}"
                id_05ht = f"{base_id}-over05ht"
                id_over25 = f"{base_id}-over25"

                if partita_appena_iniziata(orario) and over05ht >= 85 and id_05ht not in notificati:
                    partite_05ht.append((id_05ht, nazione, campionato, home, away, orario, over05ht))

                if partita_tra_poco(orario, 5) and over25 >= 80 and id_over25 not in notificati:
                    partite_over25.append((id_over25, nazione, campionato, home, away, orario, over25, btts))
            except Exception as e:
                print("❌ Riga saltata:", e)
                continue

    return partite_05ht, partite_over25

def main():
    print("🚀 Bot prematch attivo...")
    notificati = carica_notificati()
    partite_05ht, partite_over25 = leggi_partite(notificati)

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

    for match in partite_over25:
        match_id, nazione, campionato, home, away, orario, over25, btts = match
        orario_locale = converti_orario_a_locale(orario)
        forza = indicatore_forza(over25)
        messaggio = (
            f"🔥 *SEGNALAZIONE OVER 2.5*\n"
            f"🌍 {nazione} | {campionato}\n"
            f"⚽ {home} vs {away}\n"
            f"🕒 Ore: *{orario_locale}*\n"
            f"📈 O2.5: {forza} | BTTS: *{round(btts,1)}%*"
        )
        send_telegram_message(messaggio)
        salva_notificato(match_id)
        time.sleep(1.5)

if __name__ == "__main__":
    main()
