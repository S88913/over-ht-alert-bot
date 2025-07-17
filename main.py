import os
import pandas as pd
import requests
import time
import logging
from datetime import datetime, timedelta
from io import StringIO

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurazione Telegram
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '7912248885:AAFwOdg0rX3weVr6NXzW1adcUorvlRY8LyI')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '6146221712')

# Parametri sistema
PROBABILITA_MINIMA = float(os.getenv('PROBABILITA_MINIMA', '85.0'))
CSV_GITHUB_URL = os.getenv('CSV_GITHUB_URL', 'https://raw.githubusercontent.com/S88913/over-ht-monitor/main/matches_today.csv')
INTERVALLO_CONTROLLO = int(os.getenv('INTERVALLO_CONTROLLO', '300'))  # 5 minuti
INTERVALLO_CSV = int(os.getenv('INTERVALLO_CSV', '7200'))  # 2 ore

# Storage globale
match_target = {}
match_notificati = set()
ultimo_caricamento_csv = 0

def invia_messaggio_telegram(messaggio):
    """Invia messaggio Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': messaggio,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("✅ Messaggio Telegram inviato")
            return True
        else:
            logger.error(f"❌ Errore Telegram: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Errore invio Telegram: {e}")
        return False

def normalizza_nome_squadra(nome):
    """Normalizza il nome della squadra per il matching"""
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
    
    nome = ' '.join(nome.split())
    return nome.strip()

def carica_csv_da_github():
    """Carica e processa il CSV da GitHub"""
    global match_target, ultimo_caricamento_csv
    
    try:
        logger.info(f"📥 Scaricando CSV da GitHub...")
        response = requests.get(CSV_GITHUB_URL, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"❌ Errore download CSV: {response.status_code}")
            return False
        
        csv_content = StringIO(response.text)
        
        # Leggi CSV con header
        df = pd.read_csv(csv_content)
        logger.info(f"📊 CSV scaricato: {len(df)} match totali")
        
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
            logger.error(f"❌ Colonna Over 0.5 HT non trovata!")
            return False
        
        logger.info(f"✅ Usando colonna: {over_05_ht_col}")
        
        # Converti la colonna percentuale in numerico
        df[over_05_ht_col] = pd.to_numeric(df[over_05_ht_col], errors='coerce')
        
        # Filtra match con probabilità >= soglia E ESCLUDI ESPORTS
        df_filtrato = df[
            (df[over_05_ht_col] >= PROBABILITA_MINIMA) & 
            (df['Country'] != 'Esports')  # ESCLUDI MATCH ESPORTS
        ].copy()
        logger.info(f"🎯 Match filtrati (≥{PROBABILITA_MINIMA}% + NO Esports): {len(df_filtrato)}")
        
        # Prepara dictionary per monitoring
        match_dict = {}
        
        for index, row in df_filtrato.iterrows():
            home_team = str(row['Home Team']).strip()
            away_team = str(row['Away Team']).strip()
            probabilita = row[over_05_ht_col]
            data_match = str(row['date_GMT']).strip()
            country = str(row['Country']).strip()
            league = str(row['League']).strip()
            
            # Crea chiave di ricerca
            home_norm = normalizza_nome_squadra(home_team)
            away_norm = normalizza_nome_squadra(away_team)
            match_key = f"{home_norm}_vs_{away_norm}"
            
            match_dict[match_key] = {
                'home': home_team,
                'away': away_team,
                'home_norm': home_norm,
                'away_norm': away_norm,
                'probabilita': probabilita,
                'data': data_match,
                'country': country,
                'league': league
            }
        
        match_target = match_dict
        ultimo_caricamento_csv = time.time()
        
        # Notifica Telegram caricamento SOLO AL PRIMO AVVIO
        if len(match_target) == 0:
            logger.warning("⚠️ Nessun match target trovato")
        else:
            logger.info(f"✅ {len(match_target)} match target caricati")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Errore caricamento CSV: {e}")
        return False

def trova_match_in_csv(home_live, away_live):
    """Trova un match live nel CSV caricato"""
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
            return match_data
    
    return None

def calcola_minuti_da_inizio(ora_inizio_str):
    """Calcola i minuti passati dall'inizio del match"""
    try:
        # Formato esempio: "Jul 16 2025 - 10:00am" o "Jul 16 2025 - 11:30pm"
        logger.info(f"🕐 Parsing data: {ora_inizio_str}")
        
        # Parse con formato corretto
        ora_inizio = datetime.strptime(ora_inizio_str.strip(), "%b %d %Y - %I:%M%p")
        ora_attuale = datetime.now()
        
        logger.info(f"🕐 Match iniziato: {ora_inizio}")
        logger.info(f"🕐 Ora attuale: {ora_attuale}")
        
        # Calcola differenza in minuti
        diff = ora_attuale - ora_inizio
        minuti = int(diff.total_seconds() / 60)
        
        logger.info(f"🕐 Minuti dall'inizio: {minuti}")
        
        # Se il match non è ancora iniziato, ritorna valore negativo
        if minuti < 0:
            logger.info(f"⏰ Match non ancora iniziato (inizia tra {abs(minuti)} minuti)")
            return minuti
            
        return minuti
    except Exception as e:
        logger.error(f"❌ Errore parsing data '{ora_inizio_str}': {e}")
        return 0

