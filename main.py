import requests
import pandas as pd
import json
import time
from datetime import datetime
import os
import logging
from io import StringIO

# Setup logging per Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurazione da variabili d'ambiente
API_KEY = os.getenv('BET365_API_KEY', 'ef6ca400b4msh27cf7bcbe15ccdbp115debjsn05d47a0aaf0e')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '7912248885:AAFwOdg0rX3weVr6NXzW1adcUorvlRY8LyI')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '6146221712')

# URL del CSV su GitHub (DA CONFIGURARE)
CSV_GITHUB_URL = os.getenv('CSV_GITHUB_URL', 'https://raw.githubusercontent.com/TUO_USERNAME/TUO_REPO/main/matches_today.csv')

# Parametri
PROBABILITA_MINIMA = float(os.getenv('PROBABILITA_MINIMA', '85.0'))
QUOTA_MINIMA_LIVE = float(os.getenv('QUOTA_MINIMA_LIVE', '2.00'))
INTERVALLO_CONTROLLO = int(os.getenv('INTERVALLO_CONTROLLO', '30'))  # 30 secondi invece di 120
INTERVALLO_CSV = int(os.getenv('INTERVALLO_CSV', '3600'))  # Ricarica CSV ogni ora

BASE_URL = 'https://bet365data.p.rapidapi.com'

headers = {
    'x-rapidapi-host': 'bet365data.p.rapidapi.com',
    'x-rapidapi-key': API_KEY
}

# Cache globali
match_target = {}
match_notificati = set()
ultimo_caricamento_csv = 0

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

