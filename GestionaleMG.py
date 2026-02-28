import streamlit as st
import httpx
from datetime import date
import random

# ==========================================
# [01_CONFIGURAZIONE SICURA]
# ==========================================
st.set_page_config(page_title="MasterGroup Cloud 🏗️", layout="wide")

try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    URL = "https://clauyljovenkcqemswfk.supabase.co"
    KEY = "sb_publishable_WetwA7q8dmctM2a-VDBfTg_M46vnFi0"

headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

# ==========================================
# [02_FUNZIONI CORE]
# ==========================================
def leggi_tabella(tabella):
    try:
        with httpx.Client() as client:
            res = client.get(f"{URL}/rest/v1/{tabella}?select=*", headers=headers)
            return res.json()
    except: return []

def scrivi_dati(tabella, dati_json):
    try:
        with httpx.Client() as client:
            return client.post(f"{URL}/rest/v1/{tabella}", headers=headers, json=dati_json)
    except: return None

# ==========================================
# [03_LOGICA DI AUTENTICAZIONE]
# ==========================================
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False
    st.session_state.utente = None

def login():
    st.title("🏗️ MasterGroup in Cloud")
    st.subheader("Accesso Area Riservata")
    
    with st.form("login_form"):
        email_inserita = st.text_input("Email Aziendale")
        pass_inserita = st.text_input("Password", type="password")
        submit = st.form_submit_button("Accedi")
        
        if submit:
            utenti = leggi_tabella("utenti")
            # Cerchiamo l'utente che corrisponde a email e password
            user_match = next((u for u in utenti if u.get('email') == email_inserita and u.get('password') == pass_inserita), None)
            
            if user_match:
                st.session_state.autenticato = True
                st.session_state.utente = user_match
                st.success(f"Benvenuto {user_match['nome']}!")
                st.rerun()
            else:
                st.error("Credenziali errate. Riprova o contatta l'Admin.")

# ==========================================
# [04_APP PRINCIPALE]
# ==========================================
if not st.session_state.autenticato:
    login()
else:
    u = st.session_state.utente
    nome_utente = u['nome']
    ruolo = u['ruolo']
    
    st.sidebar.title("🏗️ MasterGroup")
    st.sidebar.info(f"Utente: **{nome_utente}**\n\nRuolo: **{ruolo}**")
    
    # Menu dinamico in base al ruolo
    opzioni = ["🏠 Dashboard", "📋 I Miei Task"]
    if ruolo in ["Admin", "PM"]:
        opzioni.extend(["🏗️ Nuova Commessa", "🎯 Assegna Lavoro"])
    
    scelta = st.sidebar.radio("Navigazione", opzioni)
    
    if st.sidebar.button("Esci (Logout)"):
        st.session_state.autenticato = False
        st.rerun()

    # --- DASHBOARD ---
    if scelta == "🏠 Dashboard":
        st.header(f"Benvenuto, {nome_utente}")
        # Qui aggiungeremo il meteo nel prossimo step!
        st.write("Seleziona un'attività dal menu a sinistra per iniziare.")
        
        # Statistiche veloci
        t_db = leggi_tabella("task")
        c_db = leggi_tabella("commesse")
        
        col1, col2 = st.columns(2)
        if ruolo == "Admin":
            col1.metric("Commesse Totali", len(c_db))
            col2.metric("Task in corso", len([t for t in t_db if t['stato'] != 'Completato']))
        else:
            miei_t = [t for t in t_db if t['assegnato_a'] == nome_utente]
            col1.metric("I Miei Task", len(miei_t))
            col2.metric("Completati", len([t for t in miei_t if t['stato'] == 'Completato']))

    # --- MODULO TASK (ORDINATO PER PRIORITÀ) ---
    elif scelta == "📋 I Miei Task":
        st.header("Le tue attività")
        t_db = leggi_tabella("task")
        # Filtriamo solo i task dell'utente loggato
        miei_task = [t for t in t_db if t['assegnato_a'] == nome_utente and t['stato'] != 'Completato']
        
        # Ordinamento: Alta -> Media -> Bassa
        ordine_prio = {"Alta": 0, "Media": 1, "Bassa": 2}
        miei_task.sort(key=lambda x: ordine_prio.get(x['priorita'], 3))
        
        if not miei_task:
            st.success("Ottimo lavoro! Non hai task pendenti.")
        else:
            for t in miei_task:
                prio_col = "🔴" if t['priorita'] == "Alta" else "🟡" if t['priorita'] == "Media" else "🟢"
                with st.expander(f"{prio_col} {t['commessa_ref']} - {t['descrizione']}"):
                    st.write(f"Scadenza: {t['scadenza']}")
                    # Logica aggiornamento stato... (omessa per brevità ma presente nel tuo file locale)

    # --- NUOVA COMMESSA & ASSEGNAZIONE (Solo Admin/PM) ---
    # ... (inserire qui i moduli 06 e 07 del file precedente)
