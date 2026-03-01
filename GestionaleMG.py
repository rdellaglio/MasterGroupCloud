import streamlit as st
import httpx
import smtplib
from email.mime.text import MIMEText
from datetime import date, datetime
#REV 01.03
# ==========================================
# [01] CONFIGURAZIONE & BRANDING
# ==========================================
st.set_page_config(page_title="MasterGroup Cloud", page_icon="🏗️", layout="wide")

TASK_STANDARD = [
    "CME (Computo Metrico Estimativo)", "CILA / SCIA / PdC", "DOCFA (Variazione Catastale)", 
    "APE (Attestato Energetico)", "Relazione Legge 10", "Sopralluogo / Rilievo",
    "Contabilità (SAL)", "Sicurezza (PSC / POS)", "Pratica ENEA", "Redazione Elaborati Grafici"
]

# CSS per pulizia interfaccia
st.markdown("""
    <style>
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stHeader"] {background-color: rgba(0,0,0,0); height: 3rem;}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# [02] CONNESSIONE & MOTORE DB
# ==========================================
URL = st.secrets.get("SUPABASE_URL")
KEY = st.secrets.get("SUPABASE_KEY")
HEADERS = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

def db_get(tabella):
    try:
        # Cache killer per dati sempre freschi
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
# [03] GESTIONE ACCESSO
# ==========================================
if "u" not in st.session_state:
    st.title("🏗️ MasterGroup Cloud")
    with st.form("login"):
        m = st.text_input("Email Aziendale").strip().lower()
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Accedi"):
            utenti = db_get("utenti")
            user = next((x for x in utenti if str(x.get('email', '')).lower() == m and str(x.get('password', '')) == p), None)
            if user:
                st.session_state.u = user
                st.rerun()
            else: st.error("Email o Password errati.")
    st.stop()

u = st.session_state.u
ruolo, nome_u = u.get('ruolo'), u.get('nome')

# ==========================================
# [04] SIDEBAR & NAVIGAZIONE
# ==========================================
st.sidebar.title("MasterGroup")
st.sidebar.write(f"👤 **{nome_u}** ({ruolo})")
st.sidebar.divider()

menu = ["🏠 Dashboard", "📋 Gestione Task"]
if ruolo in ["Admin", "PM"]: menu.extend(["📊 Analisi Commesse", "🎯 Assegnazione"])

scelta = st.sidebar.radio("Navigazione", menu)
if st.sidebar.button("Logout"):
    del st.session_state.u
    st.rerun()

# ==========================================
# [05] DASHBOARD (GENDER NEUTRAL)
# ==========================================
if scelta == "🏠 Dashboard":
    st.header(f"Ciao {nome_u}, bentornato/a in Studio")
    st.info(get_meteo_bari())
    
    ts = db_get("task")
    miei = [t for t in ts if t.get('assegnato_a') == nome_u and t.get('stato') != 'Completato']
    
    c1, c2 = st.columns(2)
    c1.metric("I tuoi Task aperti", len(miei))
    if ruolo == "Admin":
        cs = db_get("commesse")
        tot_budget = sum(float(c.get('budget', 0)) for c in cs)
        c2.metric("Budget Totale Commesse", f"€ {tot_budget:,.2f}")

# ==========================================
# [06] GESTIONE TASK
# ==========================================
elif scelta == "📋 Gestione Task":
    st.header("Monitoraggio Attività")
    ts, cs, us = db_get("task"), db_get("commesse"), db_get("utenti")
    oggi = date.today()

    c1, c2, c3 = st.columns(3)
    f_nome = nome_u if ruolo == "Operatore" else c1.selectbox("Filtra Tecnico", ["Tutti"] + [usr.get('nome') for usr in us])
    f_comm = c2.selectbox("Filtra Commessa", ["Tutte"] + [cm.get('codice') for cm in cs])
    f_stato = c3.selectbox("Filtra Stato", ["Tutti", "In corso", "Bloccato", "Completato"])

    f_t = ts
    if f_nome != "Tutti" and ruolo != "Operatore": f_t = [t for t in f_t if t.get('assegnato_a') == f_nome]
    elif ruolo == "Operatore": f_t = [t for t in f_t if t.get('assegnato_a') == nome_u]
    if f_comm != "Tutte": f_t = [t for t in f_t if t.get('commessa_ref') == f_comm]
    if f_stato != "Tutti": f_t = [t for t in f_t if t.get('stato') == f_stato]
    
    f_t.sort(key=lambda x: x.get('scadenza', '9999-12-31'))

    for t in f_t:
        try:
            d_scad = datetime.strptime(t['scadenza'], '%Y-%m-%d').date()
            diff = (d_scad - oggi).days
            label = f"⏳ {diff}gg" if diff >= 0 else f"⏰ SCADUTO ({abs(diff)}gg)"
        except: label, d_scad = "📅 Data n.d.", oggi
        
        with st.expander(f"{label} | {t.get('commessa_ref')} - {t.get('descrizione')}"):
            if ruolo == "Admin":
                st.subheader("🛠️ Riassegnazione (Admin)")
                l_nomi = [usr.get('nome') for usr in us]
                n_tec = st.selectbox("Tecnico", l_nomi, index=l_nomi.index(t['assegnato_a']) if t['assegnato_a'] in l_nomi else 0, key=f"re_{t['id']}")
                n_scad = st.date_input("Scadenza", value=d_scad, key=f"sc_{t['id']}")
                if st.button("Salva Modifiche", key=f"save_{t['id']}"):
                    db_update("task", t['id'], {"assegnato_a": n_tec, "scadenza": str(n_scad)})
                    st.success("Modificato!")
                    st.rerun()
            
            st.divider()
            stati_v = ["In corso", "Completato", "Bloccato"]
            curr_st = t.get('stato', 'In corso')
            idx_s = stati_v.index(curr_st) if curr_st in stati_v else 0
            n_st = st.selectbox("Aggiorna Stato", stati_v, index=idx_s, key=f"st_{t['id']}")
            if st.button("Conferma Stato", key=f"up_{t['id']}"):
                db_update("task", t['id'], {"stato": n_st})
                st.rerun()

# ==========================================
# [07] ANALISI COMMESSE (USO CAMPO BUDGET)
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
                st.write(f"💰 Budget: **€ {c.get('budget', 0):,.2f}**")
            st.progress(perc / 100)
            for tc in t_comm:
                st.write(f"- {tc.get('assegnato_a')}: {tc.get('descrizione')} [{tc.get('stato')}]")

# ==========================================
# [08] ASSEGNAZIONE (RIPRISTINO BUDGET)
# ==========================================
elif scelta == "🎯 Assegnazione":
    st.header("Nuova Commessa o Task")
    tab1, tab2 = st.tabs(["🆕 Commessa", "📝 Task"])
    with tab1:
        with st.form("f_c", clear_on_submit=True):
            c_cod = st.text_input("Codice")
            c_cli = st.text_input("Cliente")
            c_bud = st.number_input("Budget / Valore (€)", min_value=0.0, step=500.0) # Uso nome Budget
            if st.form_submit_button("Crea Commessa"):
                if c_cod and c_cli:
                    res = db_insert("commesse", {"codice": c_cod, "cliente": c_cli, "budget": c_bud})
                    if res.status_code in [200, 201]: st.success("Commessa creata!"); st.rerun()
                    else: st.error(f"Errore DB: {res.status_code}. Verifica campo 'budget' su Supabase.")
    with tab2:
        with st.form("f_t", clear_on_submit=True):
            comms = [c['codice'] for c in db_get("commesse")]
            t_comm = st.selectbox("Commessa", comms)
            t_desc = st.selectbox("Attività", TASK_STANDARD)
            t_tec = st.selectbox("Tecnico", [u['nome'] for u in db_get("utenti")])
            t_scad = st.date_input("Scadenza")
            if st.form_submit_button("Assegna Task"):
                db_insert("task", {"commessa_ref": t_comm, "descrizione": t_desc, "assegnato_a": t_tec, "scadenza": str(t_scad), "stato": "In corso"})
                st.success("Task creato!")
