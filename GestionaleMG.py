import streamlit as st
import httpx
from datetime import date
import random

# ==========================================
# [01_CONFIGURAZIONE & CSS]
# ==========================================
st.set_page_config(page_title="MasterGroup Cloud 🏗️", layout="wide")

st.markdown("""
    <style>
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    #stDecoration {display:none;}
    [data-testid="stHeader"] {background-color: rgba(0,0,0,0); height: 3rem;}
    </style>
    """, unsafe_allow_html=True)

try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    URL = "https://clauyljovenkcqemswfk.supabase.co"
    KEY = "sb_publishable_WetwA7q8dmctM2a-VDBfTg_M46vnFi0"

headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

ATTIVITA_STANDARD = ["Sopralluogo", "Grafici", "CILA/SCIA", "DOCFA", "APE", "DL", "Contabilità", "Altro..."]
CITAZIONI = [{"t": "L'architettura è un cristallo.", "a": "Gio Ponti"}, {"t": "Dio è nei dettagli.", "a": "Mies van der Rohe"}]

# ==========================================
# [02_MOTORE_CLOUD]
# ==========================================
@st.cache_data(ttl=60) # Ottimizziamo la lettura per evitare sovraccarichi
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

def aggiorna_db(tabella, id_riga, payload):
    try:
        with httpx.Client() as client:
            return client.patch(f"{URL}/rest/v1/{tabella}?id=eq.{id_riga}", headers=headers, json=payload)
    except: return None

# ==========================================
# [03_LOGICA ACCESSO]
# ==========================================
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🏗️ MasterGroup in Cloud")
    with st.form("login_form"):
        e = st.text_input("Email Aziendale", key="login_email")
        p = st.text_input("Password", type="password", key="login_pass")
        if st.form_submit_button("Entra"):
            utenti = leggi_tabella("utenti")
            u = next((x for x in utenti if x.get('email')==e and x.get('password')==p), None)
            if u: 
                st.session_state.autenticato = True
                st.session_state.u = u
                st.rerun()
            else:
                st.error("Credenziali errate.")
    st.stop() # Blocca tutto il resto se non loggato

# --- SESSIONE ATTIVA ---
u_log = st.session_state.u
ruolo = u_log['ruolo']
nome_log = u_log['nome']

# ==========================================
# [04_SIDEBAR & NAVIGAZIONE]
# ==========================================
st.sidebar.title("🏗️ MasterGroup")
st.sidebar.info(f"👤 **{nome_log}**\n🔑 **{ruolo}**")

# Costruiamo il menu in base al ruolo
menu = ["🏠 Dashboard", "📋 Gestione Task"]
if ruolo in ["Admin", "PM"]:
    menu.extend(["📊 Analisi Commesse", "🎯 Assegnazione"])
if ruolo == "Admin":
    menu.append("⚖️ Approvazioni")

# Usiamo una KEY univoca per evitare il DuplicateElementId
scelta = st.sidebar.radio("Navigazione", menu, key="main_nav_radio")

if st.sidebar.button("Logout", key="logout_btn"):
    st.session_state.autenticato = False
    st.rerun()

# ==========================================
# [05_MODULI]
# ==========================================
if scelta == "🏠 Dashboard":
    st.header(f"Benvenuto, {nome_log}")
    cit = random.choice(CITAZIONI)
    st.info(f"💡 *\"{cit['t']}\"* — {cit['a']}")
    
    t_db = leggi_tabella("task")
    miei_t = [t for t in t_db if t['assegnato_a'] == nome_log and t['stato'] != 'Completato']
    
    c1, c2 = st.columns(2)
    c1.metric("Task da completare", len(miei_t))
    if ruolo in ["Admin", "PM"]:
        bloccati = [t for t in t_db if t.get('stato') == 'Bloccato']
        c2.metric("🆘 Criticità Studio", len(bloccati))

elif scelta == "📋 Gestione Task":
    st.header("Lista Attività")
    t_db = leggi_tabella("task")
    utenti_list = leggi_tabella("utenti")
    
    col_f1, col_f2 = st.columns(2)
    filtro_tecnico = nome_log
    if ruolo in ["Admin", "PM"]:
        nomi_op = ["Tutti"] + [ut['nome'] for ut in utenti_list]
        filtro_tecnico = col_f1.selectbox("Tecnico", nomi_op, key="filter_tech")
    f_prio = col_f2.selectbox("Priorità", ["Tutte", "Alta", "Media", "Bassa"], key="filter_prio")

    tasks = [t for t in t_db if t['stato'] != 'Completato']
    if filtro_tecnico != "Tutti": tasks = [t for t in tasks if t['assegnato_a'] == filtro_tecnico]
    if f_prio != "Tutte": tasks = [t for t in tasks if t['priorita'] == f_prio]

    for t in tasks:
        with st.expander(f"📌 {t.get('commessa_ref')} - {t.get('descrizione')}"):
            nuovo_st = st.selectbox("Stato", ["In corso", "Completato", "Bloccato"], key=f"st_{t['id']}")
            if st.button("Aggiorna", key=f"btn_{t['id']}"):
                aggiorna_db("task", t['id'], {"stato": nuovo_st})
                st.rerun()

elif scelta == "📊 Analisi Commesse":
    st.header("Avanzamento Progetti")
    c_db = leggi_tabella("commesse")
    t_db = leggi_tabella("task")
    for c in c_db:
        t_c = [t for t in t_db if t.get('commessa_ref') == c['codice']]
        chiusi = len([t for t in t_c if t['stato'] == 'Completato'])
        perc = (chiusi / len(t_c) * 100) if t_c else 0
        st.write(f"📂 **{c['codice']}** - {c['cliente']}")
        st.progress(perc / 100)

elif scelta == "🎯 Assegnazione":
    tab1, tab2 = st.tabs(["🏗️ Commessa", "📝 Task"])
    with tab1:
        with st.form("form_c", clear_on_submit=True):
            cod = st.text_input("Codice")
            cli = st.text_input("Cliente")
            if st.form_submit_button("Crea Commessa"):
                scrivi_dati("commesse", {"codice": cod, "cliente": cli, "scadenza": str(date.today())})
                st.success("Creata!")
    with tab2:
        with st.form("form_t", clear_on_submit=True):
            c_list = leggi_tabella("commesse")
            sel_c = st.selectbox("Progetto", [c['codice'] for c in c_list])
            chi = st.selectbox("Tecnico", [u['nome'] for u in leggi_tabella("utenti")])
            if st.form_submit_button("Assegna"):
                scrivi_dati("task", {"commessa_ref": sel_c, "assegnato_a": chi, "stato": "In corso", "scadenza": str(date.today())})
                st.success("Inviato!")

elif scelta == "⚖️ Approvazioni":
    st.write("Modulo approvazioni attivo.")