def carica_csv_da_github():
    """Carica CSV direttamente da GitHub"""
    global match_target, ultimo_caricamento_csv
    
    try:
        logger.info(f"📡 Scaricando CSV da GitHub: {CSV_GITHUB_URL}")
        
        # Scarica CSV da GitHub
        response = requests.get(CSV_GITHUB_URL, timeout=30)
        response.raise_for_status()
        
        # Leggi CSV dal contenuto
        csv_content = StringIO(response.text)
        
        # Leggi CSV con header
        df = pd.read_csv(csv_content)
        logger.info(f"📊 CSV scaricato: {len(df)} match totali")
        
        # Verifica colonne disponibili
        logger.info(f"🔍 Colonne trovate: {list(df.columns)}")
        
        # DEBUG: Mostra prime 3 righe per verifica
        logger.info(f"📊 PRIME 3 RIGHE CSV:")
        for idx, row in df.head(3).iterrows():
            logger.info(f"   Riga {idx}: Home={row.get('Home Team', 'N/A')}, Away={row.get('Away Team', 'N/A')}")
            logger.info(f"   Over05 FHG HT Average: {row.get('Over05 FHG HT Average', 'N/A')}")
        
        # Trova la colonna corretta per Over 0.5 HT
        over_05_ht_col = None
        possibili_colonne = [
            'Over05 FHG HT Average',
            'Over 0.5 FHG HT Average', 
            'over_05_ht_percent',
            'Over05 FHG HT'
        ]
        
        for col in possibili_colonne:
            if col in df.columns:
                over_05_ht_col = col
                break
        
        if not over_05_ht_col:
            logger.error(f"❌ Colonna Over 0.5 HT non trovata! Colonne disponibili: {list(df.columns)}")
            return False
        
        logger.info(f"✅ Usando colonna: {over_05_ht_col}")
        
        # DEBUG: Verifica valori nella colonna selezionata
        logger.info(f"📊 SAMPLE VALORI COLONNA {over_05_ht_col}:")
        sample_values = df[over_05_ht_col].head(10).tolist()
        logger.info(f"   Primi 10 valori: {sample_values}")
        
        # Converti la colonna percentuale in numerico
        df[over_05_ht_col] = pd.to_numeric(df[over_05_ht_col], errors='coerce')
        
        # DEBUG: Verifica dopo conversione numerica
        logger.info(f"📊 DOPO CONVERSIONE NUMERICA:")
        sample_numeric = df[over_05_ht_col].head(10).tolist()
        logger.info(f"   Primi 10 valori numerici: {sample_numeric}")
        
        # DEBUG: Mostra distribuzione valori
        value_counts = df[over_05_ht_col].value_counts().head(10)
        logger.info(f"📊 DISTRIBUZIONE VALORI PIÙ COMUNI:")
        for value, count in value_counts.items():
            logger.info(f"   Valore {value}: {count} match")
        
        # Filtra match con probabilità >= soglia
        logger.info(f"🎯 FILTRO: Cercando match con {over_05_ht_col} >= {PROBABILITA_MINIMA}")
        df_filtrato = df[df[over_05_ht_col] >= PROBABILITA_MINIMA].copy()
        logger.info(f"🎯 Match filtrati (≥{PROBABILITA_MINIMA}%): {len(df_filtrato)}")
        
        # DEBUG: Mostra i match che hanno passato il filtro
        if len(df_filtrato) > 0:
            logger.info(f"📋 MATCH CHE HANNO PASSATO IL FILTRO:")
            for idx, row in df_filtrato.head(5).iterrows():
                logger.info(f"   {row['Home Team']} vs {row['Away Team']}: {row[over_05_ht_col]}%")
        
        # Prepara dictionary per monitoring con DEBUG COMPLETO
        match_dict = {}
        
        for index, row in df_filtrato.iterrows():
            home_team = str(row['Home Team']).strip()
            away_team = str(row['Away Team']).strip()
            probabilita = row[over_05_ht_col]
            data_match = str(row['date_GMT']).strip()
            country = str(row['Country']).strip()
            league = str(row['League']).strip()
            
            # DEBUG: Log dettagliato per ogni match filtrato
            logger.info(f"🔍 MATCH FILTRATO: {home_team} vs {away_team}")
            logger.info(f"   📊 Colonna usata: {over_05_ht_col}")
            logger.info(f"   📈 Valore colonna: {probabilita}")
            logger.info(f"   🗓️ Data: {data_match}")
            logger.info(f"   🌍 Paese: {country}")
            logger.info(f"   🏆 Lega: {league}")
            logger.info(f"   📋 Riga CSV completa: {dict(row)}")
            
            # Crea chiave di ricerca
            home_norm = normalizza_nome_squadra(home_team)
            away_norm = normalizza_nome_squadra(away_team)
            match_key = f"{home_norm}_vs_{away_norm}"
            match_key = f"{home_norm}_vs_{away_norm}"
            
            match_dict[match_key] = {
                'home': home_team,
                'away': away_team,
                'home_norm': home_norm,
                'away_norm': away_norm,
                'probabilita': probabilita,
                'data': data_match,
                'country': country,
                'league': league,
                'notificato': False
            }
        
        match_target = match_dict
        ultimo_caricamento_csv = time.time()
        
        logger.info(f"✅ {len(match_target)} match caricati per monitoring")
        
        # Log top matches
        if match_target:
            logger.info("🎯 TOP MATCH CARICATI:")
            sorted_matches = sorted(match_target.items(), key=lambda x: x[1]['probabilita'], reverse=True)
            
            for i, (key, match) in enumerate(sorted_matches[:5]):
                logger.info(f"   {i+1}. {match['home']} vs {match['away']} ({match['probabilita']}%)")
                logger.info(f"      🌍 {match['country']} | 🏆 {match['league']}")
        
        # Notifica Telegram caricamento
        msg_csv = f"""
📊 <b>CSV AGGIORNATO!</b>

✅ Match totali: {len(df)}
🎯 Match target (≥{PROBABILITA_MINIMA}%): {len(match_target)}
💰 Quota minima: {QUOTA_MINIMA_LIVE}
⏰ Caricato: {datetime.now().strftime('%H:%M:%S')}

🤖 <i>Monitor attivo!</i>
"""
        invia_messaggio_telegram(msg_csv)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Errore caricamento CSV: {e}")
        msg_errore = f"❌ <b>ERRORE CSV!</b>\n\n{str(e)}\n\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        invia_messaggio_telegram(msg_errore)
        return False

