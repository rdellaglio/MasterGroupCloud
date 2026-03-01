import streamlit as st
import httpx
import smtplib
from email.mime.text import MIMEText
from datetime import date, datetime
#Rev 01.04
# ==========================================
# [01] CONFIGURAZIONE & BRANDING
# ==========================================
st.set_page_config(page_title="MasterGroup Cloud", page_icon="🏗️", layout="wide")

TASK_STANDARD = [
    "CME (Computo Metrico Estimativo)", "CILA / SCIA / PdC", "DOCFA (Variazione Catastale)", 
    "APE (Attestato Energetico)", "Relazione Legge 10", "Sopralluogo / Rilievo",
    "Contabilità (SAL)", "Sicurezza (PSC / POS)", "Pratica ENEA", "Redazione Elaborati Grafici"
]

st.markdown("""
    <style>
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stHeader"] {background-color: rgba(0,0,0,0); height: 3rem;}
    [data-testid="stSidebarNav"] {padding-top: 20px;}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# [02] CONNESSIONE & MOTORE DB (CACHE KILLER)
# ==========================================
URL = st.secrets.get("SUPABASE_URL")
KEY = st.secrets.get("SUPABASE_KEY")
HEADERS = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

def db_get(tabella):
    try:
        # Il parametro 't' forza il DB a ignorare la cache e dare dati reali
        res = httpx.get(f"{URL}/rest/v1/{tabella}?select=*&t={datetime.now().timestamp()}", headers=HEADERS, timeout=10)
        return res.json() if res.status_code == 200 else []
    except: return []

def db_update(tabella, id_riga, payload):
    return httpx.patch(f"{URL}/rest/v1/{tabella}?id=eq.{id_riga}", headers=HEADERS, json=payload)

def db_insert(tabella, payload):
    return httpx.post(f"{URL}/rest/v1/{tabella}", headers=HEADERS, json=payload)

def get_meteo_bari():
    try:
        res = httpx.get("https://api.open-meteo.com/v1/forecast?latitude=41.11&longitude=16.87&current_weather=true").json()
        temp = res["current_weather"]["temperature"]
        return f"☀️ Bari: {temp}°C. Buon lavoro al team MasterGroup!"
    except: return "🌤️ MasterGroup Cloud pronto."

# ==========================================
# [03] ACCESSO & SESSIONE
# ==========================================
if "u" not in st.session_state:
    st.title("🏗️ MasterGroup Cloud")
    with st.form("login_form"):
        m = st.text_input("Email Aziendale").strip().lower()
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Accedi"):
            utenti = db_get("utenti")
            user = next((x for x in utenti if str(x.get('email', '')).lower() == m and str(x.get('password', '')) == p), None)
            if user:
                st.session_state.u = user
                st.rerun()
            else: st.error("Credenziali non valide.")
    st.stop()

u = st.session_state.u
ruolo, nome_u = u.get('ruolo'), u.get('nome')

# ==========================================
# [04] SIDEBAR & NAVIGAZIONE
# ==========================================
st.sidebar.title("MasterGroup")
st.sidebar.write(f"👤 **{nome_u}**")
st.sidebar.caption(f"Ruolo: {ruolo}")
st.sidebar.divider()

menu = ["🏠 Dashboard", "📋 Gestione Task"]
if ruolo in ["Admin", "PM"]: menu.extend(["📊 Analisi Commesse", "🎯 Assegnazione"])

scelta = st.sidebar.radio("Navigazione", menu)
if st.sidebar.button("Logout"):
    del st.session_state.u
    st.rerun()

# ==========================================
# [05] DASHBOARD
# ==========================================
if scelta == "🏠 Dashboard":
    st.header(f"Ciao {nome_u}, bentornato/a in Studio")
    st.info(get_meteo_bari())
    
    ts = db_get("task")
    miei_aperti = [t for t in ts if t.get('assegnato_a') == nome_u and t.get('stato') != 'Completato']
    
    col1, col2 = st.columns(2)
    col1.metric("I tuoi Task aperti", len(miei_aperti))
    
    if ruolo == "Admin":
        cs = db_get("commesse")
        # Calcolo budget totale (nome campo: budget)
        tot_b = sum(float(c.get('budget', 0)) for c in cs)
        col2.metric("Budget Totale Commesse", f"€ {tot_b:,.2f}")

# ==========================================
# [06] GESTIONE TASK (RIASSEGNAZIONE SOLO ADMIN)
# ==========================================
elif scelta == "📋 Gestione Task":
    st.header("Monitoraggio Attività")
    ts, cs, us = db_get("task"), db_get("commesse"), db_get("utenti")
    oggi = date.today()

    # --- FILTRI ---
    f1, f2, f3 = st.columns(3)
    sel_tec = nome_u if ruolo == "Operatore" else f1.selectbox("Filtra Tecnico", ["Tutti"] + [usr.get('nome') for usr in us])
    sel_com = f2.selectbox("Filtra Commessa", ["Tutte"] + [cm.get('codice') for cm in cs])
    sel_sta = f3.selectbox("Filtra Stato", ["Tutti", "In corso", "Bloccato", "Completato"])

    # --- LOGICA FILTRO ---
    f_t = ts
    if sel_tec != "Tutti" and ruolo != "Operatore": f_t = [t for t in f_t if t.get('assegnato_a') == sel_tec]
    elif ruolo == "Operatore": f_t = [t for t in f_t if t.get('assegnato_a') == nome_u]
    if sel_com != "Tutte": f_t = [t for t in f_t if t.get('commessa_ref') == sel_com]
    if sel_sta != "Tutti": f_t = [t for t in f_t if t.get('stato') == sel_sta]
    
    f_t.sort(key=lambda x: x.get('scadenza', '9999-12-31'))

    # --- VISUALIZZAZIONE TASK ---
    for t in f_t:
        try:
            d_scad = datetime.strptime(t['scadenza'], '%Y-%m-%d').date()
            diff = (d_scad - oggi).days
            label = f"⏳ {diff}gg" if diff >= 0 else f"⏰ SCADUTO ({abs(diff)}gg)"
        except: label, d_scad = "📅 Data n.d.", oggi
        
        pre = "🚨 " if t.get('stato') == 'Bloccato' else ""
        with st.expander(f"{pre}{label} | {t.get('commessa_ref')} - {t.get('descrizione')}"):
            
            # 🛠️ RIASSEGNAZIONE (Visibile SOLO ad Admin)
            if ruolo == "Admin":
                st.markdown("##### 🛠️ Area Riservata Admin")
                c_tec, c_dat = st.columns(2)
                l_utenti = [usr.get('nome') for usr in us]
                nuovo_tec = c_tec.selectbox("Riassegna a", l_utenti, index=l_utenti.index(t['assegnato_a']) if t['assegnato_a'] in l_utenti else 0, key=f"re_{t['id']}")
                nuova_scad = c_dat.date_input("Cambia Scadenza", value=d_scad, key=f"sc_{t['id']}")
                if st.button("Aggiorna Task", key=f"save_{t['id']}"):
                    db_update("task", t['id'], {"assegnato_a": nuovo_tec, "scadenza": str(nuova_scad)})
                    st.success("Modifiche salvate!")
                    st.rerun()
                st.divider()

            # 📈 STATO (Visibile a TUTTI)
            st.markdown("##### 📈 Stato Avanzamento")
            stati_v = ["In corso", "Completato", "Bloccato"]
            curr_st = t.get('stato', 'In corso')
            idx_s = stati_v.index(curr_st) if curr_st in stati_v else 0
            n_st = st.selectbox("Cambia Stato", stati_v, index=idx_s, key=f"st_{t['id']}")
            if st.button("Conferma Stato", key=f"up_{t['id']}"):
                db_update("task", t['id'], {"stato": n_st})
                st.success("Stato aggiornato!")
                st.rerun()

# ==========================================
# [07] ANALISI COMMESSE
# ==========================================
elif scelta == "📊 Analisi Commesse":
    st.header("Stato Avanzamento Progetti")
    cs, ts, oggi = db_get("commesse"), db_get("task"), date.today()
    for c in cs:
        t_comm = [t for t in ts if t.get('commessa_ref') == c.get('codice')]
        chiusi = len([t for t in t_comm if t['stato'] == 'Completato'])
        perc = (chiusi / len(t_comm) * 100) if t_comm else 0
        
        with st.expander(f"📂 {c['codice']} - {c['cliente']} ({int(perc)}%)"):
            if ruolo == "Admin":
                st.write(f"💰 Budget Commessa: **€ {c.get('budget', 0):,.2f}**")
            st.progress(perc / 100)
            for tc in t_comm:
                st.write(f"- **{tc.get('assegnato_a')}**: {tc.get('descrizione')} | [{tc.get('stato')}]")

# ==========================================
# [08] ASSEGNAZIONE (TABS & BUDGET)
# ==========================================
elif scelta == "🎯 Assegnazione":
    st.header("Nuova Gestione")
    tab1, tab2 = st.tabs(["🆕 Nuova Commessa", "📝 Nuovo Task"])
    
    with tab1:
        with st.form("form_commessa", clear_on_submit=True):
            st.subheader("Anagrafica Commessa")
            c_cod = st.text_input("Codice Commessa")
            c_cli = st.text_input("Nome Cliente")
            c_bud = st.number_input("Budget (€)", min_value=0.0, step=500.0)
            if st.form_submit_button("Crea Commessa"):
                if c_cod and c_cli:
                    res = db_insert("commesse", {"codice": c_cod, "cliente": c_cli, "budget": c_bud})
                    if res.status_code in [200, 201]: 
                        st.success("✅ Commessa creata con successo!")
                        st.rerun()
                    else: st.error(f"Errore DB: {res.status_code}")
                else: st.warning("Compila tutti i campi!")

    with tab2:
        with st.form("form_task", clear_on_submit=True):
            st.subheader("Assegnazione Attività")
            l_comms = [c['codice'] for c in db_get("commesse")]
            t_com = st.selectbox("Seleziona Commessa", l_comms)
            t_des = st.selectbox("Attività Standard", TASK_STANDARD)
            t_tec = st.selectbox("Assegna a", [u['nome'] for u in db_get("utenti")])
            t_dat = st.date_input("Scadenza Task", value=date.today())
            if st.form_submit_button("Invia Task"):
                payload = {
                    "commessa_ref": t_com, 
                    "descrizione": t_des, 
                    "assegnato_a": t_tec, 
                    "scadenza": str(t_dat), 
                    "stato": "In corso"
                }
                res = db_insert("task", payload)
                if res.status_code in [200, 201]: 
                    st.success("✅ Task assegnato correttamente!")
                else: st.error("Errore nella creazione del task.")
