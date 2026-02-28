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

ATTIVITA_STANDARD = [
    "Sopralluogo e Rilievo Strumentale", "Redazione Elaborati Grafici",
    "Pratica Edilizia (CILA/SCIA/PdC)", "Pratica Catastale (DOCFA)",
    "APE (Prestazione Energetica)", "Direzione Lavori", "Contabilità Lavori", "Altro..."
]

CITAZIONI = [
    {"testo": "L'architettura è un cristallo.", "autore": "Gio Ponti"},
    {"testo": "Dio è nei dettagli.", "autore": "Mies van der Rohe"},
    {"testo": "L'architettura deve commuovere.", "autore": "Le Corbusier"},
    {"testo": "Usate la matita come se fosse una spada.", "autore": "Franco Albini"}
]

# ==========================================
# [02_MOTORE_CLOUD]
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

def aggiorna_stato_db(id_task, nuovo_stato, nota_blocco=""):
    try:
        payload = {"stato": nuovo_stato, "motivo_blocco": nota_blocco}
        with httpx.Client() as client:
            res = client.patch(f"{URL}/rest/v1/task?id=eq.{id_task}", headers=headers, json=payload)
            return res.status_code
    except: return 500

# ==========================================
# [03_LOGICA DI AUTENTICAZIONE]
# ==========================================
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False
    st.session_state.utente = None

if not st.session_state.autenticato:
    st.title("🏗️ MasterGroup in Cloud")
    with st.form("login_form"):
        email = st.text_input("Email Aziendale")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Accedi"):
            utenti = leggi_tabella("utenti")
            user = next((u for u in utenti if u.get('email') == email and u.get('password') == pwd), None)
            if user:
                st.session_state.autenticato = True
                st.session_state.utente = user
                st.rerun()
            else:
                st.error("Credenziali errate.")
    st.stop()

# --- DA QUI IN POI L'UTENTE È LOGGATO ---
u = st.session_state.utente
nome_u = u['nome']
ruolo_u = u['ruolo']

st.sidebar.title("🏗️ MasterGroup")
st.sidebar.write(f"Utente: **{nome_u}**")
st.sidebar.write(f"Ruolo: **{ruolo_u}**")

menu = ["🏠 Dashboard", "📋 I Miei Task"]
if ruolo_u in ["Admin", "PM"]:
    menu.extend(["🏗️ Nuova Commessa", "🎯 Assegna Lavoro"])

scelta = st.sidebar.radio("Navigazione", menu)

if st.sidebar.button("Logout"):
    st.session_state.autenticato = False
    st.rerun()

# ==========================================
# [05_DASHBOARD]
# ==========================================
if scelta == "🏠 Dashboard":
    st.header(f"Benvenuto nel Cloud, {nome_u}")
    cit = random.choice(CITAZIONI)
    st.info(f"💡 *\"{cit['testo']}\"* — **{cit['autore']}**")
    
    c_db = leggi_tabella("commesse")
    t_db = leggi_tabella("task")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Progetti Studio", len(c_db))
    col2.metric("Task Totali", len(t_db))
    col3.metric("I Miei Task", len([t for t in t_db if t['assegnato_a'] == nome_u and t['stato'] != 'Completato']))

# ==========================================
# [06_NUOVA_COMMESSA]
# ==========================================
elif scelta == "🏗️ Nuova Commessa":
    st.header("Registrazione Nuova Commessa")
    with st.form("f_c", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cod = c1.text_input("Codice (es. 2024_10)")
        cli = c1.text_input("Cliente")
        bud = c2.number_input("Budget (€)", min_value=0.0)
        scad = c2.date_input("Scadenza Contrattuale")
        if st.form_submit_button("Crea Progetto"):
            scrivi_dati("commesse", {"codice": cod, "cliente": cli, "budget": bud, "scadenza": str(scad)})
            st.success("Commessa creata!")

# ==========================================
# [07_ASSEGNA_LAVORO]
# ==========================================
elif scelta == "🎯 Assegna Lavoro":
    st.header("Distribuzione Task")
    comm_db = leggi_tabella("commesse")
    codici = [c['codice'] for c in comm_db] if comm_db else ["Nessuna"]
    utenti_db = leggi_tabella("utenti")
    nomi_u = [ut['nome'] for ut in utenti_db]

    with st.form("f_t"):
        sel_c = st.selectbox("Progetto", codici)
        att = st.selectbox("Attività", ATTIVITA_STANDARD)
        chi = st.selectbox("Tecnico", nomi_u)
        prio = st.select_slider("Priorità", options=["Bassa", "Media", "Alta"])
        scad_t = st.date_input("Scadenza")
        if st.form_submit_button("Invia Task"):
            scrivi_dati("task", {
                "commessa_ref": sel_c, "descrizione": att, "assegnato_a": chi,
                "priorita": prio, "scadenza": str(scad_t), "stato": "In corso"
            })
            st.success("Task assegnato!")

# ==========================================
# [08_SCRIVANIA_OPERATORE]
# ==========================================
elif scelta == "📋 I Miei Task":
    st.header(f"Attività di {nome_u}")
    t_db = leggi_tabella("task")
    miei = [t for t in t_db if t['assegnato_a'] == nome_u and t['stato'] != 'Completato']
    
    if not miei:
        st.success("Nessun task pendente!")
    else:
        for t in miei:
            with st.expander(f"📁 {t['commessa_ref']} | {t['descrizione']} ({t['priorita']})"):
                st.write(f"Scadenza: {t['scadenza']}")
                nuovo_st = st.selectbox("Aggiorna Stato", ["In corso", "Completato", "Bloccato"], key=f"s_{t['id']}")
                nota = st.text_area("Note blocco", value=t.get('motivo_blocco',''), key=f"n_{t['id']}") if nuovo_st == "Bloccato" else ""
                if st.button("Salva", key=f"b_{t['id']}"):
                    if aggiorna_stato_db(t['id'], nuovo_st, nota) in [200, 204]:
                        st.rerun()