def normalizza_nome_squadra(nome):
    """Normalizza il nome della squadra per il matching - VERSIONE RIGOROSA"""
    if not nome:
        return ""
    
    nome = str(nome).strip().lower()
    
    # Rimuovi caratteri speciali e normalizza
    sostituzioni = {
        '.': '', '-': ' ', '_': ' ', '  ': ' ', '\t': ' ',
        'football club': 'fc', 'soccer club': 'sc', 'athletic club': 'ac'
    }
    
    for old, new in sostituzioni.items():
        nome = nome.replace(old, new)
    
    # Rimuovi spazi multipli
    nome = ' '.join(nome.split())
    
    return nome.strip()

def trova_match_in_csv(home_live, away_live):
    """Trova un match live nel CSV caricato - MATCHING RIGOROSO"""
    home_norm = normalizza_nome_squadra(home_live)
    away_norm = normalizza_nome_squadra(away_live)
    
    # Cerca match esatto
    match_key = f"{home_norm}_vs_{away_norm}"
    if match_key in match_target:
        logger.info(f"✅ Match esatto trovato: {home_live} vs {away_live}")
        return match_target[match_key]
    
    # Matching rigoroso - almeno 70% di sovrapposizione
    for key, match_data in match_target.items():
        home_csv_norm = match_data['home_norm']
        away_csv_norm = match_data['away_norm']
        
        # Calcola similarità usando parole chiave
        home_words_live = set(home_norm.split())
        away_words_live = set(away_norm.split())
        home_words_csv = set(home_csv_norm.split())
        away_words_csv = set(away_csv_norm.split())
        
        # Rimuovi parole comuni che causano confusione
        common_words = {'fc', 'sc', 'ac', 'cf', 'cd', 'united', 'city', 'town', 'women', 'u23', 'u20', 'u21', 'reserves', 'ii'}
        
        home_words_live = home_words_live - common_words
        away_words_live = away_words_live - common_words  
        home_words_csv = home_words_csv - common_words
        away_words_csv = away_words_csv - common_words
        
        if not home_words_live or not away_words_live or not home_words_csv or not away_words_csv:
            continue
            
        # Calcola overlap percentage
        home_overlap = len(home_words_live & home_words_csv) / max(len(home_words_live), len(home_words_csv))
        away_overlap = len(away_words_live & away_words_csv) / max(len(away_words_live), len(away_words_csv))
        
        # Richiedi almeno 70% di overlap per entrambe le squadre
        if home_overlap >= 0.7 and away_overlap >= 0.7:
            logger.info(f"✅ Match rigoroso trovato: {home_live} vs {away_live} -> {match_data['home']} vs {match_data['away']}")
            logger.info(f"   Overlap: Casa {home_overlap:.1%}, Trasferta {away_overlap:.1%}")
            return match_data
        elif home_overlap >= 0.4 and away_overlap >= 0.4:
            # Log match sospetti ma non li accetta
            logger.warning(f"⚠️  Match sospetto (overlap basso): {home_live} vs {away_live} -> {match_data['home']} vs {match_data['away']}")
            logger.warning(f"   Overlap: Casa {home_overlap:.1%}, Trasferta {away_overlap:.1%} - SCARTATO")
    
    return None

def get_live_events():
    """Ottiene eventi live"""
    url = f"{BASE_URL}/live-events?sport=soccer"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            logger.warning("⚠️ Rate limit - pausa...")
            time.sleep(180)
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
            logger.warning("⚠️ Rate limit quote...")
            time.sleep(60)
            return None
        else:
            return None
    except Exception as e:
        logger.error(f"❌ Errore quote evento {event_id}: {e}")
        return None

def trova_over_05_ht(odds_data):
    """Trova quote Over 0.5 HT"""
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
                                        
                                        if handicap == '0.5':
                                            return {
                                                'quota': price,
                                                'handicap': handicap,
                                                'fraction': fraction
                                            }
                                    except:
                                        continue
    return None