def monitor_matches():
    """Monitor principale - versione semplificata"""
    logger.info("🤖 MONITOR SEMPLIFICATO AVVIATO!")
    
    # Carica CSV iniziale
    if not carica_csv_da_github():
        logger.error("❌ Impossibile caricare CSV iniziale!")
        return
    
    # Messaggio di avvio UNICO
    start_msg = f"""
🤖 <b>MONITOR OVER 0.5 HT SEMPLIFICATO!</b>

📊 Match target: {len(match_target)}
🎯 Soglia: ≥{PROBABILITA_MINIMA}%
⏱️ Notifica: dopo 20 minuti dall'inizio
💰 Controllo manuale: su Bet365

🔕 <i>Solo notifiche intelligenti - zero costi API!</i>
"""
    invia_messaggio_telegram(start_msg)
    
    while True:
        try:
            logger.info(f"🔄 Ciclo controllo - {datetime.now().strftime('%H:%M:%S')}")
            
            # Ricarica CSV ogni 2 ore
            if time.time() - ultimo_caricamento_csv > INTERVALLO_CSV:
                logger.info("🔄 Ricaricamento CSV...")
                carica_csv_da_github()
            
            # Controlla ogni match target per timing
            notifiche_inviate_questo_ciclo = 0
            
            for match_key, match_data in match_target.items():
                data_match = match_data['data']
                home = match_data['home']
                away = match_data['away']
                probabilita = match_data['probabilita']
                country = match_data['country']
                league = match_data['league']
                
                # Calcola minuti dall'inizio
                minuti_passati = calcola_minuti_da_inizio(data_match)
                
                logger.info(f"⚽ {home} vs {away}: {minuti_passati}' dall'inizio")
                
                # NOTIFICA ESATTAMENTE TRA 18-22 MINUTI (target 20')
                if 18 <= minuti_passati <= 22:
                    if match_key not in match_notificati:
                        match_notificati.add(match_key)
                        notifiche_inviate_questo_ciclo += 1
                        
                        # Invia notifica con tutti i dettagli
                        messaggio = f"""
🚨 <b>SEGNALE OVER 0.5 HT!</b> 🚨

⚽ <b>{home} vs {away}</b>
🌍 {country} | {league}
📈 <b>Probabilità CSV: {probabilita}%</b>
⏰ <b>Minuti giocati: ~{minuti_passati}'</b>

💡 <b>AZIONE:</b>
1️⃣ Controlla su Bet365 se ancora 0-0
2️⃣ Se 0-0 → Scommetti "Over 0.5 HT" 
3️⃣ Se già gol → Passa al prossimo

🎯 <i>Timing perfetto per entrare!</i>
📅 Match iniziato: {data_match}
🕐 Notifica alle: {datetime.now().strftime('%H:%M')}
"""
                        
                        if invia_messaggio_telegram(messaggio):
                            logger.info(f"🚨 SEGNALE INVIATO: {home} vs {away} ({probabilita}%) dopo {minuti_passati}' minuti")
                        else:
                            logger.error(f"❌ Errore invio notifica per {home} vs {away}")
                
                # Debug: mostra status di tutti i match
                elif minuti_passati < 0:
                    logger.info(f"⏳ {home} vs {away}: Inizia tra {abs(minuti_passati)} minuti")
                elif minuti_passati > 45:
                    logger.info(f"⏹️ {home} vs {away}: Match terminato ({minuti_passati} minuti fa)")
                else:
                    logger.info(f"👀 {home} vs {away}: {minuti_passati}' giocati (aspetto 20')")
            
            if notifiche_inviate_questo_ciclo > 0:
                logger.info(f"📱 Inviate {notifiche_inviate_questo_ciclo} notifiche in questo ciclo")
            
            logger.info(f"✅ Controllo completato - prossimo in {INTERVALLO_CONTROLLO//60} minuti")
            time.sleep(INTERVALLO_CONTROLLO)
            
        except Exception as e:
            logger.error(f"❌ Errore nel loop principale: {e}")
            time.sleep(60)  # Pausa di 1 minuto in caso di errore

if __name__ == "__main__":
    monitor_matches()
