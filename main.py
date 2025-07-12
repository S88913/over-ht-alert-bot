# main.py - File principale per Render
import requests
import json
import time
from datetime import datetime
import os
import logging

# Setup logging per Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurazione da variabili d'ambiente (sicurezza per Render)
API_KEY = os.getenv('BET365_API_KEY', 'ef6ca400b4msh27cf7bcbe15ccdbp115debjsn05d47a0aaf0e')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '7912248885:AAFwOdg0rX3weVr6NXzW1adcUorvlRY8LyI')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '6146221712')

# Parametri configurabili
QUOTA_MINIMA = float(os.getenv('QUOTA_MINIMA', '1.40'))
QUOTA_MASSIMA = float(os.getenv('QUOTA_MASSIMA', '3.00'))
INTERVALLO_CONTROLLO = int(os.getenv('INTERVALLO_CONTROLLO', '120'))  # 2 minuti per Render
MAX_EVENTI_CONTROLLO = int(os.getenv('MAX_EVENTI_CONTROLLO', '15'))

BASE_URL = 'https://bet365data.p.rapidapi.com'

headers = {
    'x-rapidapi-host': 'bet365data.p.rapidapi.com',
    'x-rapidapi-key': API_KEY
}

# Cache per evitare duplicati
opportunita_segnalate = set()

def invia_messaggio_telegram(messaggio):
    """Invia messaggio al bot Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': messaggio,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("✅ Messaggio Telegram inviato!")
            return True
        else:
            logger.error(f"❌ Errore Telegram: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Errore invio Telegram: {e}")
        return False

def get_live_events():
    """Ottiene eventi live"""
    url = f"{BASE_URL}/live-events?sport=soccer"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            logger.warning("⚠️ Rate limit - pausa di 5 minuti...")
            time.sleep(300)
            return None
        else:
            logger.error(f"❌ Errore API eventi: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"❌ Errore connessione eventi: {e}")
        return None

def get_event_odds(event_id):
    """Ottiene quote per un evento"""
    url = f"{BASE_URL}/live-events/{event_id}"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            logger.warning("⚠️ Rate limit quote - attendo...")
            time.sleep(60)
            return None
        else:
            return None
    except Exception as e:
        logger.error(f"❌ Errore quote evento {event_id}: {e}")
        return None

def trova_over_05_ht(odds_data):
    """Trova SOLO quote Over 0.5 HT"""
    if not odds_data or not isinstance(odds_data, dict):
        return None
    
    if 'data' not in odds_data:
        return None
        
    data = odds_data['data']
    if not isinstance(data, dict) or 'mg' not in data:
        return None
    
    markets = data['mg']
    
    for market in markets:
        if isinstance(market, dict):
            market_name = str(market.get('name', '')).lower()
            
            if '1st half goals' in market_name:
                if 'ma' in market:
                    odds = market['ma']
                    
                    for odd in odds:
                        if isinstance(odd, dict):
                            selection = str(odd.get('name', '')).lower()
                            
                            if 'over' in selection:
                                pa_data = odd.get('pa', [])
                                if isinstance(pa_data, list) and pa_data:
                                    price_str = pa_data[0].get('decimal', '')
                                    handicap = pa_data[0].get('HA', '')
                                    fraction = pa_data[0].get('OD', '')
                                    
                                    try:
                                        price = float(price_str)
                                        
                                        # SOLO Over 0.5 HT
                                        if handicap == '0.5':
                                            return {
                                                'quota': price,
                                                'handicap': handicap,
                                                'fraction': fraction
                                            }
                                    except:
                                        continue
    return None

def analizza_evento(event):
    """Analizza un singolo evento"""
    event_id = event.get('id')
    home = event.get('home', 'Team Casa')
    away = event.get('away', 'Team Trasferta')
    live_status = event.get('live', 0)
    score = event.get('score', '0-0')
    
    if not event_id or live_status != 1:
        return None
    
    # Evita duplicati
    evento_key = f"{event_id}_{home}_{away}"
    if evento_key in opportunita_segnalate:
        return None
    
    # Ottieni quote
    odds_data = get_event_odds(event_id)
    if not odds_data:
        return None
    
    # Cerca Over 0.5 HT
    over_info = trova_over_05_ht(odds_data)
    if not over_info:
        return None
    
    quota = over_info['quota']
    
    # Controlla range
    if QUOTA_MINIMA <= quota <= QUOTA_MASSIMA:
        opportunita_segnalate.add(evento_key)
        
        return {
            'event_id': event_id,
            'home': home,
            'away': away,
            'score': score,
            'quota': quota,
            'handicap': over_info['handicap'],
            'fraction': over_info['fraction'],
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
    
    return None

def segnala_opportunita(opp):
    """Segnala un'opportunità"""
    logger.info(f"🎯 OPPORTUNITÀ: {opp['home']} vs {opp['away']} - Over {opp['handicap']} HT: {opp['quota']}")
    
    # Messaggio Telegram
    messaggio = f"""
🚨 <b>OPPORTUNITÀ LIVE!</b> 🚨

⚽ <b>{opp['home']} vs {opp['away']}</b>
📊 Score: <b>{opp['score']}</b>
💰 <b>Over {opp['handicap']} HT: {opp['quota']}</b> ({opp['fraction']})
⏰ Ora: {opp['timestamp']}

🎯 Range: {QUOTA_MINIMA} - {QUOTA_MASSIMA}
🤖 <i>Monitor H24 attivo</i>
"""
    
    invia_messaggio_telegram(messaggio)

