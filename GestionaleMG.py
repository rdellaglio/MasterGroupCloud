import streamlit as st
import httpx
from datetime import date
import random

# ==========================================
# [01_CONFIGURAZIONE & CSS EQUILIBRATO]
# ==========================================
st.set_page_config(page_title="MasterGroup Cloud 🏗️", layout="wide")

# CSS MIRATO: Nascondiamo spazzatura ma lasciamo i comandi vitali
st.markdown("""
    <style>
    /* Nasconde il link 'Made with Streamlit' in basso */
    footer {visibility: hidden;}
    /* Nasconde il tasto Deploy e il menu '...' in alto a destra */
    .stDeployButton {display:none;}
    #stDecoration {display:none;}
    [data-testid="stHeader"] {background-color: rgba(0,0,0,0); height: 3rem;}
    /* Mantiene visibile il tasto del menu (le 3 linee) ma pulisce il resto */
    </style>
    """, unsafe_allow_html=True)

try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    URL = "https://clauyljovenkcqemswfk.supabase.co"
    KEY = "sb_publishable_WetwA7q8dmctM2a-VDBfTg_M46vnFi0"

headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

# Dati Fissi
ATTIVITA_STANDARD = [
    "Sopralluogo e Rilievo Strumentale", "Redazione Elaborati Grafici",
    "Pratica Edilizia (CILA/SCIA/PdC)", "Pratica Catastale (DOCFA)",
    "APE (Prestazione Energetica)", "Direzione Lavori", "Contabilità Lavori", "Altro..."
]

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
        e = st.text_input("Email Aziendale")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Entra"):
            utenti = leggi_tabella("utenti")
            u = next((x for x in utenti if x.get('email')==e and x.get('password')==p), None)
            if u: 
                st.session_state.autenticato = True
                st.session_state.u = u
                st.rerun()
            else:
                st.error("Credenziali errate.")
    st.stop()

u_log = st.session_state.u
ruolo = u_log['ruolo']
nome_log = u_log['nome']

# ==========================================
# [04_SIDEBAR & MENU]
# ==========================================
st.sidebar.title("🏗️ MasterGroup")
st.sidebar.info(f"👤 **{nome_log}**\n🔑 **{ruolo}**")

menu = ["🏠 Dashboard", "📋 Gestione Task"]
if ruolo in ["Admin", "PM"]:
    menu.extend(["📊 Analisi Commesse", "🎯 Assegnazione"])
if ruolo == "Admin":
    menu.append("⚖️ Approvazioni")

scelta = st.sidebar.radio("Navigazione", menu)

if st.sidebar.button("Logout"):
    st.session_state.autenticato = False
    st.rerun()

# ==========================================
# [05_DASHBOARD]
# ==========================================
if scelta == "🏠 Dashboard":
    st.header(f"Benvenuto, {nome_log}")
    
    cit = random.choice(CITAZIONI)
    st.info(f"🌤️ **Meteo Bari:** Sereno. Ottimo lavoro!\n\n💡 *\"{cit['t']}\"* — {cit['a']}")
    
    t_db = leggi_tabella("task")
    bloccati = [t for t in t_db if t.get('stato') == 'Bloccato']
    
    c1, c2 = st.columns(2)
    miei_t = [t for t in t_db if t['assegnato_a'] == nome_log and t['stato'] != 'Completato']
    c1.metric("Task da fare", len(miei_t))
    
    if ruolo in ["Admin", "PM"]:
        c2.metric("🆘 Criticità Studio", len(bloccati))

