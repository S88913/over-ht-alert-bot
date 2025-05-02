import csv
import requests
import os

# === CONFIGURAZIONE ===
BOT_TOKEN = "7912248885:AAFwOdg0rX3weVr6NXzW1adcUorvlRY8LyI"
CHAT_ID = "6146221712"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=data)
        print("✅ Inviato:", response.text)
    except Exception as e:
        print("❌ Errore invio:", e)

def leggi_partite_prematch():
    partite_valide = []
    if not os.path.exists("matches.csv"):
        print("⚠️ File matches.csv non trovato.")
        return partite_valide

    with open("matches.csv", newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        for riga in reader:
            try:
                home_team = riga[4]
                away_team = riga[5]
                orario = riga[1]
                over05_ht = float(riga[12])  # colonna 13 (index 12)

                if over05_ht >= 85:
                    partite_valide.append((home_team, away_team, orario, over05_ht))
            except Exception as e:
                print("❌ Errore su riga:", e)
                continue

    return partite_valide

def main():
    print("🚀 Bot attivo su Render – modalità PREMATCH (senza quota)")
    send_telegram_message("✅ Il bot è attivo – controllo *PreMatch* in corso")

    partite = leggi_partite_prematch()
    print(f"📊 Partite trovate: {len(partite)}")

    for home, away, orario, over in partite:
        messaggio = (
            f"⚠️ *PARTITA DA MONITORARE LIVE*\n"
            f"{home} vs {away}\n"
            f"🕒 Orario: {orario}\n"
            f"🔥 Over 0.5 HT: *{over}%*"
        )
        send_telegram_message(messaggio)

if __name__ == "__main__":
    main()