def monitor_loop():
    """Loop principale del monitor"""
    logger.info("🚀 MONITOR H24 AVVIATO!")
    logger.info(f"📊 Range quote: {QUOTA_MINIMA} - {QUOTA_MASSIMA}")
    logger.info(f"⏱️ Controllo ogni: {INTERVALLO_CONTROLLO} secondi")
    
    # Messaggio di avvio
    start_msg = f"""
🤖 <b>MONITOR H24 AVVIATO!</b>

📊 Range quote: {QUOTA_MINIMA} - {QUOTA_MASSIMA}
🎯 Target: Over 0.5 HT
⏱️ Controllo ogni: {INTERVALLO_CONTROLLO}s
🔄 Max eventi: {MAX_EVENTI_CONTROLLO}

🚀 <i>Sistema operativo!</i>
"""
    invia_messaggio_telegram(start_msg)
    
    ciclo = 0
    
    while True:
        try:
            ciclo += 1
            timestamp = datetime.now().strftime('%H:%M:%S')
            logger.info(f"🔄 Ciclo {ciclo} - {timestamp}")
            
            # Ottieni eventi live
            live_data = get_live_events()
            if not live_data:
                logger.warning("❌ Nessun dato eventi")
                time.sleep(INTERVALLO_CONTROLLO)
                continue
            
            # Estrai eventi
            if 'data' in live_data and 'events' in live_data['data']:
                events = live_data['data']['events']
                logger.info(f"📋 {len(events)} eventi live - controllo primi {MAX_EVENTI_CONTROLLO}")
                
                eventi_da_controllare = events[:MAX_EVENTI_CONTROLLO]
                opportunita_trovate = 0
                
                for i, event in enumerate(eventi_da_controllare):
                    home = event.get('home', 'N/A')
                    away = event.get('away', 'N/A')
                    logger.info(f"   {i+1}/{len(eventi_da_controllare)}: {home} vs {away}")
                    
                    opportunita = analizza_evento(event)
                    
                    if opportunita:
                        logger.info("   ✅ OPPORTUNITÀ TROVATA!")
                        segnala_opportunita(opportunita)
                        opportunita_trovate += 1
                    
                    # Pausa tra eventi
                    time.sleep(5)
                
                if opportunita_trovate == 0:
                    logger.info(f"📊 Nessuna opportunità nel range {QUOTA_MINIMA}-{QUOTA_MASSIMA}")
                else:
                    logger.info(f"🎯 {opportunita_trovate} opportunità segnalate!")
                
            else:
                logger.warning("❌ Struttura eventi non riconosciuta")
            
            # Pulizia cache ogni 20 cicli
            if ciclo % 20 == 0:
                logger.info(f"🧹 Pulizia cache ({len(opportunita_segnalate)} elementi)")
                opportunita_segnalate.clear()
            
            logger.info(f"⏳ Prossimo controllo tra {INTERVALLO_CONTROLLO} secondi...")
            time.sleep(INTERVALLO_CONTROLLO)
            
        except KeyboardInterrupt:
            logger.info("🛑 Monitor interrotto")
            break
        except Exception as e:
            logger.error(f"❌ Errore nel monitor: {e}")
            time.sleep(INTERVALLO_CONTROLLO)

if __name__ == "__main__":
    # Avvia il monitor
    monitor_loop()