# ==========================================
# [06_GESTIONE TASK]
# ==========================================
elif scelta == "📋 Gestione Task":
    st.header("Lista Attività")
    t_db = leggi_tabella("task")
    utenti_list = leggi_tabella("utenti")
    
    col_f1, col_f2 = st.columns(2)
    
    filtro_tecnico = nome_log
    if ruolo in ["Admin", "PM"]:
        nomi_op = ["Tutti"] + [ut['nome'] for ut in utenti_list]
        filtro_tecnico = col_f1.selectbox("Tecnico", nomi_op)
    
    f_prio = col_f2.selectbox("Priorità", ["Tutte", "Alta", "Media", "Bassa"])

    tasks = t_db
    if filtro_tecnico != "Tutti": tasks = [t for t in tasks if t['assegnato_a'] == filtro_tecnico]
    if f_prio != "Tutte": tasks = [t for t in tasks if t['priorita'] == f_prio]

    p_map = {"Alta": 0, "Media": 1, "Bassa": 2}
    tasks.sort(key=lambda x: (p_map.get(x.get('priorita','Bassa'), 3), x.get('scadenza','9999-12-31')))

    for t in tasks:
        colore = "🔴" if t.get('priorita')=="Alta" else "🟡" if t.get('priorita')=="Media" else "🟢"
        with st.expander(f"{colore} [{t.get('scadenza')}] {t.get('commessa_ref')} - {t.get('descrizione')} ({t.get('assegnato_a')})"):
            st.write(f"Stato: **{t.get('stato')}**")
            
            if ruolo in ["Admin", "PM"] or t['assegnato_a'] == nome_log:
                nuovo_st = st.selectbox("Cambia Stato", ["In corso", "Completato", "Bloccato"], key=f"st_{t['id']}")
                nota = ""
                if nuovo_st == "Bloccato":
                    nota = st.text_area("Nota blocco", value=t.get('motivo_blocco',''), key=f"nt_{t['id']}")
                if st.button("Aggiorna Task", key=f"btn_{t['id']}"):
                    aggiorna_db("task", t['id'], {"stato": nuovo_st, "motivo_blocco": nota})
                    st.rerun()

# ==========================================
# [07_ANALISI COMMESSE]
# ==========================================
elif scelta == "📊 Analisi Commesse":
    st.header("Avanzamento Progetti")
    c_db = leggi_tabella("commesse")
    t_db = leggi_tabella("task")
    
    if ruolo == "PM":
        c_db = [c for c in c_db if c.get('pm_assegnato') == nome_log]

    for c in c_db:
        t_comm = [t for t in t_db if t.get('commessa_ref') == c['codice']]
        chiusi = len([t for t in t_comm if t['stato'] == 'Completato'])
        perc = (chiusi / len(t_comm) * 100) if t_comm else 0
        
        with st.expander(f"📂 {c['codice']} - {c['cliente']} ({int(perc)}%)"):
            col_i, col_p = st.columns([1, 2])
            with col_i:
                st.write(f"**PM:** {c.get('pm_assegnato')}")
                if ruolo == "Admin": st.write(f"**Budget:** € {c.get('budget', 0)}")
            with col_p:
                st.progress(perc / 100)
            st.write("**Team:** " + ", ".join(list(set([t['assegnato_a'] for t in t_comm]))))

# ==========================================
# [08_ASSEGNAZIONE]
# ==========================================
elif scelta == "🎯 Assegnazione":
    tab1, tab2 = st.tabs(["🏗️ Commessa", "📝 Task"])
    with tab1:
        with st.form("f_c"):
            cod = st.text_input("Codice")
            cli = st.text_input("Cliente")
            utenti = leggi_tabella("utenti")
            pms = [u['nome'] for u in utenti if u['ruolo'] in ["PM", "Admin"]]
            pm_sel = st.selectbox("PM Responsabile", pms)
            bud = st.number_input("Budget (€)", min_value=0.0)
            if st.form_submit_button("Crea"):
                scrivi_dati("commesse", {"codice": cod, "cliente": cli, "pm_assegnato": pm_sel, "budget": bud, "scadenza": str(date.today())})
                st.success("Fatto!")
    with tab2:
        with st.form("f_t"):
            c_db = leggi_tabella("commesse")
            sel_c = st.selectbox("Progetto", [c['codice'] for c in c_db])
            att = st.selectbox("Attività", ATTIVITA_STANDARD)
            utenti = leggi_tabella("utenti")
            chi = st.selectbox("Tecnico", [u['nome'] for u in utenti])
            prio = st.select_slider("Priorità", options=["Bassa", "Media", "Alta"])
            if st.form_submit_button("Assegna"):
                scrivi_dati("task", {"commessa_ref": sel_c, "descrizione": att, "assegnato_a": chi, "priorita": prio, "scadenza": str(date.today()), "stato": "In corso", "approvato_admin": (ruolo=="Admin")})
                st.success("Inviato!")
