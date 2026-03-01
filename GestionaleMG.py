import streamlit as st
import httpx
import smtplib
from email.mime.text import MIMEText
from datetime import date, datetime
#REV 01.xx
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
# [02] CONNESSIONE & SEGRETI
# ==========================================
URL = st.secrets.get("SUPABASE_URL")
KEY = st.secrets.get("SUPABASE_KEY")
MAIL_USER = st.secrets.get("EMAIL_MITTENTE")
MAIL_PASS = st.secrets.get("EMAIL_PASSWORD")

if not URL or not KEY:
    st.error("⚠️ Chiavi configurazione mancanti!")
    st.stop()

HEADERS = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

# ==========================================
# [03] FUNZIONI MOTORE
# ==========================================
def db_get(tabella):
    try:
        res = httpx.get(f"{URL}/rest/v1/{tabella}?select=*", headers=HEADERS, timeout=10)
        return res.json() if res.status_code == 200 else []
    except: return []

def db_update(tabella, id_riga, payload):
    return httpx.patch(f"{URL}/rest/v1/{tabella}?id=eq.{id_riga}", headers=HEADERS, json=payload)

def db_insert(tabella, payload):
    return httpx.post(f"{URL}/rest/v1/{tabella}", headers=HEADERS, json=payload)

def invia_mail(destinatario, oggetto, corpo):
    if not MAIL_USER or not MAIL_PASS: return
    try:
        msg = MIMEText(corpo)
        msg['Subject'] = oggetto
        msg['From'] = f"MasterGroup Cloud <{MAIL_USER}>"
        msg['To'] = destinatario
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(MAIL_USER, MAIL_PASS)
            server.sendmail(MAIL_USER, destinatario, msg.as_string())
    except: pass

def get_meteo_bari():
    try:
        res = httpx.get("https://api.open-meteo.com/v1/forecast?latitude=41.11&longitude=16.87&current_weather=true").json()
        temp = res["current_weather"]["temperature"]
        return f"☀️ Bari: {temp}°C. Buon lavoro al team MasterGroup!"
    except: return "🌤️ MasterGroup Cloud pronto."

# ==========================================
# [04] ACCESSO
# ==========================================
if "u" not in st.session_state:
    st.title("🏗️ MasterGroup Cloud")
    with st.form("login"):
        m = st.text_input("Email Aziendale").strip().lower()
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Accedi"):
            utenti = db_get("utenti")
            user = next((x for x in utenti if str(x.get('email', '')).lower() == m and str(x.get('password')) == p), None)
            if user:
                st.session_state.u = user
                st.rerun()
            else: st.error("Credenziali non valide.")
    st.stop()

u = st.session_state.u
ruolo, nome_u = u.get('ruolo'), u.get('nome')

# ==========================================
# [05] SIDEBAR
# ==========================================
st.sidebar.title("MasterGroup")
st.sidebar.write(f"👤 **{nome_u}**")
st.sidebar.write(f"💼 Ruolo: {ruolo}")
st.sidebar.divider()

menu = ["🏠 Dashboard", "📋 Gestione Task"]
if ruolo in ["Admin", "PM"]: menu.extend(["📊 Analisi Commesse", "🎯 Assegnazione"])
if ruolo == "Admin": menu.append("⚖️ Approvazioni")

scelta = st.sidebar.radio("Navigazione", menu)
if st.sidebar.button("Logout"):
    del st.session_state.u
    st.rerun()

# ==========================================
# [06] DASHBOARD
# ==========================================
if scelta == "🏠 Dashboard":
    st.header(f"Bentornato, {nome_u}")
    st.info(get_meteo_bari())
    ts = db_get("task")
    miei = [t for t in ts if t.get('assegnato_a') == nome_u and t.get('stato') != 'Completato']
    st.metric("I tuoi Task aperti", len(miei))

