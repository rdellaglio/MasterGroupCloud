import streamlit as st
import httpx
import smtplib
from email.mime.text import MIMEText
from datetime import date, datetime

# ==========================================
# [01] CONFIGURAZIONE & BRANDING
# ==========================================
st.set_page_config(page_title="MasterGroup Cloud", page_icon="🏗️", layout="wide")

TASK_STANDARD = [
    "CME (Computo Metrico)", "CILA / SCIA / PdC", "DOCFA (Catasto)", 
    "APE (Energetica)", "Relazione Legge 10", "Sopralluogo / Rilievo",
    "Contabilità (SAL)", "Sicurezza (PSC / POS)", "Pratica ENEA", "Redazione Grafici"
]

URL = st.secrets.get("SUPABASE_URL")
KEY = st.secrets.get("SUPABASE_KEY")
MAIL_USER = st.secrets.get("EMAIL_MITTENTE")
MAIL_PASS = st.secrets.get("EMAIL_PASSWORD")
HEADERS = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

# ==========================================
# [02] FUNZIONI CORE (DB, MAIL, METEO)
# ==========================================
def db_get(tab):
    try:
        # Cache killer per avere dati sempre freschi
        res = httpx.get(f"{URL}/rest/v1/{tab}?select=*&t={datetime.now().timestamp()}", headers=HEADERS, timeout=10)
        return res.json() if res.status_code == 200 else []
    except: return []

def db_update(tab, id_r, pay):
    try:
        with httpx.Client() as client:
            return client.patch(f"{URL}/rest/v1/{tab}?id=eq.{id_r}", headers=HEADERS, json=pay)
    except: return None

def db_insert(tab, pay):
    try:
        with httpx.Client() as client:
            return client.post(f"{URL}/rest/v1/{tab}", headers=HEADERS, json=pay)
    except: return None

def invia_mail(dest, subj, body):
    if not MAIL_USER or not MAIL_PASS: return
    try:
        msg = MIMEText(body)
        msg['Subject'] = subj
        msg['From'] = f"MasterGroup Cloud <{MAIL_USER}>"
        msg['To'] = dest
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(MAIL_USER, MAIL_PASS)
            s.sendmail(MAIL_USER, dest, msg.as_string())
    except: pass

def get_meteo_bari():
    try:
        res = httpx.get("https://api.open-meteo.com/v1/forecast?latitude=41.11&longitude=16.87&current_weather=true").json()
        return f"☀️ Bari: {res['current_weather']['temperature']}°C. Buon lavoro!"
    except: return "🌤️ MasterGroup Cloud pronto."

# ==========================================
# [03] ACCESSO
# ==========================================
if "u" not in st.session_state:
    st.title("🏗️ MasterGroup Cloud")
    with st.form("login_form"):
        m = st.text_input("Email Aziendale").strip().lower()
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Accedi"):
            usrs = db_get("utenti")
            user = next((x for x in usrs if str(x.get('email')).lower() == m and str(x.get('password')) == p), None)
            if user:
                st.session_state.u = user
                st.rerun()
            else: st.error("Credenziali non valide.")
    st.stop()

u = st.session_state.u
nome_u, ruolo_u = u.get('nome'), u.get('ruolo')

# ==========================================
# [04] SIDEBAR & MENU
# ==========================================
st.sidebar.title(f"👤 {nome_u}")
st.sidebar.write(f"Ruolo: **{ruolo_u}**")
st.sidebar.divider()

menu = ["🏠 Dashboard", "📋 Gestione Task"]
if ruolo_u in ["Admin", "PM"]: menu.extend(["📊 Analisi Commesse", "🎯 Assegnazione"])
if ruolo_u == "Admin": menu.append("⚖️ Approvazioni")

scelta = st.sidebar.radio("Navigazione", menu)
if st.sidebar.button("Logout"):
    del st.session_state.u
    st.rerun()

# ==========================================
# [05] DASHBOARD
# ==========================================
if scelta == "🏠 Dashboard":
    st.header(f"Benvenuto nel Cloud, {nome_u}")
    st.info(get_meteo_bari())
    ts = db_get("task")
    miei = [t for t in ts if t.get('assegnato_a') == nome_u and t.get('stato') != 'Completato']
    st.metric("I tuoi Task aperti", len(miei))