CITAZIONI = [
    {"t": "L'architettura è un cristallo.", "a": "Gio Ponti"},
    {"t": "Dio è nei dettagli.", "a": "Mies van der Rohe"},
    {"t": "La forma segue la funzione.", "a": "Louis Sullivan"},
    {"t": "L'architettura deve commuovere.", "a": "Le Corbusier"},
    {"t": "Usate la matita come se fosse una spada.", "a": "Franco Albini"}
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
    st.subheader("Accesso Area Riservata")
    with st.form("login_form"):
        e = st.text_input("Email Aziendale")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Entra"):
            utenti = leggi_tabella("utenti")
            u = next((x for x in utenti if x.get('email')==e and x.get('password')==p), None)
            if u: 
                st.session_state.autenticato = True
                st.session_state.u = u
                st.rerun()
            else:
                st.error("Credenziali errate.")
    st.stop()

u_log = st.session_state.u
ruolo = u_log['ruolo']
nome_log = u_log['nome']

# ==========================================
# [04_SIDEBAR & MENU]
# ==========================================
st.sidebar.title("🏗️ MasterGroup")
st.sidebar.info(f"👤 **{nome_log}**\n🔑 Ruolo: **{ruolo}**")

menu = ["🏠 Dashboard", "📋 Gestione Task"]
if ruolo in ["Admin", "PM"]:
    menu.extend(["📊 Analisi Commesse", "🎯 Assegnazione"])
if ruolo == "Admin":
    menu.append("⚖️ Approvazioni")

scelta = st.sidebar.radio("Navigazione", menu)

if st.sidebar.button("Logout"):
    st.session_state.autenticato = False
    st.rerun()

# ==========================================
# [05_DASHBOARD]
# ==========================================
if scelta == "🏠 Dashboard":
    st.header(f"Benvenuto, {nome_log}")
    
    cit = random.choice(CITAZIONI)
    st.info(f"🌤️ **Meteo Bari:** Sereno (21°C). Buon lavoro!\n\n💡 *\"{cit['t']}\"* — {cit['a']}")
    
    t_db = leggi_tabella("task")
    bloccati = [t for t in t_db if t.get('stato') == 'Bloccato']
    
    col1, col2 = st.columns(2)
    miei_task = [t for t in t_db if t['assegnato_a'] == nome_log and t['stato'] != 'Completato']
    col1.metric("Miei Task Attivi", len(miei_task))
    
    if ruolo in ["Admin", "PM"]:
        col2.metric("🆘 Criticità Studio", len(bloccati), delta_color="inverse")
        if bloccati:
            st.warning(f"Attenzione: {len(bloccati)} attività risultano bloccate.")

# ==========================================
# [06_GESTIONE TASK]
# ==========================================
elif scelta == "📋 Gestione Task":
    st.header("Lista Attività")
    t_db = leggi_tabella("task")
    utenti_list = leggi_tabella("utenti")
    
    c1, c2, c3 = st.columns(3)
    
    filtro_tecnico = nome_log
    if ruolo in ["Admin", "PM"]:
        nomi_op = ["Tutti"] + [ut['nome'] for ut in utenti_list]
        filtro_tecnico = c1.selectbox("Filtra Tecnico", nomi_op)
    
    f_prio = c2.selectbox("Priorità", ["Tutte", "Alta", "Media", "Bassa"])
    f_stato = c3.selectbox("Stato", ["Tutti", "In corso", "Bloccato", "Completato"])

    tasks = t_db
    if filtro_tecnico != "Tutti": tasks = [t for t in tasks if t['assegnato_a'] == filtro_tecnico]
    if f_prio != "Tutte": tasks = [t for t in tasks if t['priorita'] == f_prio]
    if f_stato != "Tutti": tasks = [t for t in tasks if t['stato'] == f_stato]

    p_map = {"Alta": 0, "Media": 1, "Bassa": 2}
    tasks.sort(key=lambda x: (p_map.get(x.get('priorita','Bassa'), 3), x.get('scadenza','9999-12-31')))

    for t in tasks:
        colore = "🔴" if t.get('priorita')=="Alta" else "🟡" if t.get('priorita')=="Media" else "🟢"
        with st.expander(f"{colore} [{t.get('scadenza')}] {t.get('commessa_ref')} - {t.get('descrizione')} ({t.get('assegnato_a')})"):
            st.write(f"Stato: **{t.get('stato')}**")
            if t.get('motivo_blocco'): st.error(f"Motivo Blocco: {t['motivo_blocco']}")
            
            if ruolo in ["Admin", "PM"] or t['assegnato_a'] == nome_log:
                nuovo_st = st.selectbox("Aggiorna Stato", ["In corso", "Completato", "Bloccato"], key=f"st_{t['id']}")
                nota = ""
                if nuovo_st == "Bloccato":
                    nota = st.text_area("Nota blocco", value=t.get('motivo_blocco',''), key=f"nt_{t['id']}")
                if st.button("Salva", key=f"btn_{t['id']}"):
                    aggiorna_db("task", t['id'], {"stato": nuovo_st, "motivo_blocco": nota})
                    st.rerun()

# ==========================================
# [07_ANALISI COMMESSE INTERATTIVA]
# ==========================================
elif scelta == "📊 Analisi Commesse":
    st.header("Avanzamento Progetti")
    c_db = leggi_tabella("commesse")
    t_db = leggi_tabella("task")
    
    if ruolo == "PM":
        c_db = [c for c in c_db if c.get('pm_assegnato') == nome_log]

    for c in c_db:
        t_comm = [t for t in t_db if t.get('commessa_ref') == c['codice']]
        chiusi = len([t for t in t_comm if t['stato'] == 'Completato'])
        perc = (chiusi / len(t_comm) * 100) if t_comm else 0
        
        with st.expander(f"📂 {c['codice']} - {c['cliente']} ({int(perc)}%)"):
            col_i, col_p = st.columns([1, 2])
            with col_i:
                st.write(f"**PM:** {c.get('pm_assegnato')}")
                if ruolo == "Admin": st.write(f"**Budget:** € {c.get('budget', 0)}")
            with col_p:
                st.progress(perc / 100)
            
            st.write("**Dettaglio Attività:**")
            for tc in t_comm:
                st.write(f"- {'✅' if tc['stato']=='Completato' else '⏳'} **{tc['assegnato_a']}**: {tc['descrizione']} ({tc['priorita']})")

# ==========================================
# [08_ASSEGNAZIONE]
# ==========================================
elif scelta == "🎯 Assegnazione":
    tab1, tab2 = st.tabs(["🏗️ Commessa", "📝 Task"])
    
    with tab1:
        with st.form("f_comm"):
            c1, c2 = st.columns(2)
            cod = c1.text_input("Codice")
            cli = c1.text_input("Cliente")
            utenti = leggi_tabella("utenti")
            pms = [u['nome'] for u in utenti if u['ruolo'] in ["PM", "Admin"]]
            pm_sel = c2.selectbox("Responsabile PM", pms)
            bud = c2.number_input("Budget (€)", min_value=0.0)
            if st.form_submit_button("Crea Commessa"):
                scrivi_dati("commesse", {"codice": cod, "cliente": cli, "pm_assegnato": pm_sel, "budget": bud, "scadenza": str(date.today())})
                st.success("Commessa creata!")

    with tab2:
        with st.form("f_task"):
            c_db = leggi_tabella("commesse")
            sel_c = st.selectbox("Progetto", [c['codice'] for c in c_db] if c_db else ["Nessuna"])
            att = st.selectbox("Attività", ATTIVITA_STANDARD)
            utenti = leggi_tabella("utenti")
            chi = st.selectbox("Assegna a", [u['nome'] for u in utenti])
            prio = st.select_slider("Priorità", options=["Bassa", "Media", "Alta"])
            scad = st.date_input("Scadenza")
            if st.form_submit_button("Assegna Task"):
                appr = True if ruolo == "Admin" else False
                scrivi_dati("task", {"commessa_ref": sel_c, "descrizione": att, "assegnato_a": chi, "priorita": prio, "scadenza": str(scad), "stato": "In corso", "approvato_admin": appr})
                st.success("Task inviato!")

# ==========================================
# [09_APPROVAZIONI ADMIN]
# ==========================================
elif scelta == "⚖️ Approvazioni":
    st.header("Validazione Task")
    t_all = leggi_tabella("task")
    da_val = [t for t in t_all if t.get('approvato_admin') == False]
    if not da_val: st.success("Nessun task in attesa.")
    for v in da_val:
        st.warning(f"Task: {v['descrizione']} | PM: {v.get('commessa_ref')} | Prio: {v['priorita']}")
        if st.button("Approva", key=f"ok_{v['id']}"):
            aggiorna_db("task", v['id'], {"approvato_admin": True})
            st.rerun()