def monitor_loop():
    """Loop principale del monitor"""
    global ultimo_caricamento_csv
    
    logger.info("🚀 MONITOR CSV H24 RENDER AVVIATO!")
    
    # Carica CSV iniziale
    if not carica_csv_da_github():
        logger.error("❌ Impossibile caricare CSV iniziale!")
        return
    
    # Messaggio di avvio
    start_msg = f"""
🤖 <b>MONITOR CSV H24 AVVIATO!</b>

📊 Match target: {len(match_target)}
🎯 Probabilità min: {PROBABILITA_MINIMA}%
💰 Quota min live: {QUOTA_MINIMA_LIVE}
⏱️ Controllo ogni: {INTERVALLO_CONTROLLO}s
📡 CSV da: GitHub

🚀 <i>Sistema H24 operativo su Render!</i>
"""
    invia_messaggio_telegram(start_msg)
    
    ciclo = 0
    
    while True:
        try:
            ciclo += 1
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            # Ricarica CSV ogni ora
            if time.time() - ultimo_caricamento_csv > INTERVALLO_CSV:
                logger.info("🔄 Ricaricamento CSV programmato...")
                carica_csv_da_github()
            
            logger.info(f"🔄 Ciclo {ciclo} - {timestamp} | Target: {len(match_target)} match")
            
            # Ottieni eventi live
            live_data = get_live_events()
            if not live_data:
                time.sleep(INTERVALLO_CONTROLLO)
                continue
            
            # Controlla eventi
            if 'data' in live_data and 'events' in live_data['data']:
                events = live_data['data']['events']
                logger.info(f"📋 {len(events)} eventi live totali")
                
                match_csv_live = 0
                opportunita_trovate = 0
                
                for event in events:
                    home_live = event.get('home', '')
                    away_live = event.get('away', '')
                    event_id = event.get('id', '')
                    live_status = event.get('live', 0)
                    score = event.get('score', '0-0')
                    
                    if live_status != 1 or not event_id:
                        continue
                    
                    # Controlla se match è nel CSV
                    match_csv = trova_match_in_csv(home_live, away_live)
                    
                    if match_csv:
                        match_csv_live += 1
                        match_key = f"{event_id}_{home_live}_{away_live}"
                        
                        logger.info(f"🎯 CSV match live: {home_live} vs {away_live} ({match_csv['probabilita']}%)")
                        
                        if match_key in match_notificati:
                            continue
                        
                        # Ottieni quote
                        odds_data = get_event_odds(event_id)
                        if odds_data:
                            over_info = trova_over_05_ht(odds_data)
                            
                            if over_info and over_info['quota'] >= QUOTA_MINIMA_LIVE:
                                match_notificati.add(match_key)
                                opportunita_trovate += 1
                                
                                # Notifica
                                messaggio = f"""
🚨 <b>MATCH CSV LIVE!</b> 🚨

⚽ <b>{home_live} vs {away_live}</b>
🌍 {match_csv['country']} | {match_csv['league']}
📊 Score: <b>{score}</b>
💰 <b>Over 0.5 HT: {over_info['quota']}</b> ({over_info['fraction']})
📈 Probabilità CSV: <b>{match_csv['probabilita']}%</b>

🎯 Target: ≥{QUOTA_MINIMA_LIVE}
📅 {match_csv['data']}
🤖 Render H24
"""
                                
                                invia_messaggio_telegram(messaggio)
                                logger.info(f"✅ OPPORTUNITÀ: {home_live} vs {away_live} - {over_info['quota']}")
                        
                        time.sleep(5)  # Pausa tra controlli quote
                
                logger.info(f"📊 Match CSV live: {match_csv_live} | Opportunità: {opportunita_trovate}")
                
            # Pulizia cache
            if ciclo % 100 == 0:
                logger.info("🧹 Pulizia cache...")
                match_notificati.clear()
            
            time.sleep(INTERVALLO_CONTROLLO)
            
        except Exception as e:
            logger.error(f"❌ Errore nel monitor: {e}")
            time.sleep(INTERVALLO_CONTROLLO)

if __name__ == "__main__":
    monitor_loop()
