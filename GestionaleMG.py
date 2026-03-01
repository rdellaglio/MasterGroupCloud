import streamlit as st
import httpx
from datetime import date, datetime
import random

# ==========================================
# [01_CONFIGURAZIONE & CSS]
# ==========================================
st.set_page_config(page_title="MasterGroup Cloud 🏗️", layout="wide")

st.markdown("""
    <style>
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
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
    with st.form("login_form"):
        e = st.text_input("Email Aziendale", key="l_email")
        p = st.text_input("Password", type="password", key="l_pass")
        if st.form_submit_button("Entra"):
            utenti = leggi_tabella("utenti")
            u = next((x for x in utenti if x.get('email')==e and x.get('password')==p), None)
            if u: 
                st.session_state.autenticato = True
                st.session_state.u = u
                st.rerun()
            else: st.error("Credenziali errate.")
    st.stop()

u_log = st.session_state.u
ruolo = u_log['ruolo']
nome_log = u_log['nome']

# ==========================================
# [04_SIDEBAR]
# ==========================================
st.sidebar.title("🏗️ MasterGroup")
menu = ["🏠 Dashboard", "📋 Gestione Task"]
if ruolo in ["Admin", "PM"]:
    menu.extend(["📊 Analisi Commesse", "🎯 Assegnazione"])
scelta = st.sidebar.radio("Navigazione", menu, key="nav_radio")

if st.sidebar.button("Logout"):
    st.session_state.autenticato = False
    st.rerun()

# ==========================================
# [05_DASHBOARD]
# ==========================================
if scelta == "🏠 Dashboard":
    st.header(f"Area Personale - {nome_log}")
    t_db = leggi_tabella("task")
    bloccati = [t for t in t_db if t.get('stato') == 'Bloccato']
    
    if bloccati and ruolo in ["Admin", "PM"]:
        st.error(f"🚨 SOS: Ci sono {len(bloccati)} task in stato BLOCCATO!")
    
    miei_t = [t for t in t_db if t['assegnato_a'] == nome_log and t['stato'] != 'Completato']
    st.metric("I miei Task aperti", len(miei_t))

# ==========================================
# [06_GESTIONE TASK (FILTRI POTENZIATI)]
# ==========================================
elif scelta == "📋 Gestione Task":
    st.header("Filtri e Operatività")
    t_db = leggi_tabella("task")
    c_db = leggi_tabella("commesse")
    utenti = leggi_tabella("utenti")
    
    col1, col2, col3 = st.columns(3)
    
    # Filtro Tecnico
    f_nome = nome_log
    if ruolo in ["Admin", "PM"]:
        f_nome = col1.selectbox("Tecnico", ["Tutti"] + [ut['nome'] for ut in utenti], key="f_t")
    
    # Filtro Commessa (Novità)
    f_comm = col2.selectbox("Commessa", ["Tutte"] + [c['codice'] for c in c_db], key="f_c")
    
    # Filtro Stato
    f_stato = col3.selectbox("Stato", ["Tutti", "In corso", "Bloccato", "Completato"], key="f_s")

    # Applicazione Filtri
    tasks = t_db
    if f_nome != "Tutti": tasks = [t for t in tasks if t['assegnato_a'] == f_nome]
    if f_comm != "Tutte": tasks = [t for t in tasks if t['commessa_ref'] == f_comm]
    if f_stato != "Tutti": tasks = [t for t in tasks if t['stato'] == f_stato]

    # Ordinamento
    p_map = {"Alta": 0, "Media": 1, "Bassa": 2}
    tasks.sort(key=lambda x: (p_map.get(x.get('priorita','Bassa'), 3), x.get('scadenza','')))

    for t in tasks:
        # Icona Sirena se bloccato
        prefix = "🚨 " if t.get('stato') == 'Bloccato' else ""
        color = "🔴" if t.get('priorita')=="Alta" else "🟡" if t.get('priorita')=="Media" else "🟢"
        
        with st.expander(f"{prefix}{color} [{t.get('scadenza')}] {t.get('commessa_ref')} - {t.get('descrizione')}"):
            st.write(f"Responsabile: **{t['assegnato_a']}**")
            if t.get('motivo_blocco'): st.warning(f"MOTIVO BLOCCO: {t['motivo_blocco']}")
            
            # Modifica permessa a titolare task, PM o Admin
            nuovo_st = st.selectbox("Aggiorna Stato", ["In corso", "Completato", "Bloccato"], 
                                   index=["In corso", "Completato", "Bloccato"].index(t['stato']), key=f"s_{t['id']}")
            nota = ""
            if nuovo_st == "Bloccato":
                nota = st.text_area("Specifica il blocco", value=t.get('motivo_blocco',''), key=f"n_{t['id']}")
            
            if st.button("Salva Modifiche", key=f"b_{t['id']}"):
                aggiorna_db("task", t['id'], {"stato": nuovo_st, "motivo_blocco": nota})
                st.rerun()

# ==========================================
# [07_ANALISI COMMESSE (CON ALERT SCADENZE)]
# ==========================================
elif scelta == "📊 Analisi Commesse":
    st.header("Monitoraggio Avanzamento e Scadenze")
    c_db = leggi_tabella("commesse")
    t_db = leggi_tabella("task")
    oggi = date.today()

    for c in c_db:
        t_comm = [t for t in t_db if t.get('commessa_ref') == c['codice']]
        chiusi = len([t for t in t_comm if t['stato'] == 'Completato'])
        perc = (chiusi / len(t_comm) * 100) if t_comm else 0
        
        with st.expander(f"📂 {c['codice']} - {c['cliente']} ({int(perc)}%)"):
            st.progress(perc / 100)
            st.write("**Dettaglio Attività e Scadenze:**")
            
            for tc in t_comm:
                # Logica Icone Scadenze
                icona_tempo = ""
                try:
                    data_scad = datetime.strptime(tc['scadenza'], '%Y-%m-%d').date()
                    if tc['stato'] != 'Completato':
                        if data_scad < oggi: icona_tempo = "⏰ **RITARDO**"
                except: pass
                
                # Icona Allarme se bloccato
                icona_alert = "🛑 **ALLARME BLOCCATO**" if tc['stato'] == 'Bloccato' else ""
                
                st.write(f"- {tc['assegnato_a']}: {tc['descrizione']} | Scadenza: {tc['scadenza']} {icona_tempo} {icona_alert}")

# ==========================================
# [08_ASSEGNAZIONE]
# ==========================================
elif scelta == "🎯 Assegnazione":
    t1, t2 = st.tabs(["Crea Commessa", "Assegna Task"])
    with t1:
        with st.form("f_c"):
            c1, c2 = st.columns(2)
            cod = c1.text_input("Codice Commessa")
            cli = c1.text_input("Cliente")
            ut = leggi_tabella("utenti")
            pm = c2.selectbox("PM Responsabile", [u['nome'] for u in ut if u['ruolo'] in ['Admin', 'PM']])
            bud = c2.number_input("Budget (€)", min_value=0.0)
            if st.form_submit_button("Registra"):
                scrivi_dati("commesse", {"codice": cod, "cliente": cli, "pm_assegnato": pm, "budget": bud, "scadenza": str(date.today())})
                st.success("Commessa creata!")
    with t2:
        with st.form("f_t"):
            c_db = leggi_tabella("commesse")
            sel_c = st.selectbox("Progetto", [c['codice'] for c in c_db])
            desc = st.text_input("Descrizione Lavoro")
            ut = leggi_tabella("utenti")
            chi = st.selectbox("Assegna a", [u['nome'] for u in ut])
            prio = st.selectbox("Priorità", ["Bassa", "Media", "Alta"])
            scad = st.date_input("Consegna prevista")
            if st.form_submit_button("Invia Task"):
                scrivi_dati("task", {"commessa_ref": sel_c, "descrizione": desc, "assegnato_a": chi, "priorita": prio, "scadenza": str(scad), "stato": "In corso"})
                st.success("Assegnato!")