# ==========================================
# [06] GESTIONE TASK (FILTRI & MODIFICHE PM)
# ==========================================
elif scelta == "📋 Gestione Task":
    st.header("Monitoraggio Attività")
    ts, us, cs = db_get("task"), db_get("utenti"), db_get("commesse")
    oggi = date.today()

    # Filtri di visualizzazione
    c1, c2, c3 = st.columns(3)
    f_nome = nome_u if ruolo_u == "Operatore" else c1.selectbox("Filtra Tecnico", ["Tutti"] + [usr['nome'] for usr in us])
    f_comm = c2.selectbox("Filtra Commessa", ["Tutte"] + [cm['codice'] for cm in cs])
    f_stato = c3.selectbox("Filtra Stato", ["Tutti", "In corso", "Bloccato", "Completato"])

    # Logica Filtro Dati
    f_t = ts if ruolo_u in ["Admin", "PM"] else [t for t in ts if t.get('assegnato_a') == nome_u]
    if f_nome != "Tutti" and ruolo_u != "Operatore": f_t = [t for t in f_t if t.get('assegnato_a') == f_nome]
    if f_comm != "Tutte": f_t = [t for t in f_t if t.get('commessa_ref') == f_comm]
    if f_stato != "Tutti": f_t = [t for t in f_t if t.get('stato') == f_stato]
    
    f_t.sort(key=lambda x: x.get('scadenza', '9999-12-31'))

    for t in f_t:
        try:
            d_s = datetime.strptime(t['scadenza'], '%Y-%m-%d').date()
            diff = (d_s - oggi).days
            label = f"⏳ {diff}gg" if diff >= 0 else f"⏰ SCADUTO ({abs(diff)}gg)"
        except: label, d_s = "📅 Data n.d.", oggi
        
        pre = "🚨 " if t.get('stato') == 'Bloccato' else ""
        with st.expander(f"{pre}{label} | {t.get('commessa_ref')} - {t.get('descrizione')}"):
            # AREA PM/ADMIN: Riassegnazione
            if ruolo_u in ["Admin", "PM"]:
                st.subheader("🛠️ Modifica parametri task")
                ln = [usr.get('nome') for usr in us]
                nuovo_tec = st.selectbox("Cambia Tecnico", ln, index=ln.index(t['assegnato_a']) if t['assegnato_a'] in ln else 0, key=f"re_{t['id']}")
                nuova_sc = st.date_input("Cambia Scadenza", value=d_s, key=f"dt_{t['id']}")
                if st.button("💾 Salva e Richiedi Approvazione", key=f"sv_{t['id']}"):
                    is_adm = (ruolo_u == "Admin")
                    res = db_update("task", t['id'], {"assegnato_a": nuovo_tec, "scadenza": str(nuova_sc), "approvato_admin": is_adm})
                    if res and res.status_code in [200, 204]:
                        if not is_adm: invia_mail(MAIL_USER, "Richiesta Modifica", f"Anna ha modificato il task {t['id']}.")
                        st.success("Modifica registrata!")
                        st.rerun()

            st.divider()
            # AREA OPERATORE: Stato
            stati = ["In corso", "Completato", "Bloccato"]
            idx_s = stati.index(t.get('stato', 'In corso')) if t.get('stato') in stati else 0
            n_st = st.selectbox("Aggiorna Stato", stati, index=idx_s, key=f"st_{t['id']}")
            if st.button("Conferma Stato", key=f"up_{t['id']}"):
                db_update("task", t['id'], {"stato": n_st})
                st.rerun()

# ==========================================
# [07] ASSEGNAZIONE (TAB RIPRISTINATI)
# ==========================================
elif scelta == "🎯 Assegnazione":
    st.header("Nuova Gestione")
    tab1, tab2 = st.tabs(["🆕 Nuova Commessa", "📝 Nuovo Task"])
    with tab1:
        with st.form("f_c"):
            c_c, c_l = st.text_input("Codice"), st.text_input("Cliente")
            if st.form_submit_button("Crea Commessa"):
                db_insert("commesse", {"codice": c_c, "cliente": c_l})
                st.success("Creata!")
    with tab2:
        with st.form("f_t"):
            c_sel = st.selectbox("Commessa", [c['codice'] for c in db_get("commesse")])
            t_std = st.selectbox("Attività", TASK_STANDARD)
            t_tec = st.selectbox("Tecnico", [u['nome'] for u in db_get("utenti")])
            t_dat = st.date_input("Scadenza")
            if st.form_submit_button("Assegna"):
                db_insert("task", {"commessa_ref": c_sel, "descrizione": t_std, "assegnato_a": t_tec, "scadenza": str(t_dat), "approvato_admin": (ruolo_u == "Admin"), "stato": "In corso"})
                st.success("Task inviato!")

# ==========================================
# [08] ANALISI & APPROVAZIONI
# ==========================================
elif scelta == "📊 Analisi Commesse":
    st.header("Avanzamento Progetti")
    for c in db_get("commesse"):
        tk = [t for t in db_get("task") if t.get('commessa_ref') == c.get('codice')]
        with st.expander(f"📂 {c.get('codice')} - {c.get('cliente')}"):
            for x in tk: st.write(f"- {x.get('assegnato_a')}: {x.get('descrizione')} [{x.get('stato')}]")

elif scelta == "⚖️ Approvazioni":
    st.header("Validazione Modifiche")
    da_val = [t for t in db_get("task") if t.get('approvato_admin') != True]
    u_all = db_get("utenti")
    if not da_val: st.info("Nessuna pendenza.")
    for v in da_val:
        with st.container():
            st.warning(f"📌 {v.get('assegnato_a')}: {v.get('descrizione')} ({v.get('commessa_ref')})")
            if st.button("✅ APPROVA E NOTIFICA", key=f"ok_{v['id']}"):
                db_update("task", v['id'], {"approvato_admin": True})
                # Notifica Mail al Tecnico
                tec = next((u for u in u_all if u.get('nome') == v.get('assegnato_a')), None)
                if tec and tec.get('email'):
                    invia_mail(tec['email'], "[MasterGroup] Task Confermato", f"Il task {v.get('descrizione')} è stato approvato.")
                st.rerun()