# ==========================================
# [07] GESTIONE TASK (RIASSEGNAZIONE SOLO ADMIN)
# ==========================================
elif scelta == "📋 Gestione Task":
    st.header("Monitoraggio Attività")
    ts, cs, us = db_get("task"), db_get("commesse"), db_get("utenti")
    oggi = date.today()

    # Filtri
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
            
            # --- SOLO ADMIN PUÒ RIASSEGNARE ---
            if ruolo == "Admin":
                st.subheader("🛠️ Modifica Avanzata (Admin)")
                l_nomi = [usr.get('nome') for usr in us]
                n_tec = st.selectbox("Cambia Tecnico", l_nomi, index=l_nomi.index(t['assegnato_a']) if t['assegnato_a'] in l_nomi else 0, key=f"re_{t['id']}")
                n_scad = st.date_input("Cambia Scadenza", value=d_scad, key=f"sc_{t['id']}")
                if st.button("Salva Modifiche", key=f"save_{t['id']}"):
                    db_update("task", t['id'], {"assegnato_a": n_tec, "scadenza": str(n_scad), "approvato_admin": True})
                    st.success("Task aggiornato correttamente!")
                    st.rerun()
            
            st.divider()
            # --- TUTTI POSSONO AGGIORNARE LO STATO ---
            st.subheader("📈 Stato Avanzamento")
            stati_v = ["In corso", "Completato", "Bloccato"]
            curr_st = t.get('stato', 'In corso')
            idx_s = stati_v.index(curr_st) if curr_st in stati_v else 0
            n_st = st.selectbox("Cambia Stato", stati_v, index=idx_s, key=f"st_{t['id']}")
            if st.button("Aggiorna Stato", key=f"up_{t['id']}"):
                db_update("task", t['id'], {"stato": n_st})
                st.success("Stato aggiornato!")
                st.rerun()

# ==========================================
# [08] ANALISI COMMESSE
# ==========================================
elif scelta == "📊 Analisi Commesse":
    st.header("Avanzamento Progetti")
    cs, ts, oggi = db_get("commesse"), db_get("task"), date.today()
    for c in cs:
        t_comm = [t for t in ts if t.get('commessa_ref') == c.get('codice')]
        chiusi = len([t for t in t_comm if t['stato'] == 'Completato'])
        perc = (chiusi / len(t_comm) * 100) if t_comm else 0
        with st.expander(f"📂 {c['codice']} - {c['cliente']} ({int(perc)}%)"):
            st.progress(perc / 100)
            for tc in t_comm:
                try:
                    d_s = datetime.strptime(tc['scadenza'], '%Y-%m-%d').date()
                    diff = (d_s - oggi).days
                    if tc['stato'] == 'Completato': icona = "✅ COMPLETATO"
                    elif diff < 0: icona = f"⏰ RITARDO ({abs(diff)} gg)"
                    elif diff <= 2: icona = f"⏳ IN SCADENZA ({diff} gg)"
                    else: icona = f"🟢 OK ({diff} gg)"
                except: icona = "📅 N.D."
                st.write(f"- **{tc.get('assegnato_a')}**: {tc.get('descrizione')} | {icona}")

# ==========================================
# [09] ASSEGNAZIONE
# ==========================================
elif scelta == "🎯 Assegnazione":
    st.header("Nuova Commessa o Task")
    tab1, tab2 = st.tabs(["🆕 Commessa", "📝 Task"])
    with tab1:
        with st.form("f_c"):
            c_cod = st.text_input("Codice Commessa")
            c_cli = st.text_input("Nome Cliente")
            if st.form_submit_button("Crea Commessa"):
                db_insert("commesse", {"codice": c_cod, "cliente": c_cli})
                st.success("Commessa creata!")
    with tab2:
        with st.form("f_t"):
            t_comm = st.selectbox("Commessa", [c['codice'] for c in db_get("commesse")])
            t_desc = st.selectbox("Attività Standard", TASK_STANDARD)
            t_tec = st.selectbox("Tecnico", [u['nome'] for u in db_get("utenti")])
            t_scad = st.date_input("Scadenza")
            if st.form_submit_button("Crea Task"):
                payload = {
                    "commessa_ref": t_comm, "descrizione": t_desc, 
                    "assegnato_a": t_tec, "scadenza": str(t_scad), 
                    "approvato_admin": (ruolo == "Admin"), "stato": "In corso"
                }
                db_insert("task", payload)
                st.success("Richiesta registrata!")

# ==========================================
# [10] APPROVAZIONI (SOLO PER NUOVI TASK PM)
# ==========================================
elif scelta == "⚖️ Approvazioni":
    st.header("Validazione Nuovi Task")
    t_raw = db_get("task")
    da_val = [t for t in t_raw if t.get('approvato_admin') == False]
    if not da_val:
        st.info("Nessun task in attesa di validazione.")
    else:
        for v in da_val:
            st.warning(f"📌 {v['assegnato_a']}: {v['descrizione']} ({v['commessa_ref']})")
            if st.button("✅ APPROVA", key=f"ok_{v['id']}"):
                db_update("task", v['id'], {"approvato_admin": True})
                st.success("Task approvato!")
                st.rerun()
