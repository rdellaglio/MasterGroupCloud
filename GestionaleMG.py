import streamlit as st
import httpx
from datetime import date
import random

# ==========================================
# [01_CONFIGURAZIONE & SECRETS]
# ==========================================
st.set_page_config(page_title="MasterGroup Cloud 🏗️", layout="wide")

try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    URL = "https://clauyljovenkcqemswfk.supabase.co"
    KEY = "sb_publishable_WetwA7q8dmctM2a-VDBfTg_M46vnFi0"

headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

CITAZIONI = [
    {"t": "L'architettura è un cristallo.", "a": "Gio Ponti"},
    {"t": "Dio è nei dettagli.", "a": "Mies van der Rohe"},
    {"t": "La forma segue la funzione.", "a": "Louis Sullivan"},
    {"t": "L'architettura deve commuovere.", "a": "Le Corbusier"}
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

def aggiorna_db(tabella, id_riga, payload):
    try:
        with httpx.Client() as client:
            return client.patch(f"{URL}/rest/v1/{tabella}?id=eq.{id_riga}", headers=headers, json=payload)
    except: return None

def scrivi_dati(tabella, dati_json):
    try:
        with httpx.Client() as client:
            return client.post(f"{URL}/rest/v1/{tabella}", headers=headers, json=dati_json)
    except: return None

# ==========================================
# [03_LOGICA ACCESSO]
# ==========================================
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🏗️ MasterGroup in Cloud")
    with st.form("login"):
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Entra"):
            utenti = leggi_tabella("utenti")
            u = next((x for x in utenti if x.get('email')==e and x.get('password')==p), None)
            if u: 
                st.session_state.autenticato = True
                st.session_state.u = u
                st.rerun()
    st.stop()

u_log = st.session_state.u
ruolo = u_log['ruolo']
nome_log = u_log['nome']

# ==========================================
# [04_NAVIGAZIONE SIDEBAR]
# ==========================================
st.sidebar.title("🏗️ MasterGroup")
st.sidebar.info(f"👤 **{nome_log}**\n\n🔑 Ruolo: **{ruolo}**")

menu = ["🏠 Dashboard", "📋 Gestione Task"]
if ruolo in ["Admin", "PM"]:
    menu.extend(["🏗️ Commesse", "🎯 Assegnazione"])
if ruolo == "Admin":
    menu.append("⚖️ Approvazioni")

scelta = st.sidebar.radio("Vai a:", menu)

# ==========================================
# [05_DASHBOARD MOTIVAZIONALE]
# ==========================================
if scelta == "🏠 Dashboard":
    st.header(f"Benvenuto, {nome_log}")
    
    # IA & Citazione
    cit = random.choice(CITAZIONI)
    st.info(f"☀️ **Meteo Bari:** Sereno (22°C) - Ottimo per il cantiere!\n\n💡 *\"{cit['t']}\"* — {cit['a']}")
    
    t_db = leggi_tabella("task")
    miei_t = [t for t in t_db if t['assegnato_a'] == nome_log and t['stato'] != 'Completato']
    
    col1, col2 = st.columns(2)
    col1.metric("Task da completare", len(miei_t))
    
    # Solo Admin vede il Budget Totale
    if ruolo == "Admin":
        c_db = leggi_tabella("commesse")
        tot_budget = sum(float(c.get('budget', 0)) for c in c_db)
        col2.metric("Budget Totale Gestito", f"€ {tot_budget:,.2f}")

# ==========================================
# [06_GESTIONE TASK (FILTRATI E ORDINATI)]
# ==========================================
elif scelta == "📋 Gestione Task":
    st.header("Le tue Attività")
    t_db = leggi_tabella("task")
    
    # Logica di visualizzazione basata sul RUOLO
    if ruolo == "Admin":
        mostra_task = t_db
    elif ruolo == "PM":
        # Il PM vede i suoi e quelli delle sue commesse (placeholder logica)
        mostra_task = [t for t in t_db if t['assegnato_a'] == nome_log or ruolo == "PM"] 
    else:
        mostra_task = [t for t in t_db if t['assegnato_a'] == nome_log]

    # Ordinamento per Priorità (Alta > Media > Bassa)
    p_map = {"Alta": 0, "Media": 1, "Bassa": 2}
    mostra_task.sort(key=lambda x: (p_map.get(x.get('priorita','Bassa'), 3), x.get('scadenza','')))

    for t in mostra_task:
        color = "🔴" if t.get('priorita')=="Alta" else "🟡" if t.get('priorita')=="Media" else "🟢"
        with st.expander(f"{color} [{t.get('scadenza')}] {t.get('commessa_ref')} - {t.get('descrizione')}"):
            st.write(f"Assegnato a: {t.get('assegnato_a')}")
            
            # Permessi di modifica
            posso_modificare = (ruolo == "Admin") or (ruolo == "PM" and t.get('assegnato_a') == nome_log)
            
            if posso_modificare:
                nuova_prio = st.selectbox("Cambia Priorità", ["Bassa", "Media", "Alta"], index=["Bassa", "Media", "Alta"].index(t.get('priorita','Bassa')), key=f"p_{t['id']}")
                nuova_scad = st.date_input("Cambia Scadenza", value=date.fromisoformat(t['scadenza']) if t.get('scadenza') else date.today(), key=f"d_{t['id']}")
                if st.button("Salva Modifiche", key=f"b_{t['id']}"):
                    # Se PM cambia priorità, richiede approvazione (approvato_admin = False)
                    appr = True if ruolo == "Admin" else False
                    aggiorna_db("task", t['id'], {"priorita": nuova_prio, "scadenza": str(nuova_scad), "approvato_admin": appr})
                    st.success("Richiesta inviata!" if not appr else "Aggiornato!")
                    st.rerun()

# ==========================================
# [07_COMMESSE (PRIVACY BUDGET)]
# ==========================================
elif scelta == "🏗️ Commesse":
    st.header("Gestione Progetti")
    c_db = leggi_tabella("commesse")
    
    # Filtro PM: vede solo quelle assegnate a lui
    if ruolo == "PM":
        c_db = [c for c in c_db if c.get('pm_assegnato') == nome_log]
    
    for c in c_db:
        with st.container():
            col_a, col_b = st.columns([3,1])
            col_a.subheader(f"📂 {c['codice']} - {c['cliente']}")
            if ruolo == "Admin": # Solo Admin vede il budget
                col_b.metric("Budget", f"€ {c.get('budget', 0)}")
            st.write(f"Responsabile PM: {c.get('pm_assegnato', 'Non assegnato')}")
            st.divider()

# ==========================================
# [08_NUOVA COMMESSA (CON SCELTA PM)]
# ==========================================
elif scelta == "🎯 Assegnazione":
    st.header("Crea Progetto o Task")
    utenti = leggi_tabella("utenti")
    pms = [u['nome'] for u in utenti if u['ruolo'] in ["PM", "Admin"]]
    
    with st.form("nuova_c"):
        st.subheader("Crea Commessa")
        c1, c2 = st.columns(2)
        cod = c1.text_input("Codice")
        cli = c1.text_input("Cliente")
        pm_sel = c2.selectbox("Assegna PM Responsabile", pms)
        bud = c2.number_input("Budget (€)", min_value=0.0)
        if st.form_submit_button("Crea Commessa"):
            scrivi_dati("commesse", {"codice": cod, "cliente": cli, "pm_assegnato": pm_sel, "budget": bud, "scadenza": str(date.today())})
            st.success("Commessa creata!")
