import csv
import requests
import os

# === CONFIGURAZIONE ===
BOT_TOKEN = "7912248885:AAFwOdg0rX3weVr6NXzW1adcUorvlRY8LyI"
CHAT_ID = "6146221712"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data)
        print("✅ Inviato:", response.text)
    except Exception as e:
        print("❌ Errore invio:", e)

def leggi_partite_da_csv():
    partite = []
    if not os.path.exists("matches.csv"):
        print("⚠️ File matches.csv non trovato.")
        return partite
    try:
        with open("matches.csv", newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for riga in reader:
                try:
                    over = float(riga.get("Over 0.5 HT", "0").replace("%", "").strip())
                    if over >= 85:
                        partite.append(riga)
                except:
                    continue
    except Exception as e:
        print("❌ Errore lettura CSV:", e)
    return partite

def invia_notifiche_prematch():
    partite = leggi_partite_da_csv()
    print(f"📊 Partite pre-match da notificare: {len(partite)}")
    for p in partite:
        msg = (
            f"⚠️ *PARTITA DA MONITORARE LIVE*\n"
            f"{p.get('Home Team')} vs {p.get('Away Team')}\n"
            f"🕒 Orario: {p.get('Time')}\n"
            f"🔥 Over 0.5 HT: {p.get('Over 0.5 HT')}%"
        )
        send_telegram_message(msg)

def main():
    print("🚀 Bot attivo su Render")
    send_telegram_message("✅ Il bot è attivo su Render – modalità *PreMatch*")
    invia_notifiche_prematch()

if __name__ == "__main__":
    main()
