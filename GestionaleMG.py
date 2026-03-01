import streamlit as st
import httpx
import smtplib
from email.mime.text import MIMEText
from datetime import date, datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="MasterGroup Cloud", page_icon="🏗️", layout="wide")

TASK_STANDARD = [
    "CME (Computo Metrico)", "CILA / SCIA / PdC", "DOCFA (Catasto)", 
    "APE (Energetica)", "Relazione Legge 10", "Sopralluogo",
    "Contabilità (SAL)", "Sicurezza (PSC)", "Pratica ENEA", "Grafici"
]

URL = st.secrets.get("SUPABASE_URL")
KEY = st.secrets.get("SUPABASE_KEY")
MAIL_USER = st.secrets.get("EMAIL_MITTENTE")
MAIL_PASS = st.secrets.get("EMAIL_PASSWORD")
HEADERS = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

# --- FUNZIONI CORE ---
def db_get(tab):
    try:
        res = httpx.get(f"{URL}/rest/v1/{tab}?select=*", headers=HEADERS, timeout=10)
        return res.json() if res.status_code == 200 else []
    except: return []

def db_update(tab, id_r, pay):
    with httpx.Client() as client:
        return client.patch(f"{URL}/rest/v1/{tab}?id=eq.{id_r}", headers=HEADERS, json=pay)

def db_insert(tab, pay):
    return httpx.post(f"{URL}/rest/v1/{tab}", headers=HEADERS, json=pay)

def invia_mail(dest, subj, body):
    if not MAIL_USER or not MAIL_PASS: return
    try:
        msg = MIMEText(body)
        msg['Subject'] = subj
        msg['From'] = f"MasterGroup <{MAIL_USER}>"
        msg['To'] = dest
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(MAIL_USER, MAIL_PASS)
            s.sendmail(MAIL_USER, dest, msg.as_string())
    except: pass

# --- LOGIN ---
if "u" not in st.session_state:
    st.title("🏗️ MasterGroup Cloud")
    with st.form("l"):
        m = st.text_input("Email").strip().lower()
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Accedi"):
            usrs = db_get("utenti")
            user = next((x for x in usrs if str(x.get('email')).lower() == m and str(x.get('password')) == p), None)
            if user: st.session_state.u = user; st.rerun()
            else: st.error("Dati errati.")
    st.stop()

u = st.session_state.u
nome_u, ruolo_u = u.get('nome'), u.get('ruolo')

# --- SIDEBAR ---
st.sidebar.title(f"👤 {nome_u}")
menu = ["🏠 Dashboard", "📋 Task"]
if ruolo_u in ["Admin", "PM"]: menu.extend(["📊 Analisi", "🎯 Assegna"])
if ruolo_u == "Admin": menu.append("⚖️ Approvazioni")
scelta = st.sidebar.radio("Naviga", menu)

# --- DASHBOARD ---
if scelta == "🏠 Dashboard":
    st.header(f"MasterGroup - {nome_u}")
    st.write("Seleziona una voce dal menu a sinistra.")

# --- TASK (GESTIONE & MODIFICA) ---
elif scelta == "📋 Task":
    st.header("Gestione Attività")
    ts = db_get("task")
    us = db_get("utenti")
    oggi = date.today()
    
    # Filtro solo per i miei se sono operatore
    f_t = [t for t in ts if t.get('assegnato_a') == nome_u] if ruolo_u == "Operatore" else ts
    f_t.sort(key=lambda x: x.get('scadenza', '9999'))

    for t in f_t:
        with st.expander(f"📌 {t.get('commessa_ref')} - {t.get('descrizione')}"):
            if ruolo_u in ["Admin", "PM"]:
                st.subheader("🛠️ Modifica (Richiede OK Admin)")
                l_n = [usr.get('nome') for usr in us]
                nuovo_t = st.selectbox("Cambia Tecnico", l_n, index=l_n.index(t['assegnato_a']) if t['assegnato_a'] in l_n else 0, key=f"n_{t['id']}")
                if st.button("💾 Salva e Richiedi Approvazione", key=f"s_{t['id']}"):
                    # Se sono PM, approvato_admin DIVENTA FALSE
                    res = db_update("task", t['id'], {"assegnato_a": nuovo_t, "approvato_admin": (ruolo_u == "Admin")})
                    if res.status_code in [200, 204]:
                        st.success("Richiesta inviata!")
                        st.rerun()
                    else: st.error(f"Errore DB: {res.status_code}")
            
            st.divider()
            st_val = ["In corso", "Completato", "Bloccato"]
            nuovo_s = st.selectbox("Stato", st_val, index=st_val.index(t.get('stato','In corso')) if t.get('stato') in st_val else 0, key=f"st_{t['id']}")
            if st.button("Aggiorna", key=f"up_{t['id']}"):
                db_update("task", t['id'], {"stato": nuovo_s})
                st.rerun()

# --- ANALISI ---
elif scelta == "📊 Analisi":
    st.header("Avanzamento")
    for c in db_get("commesse"):
        tasks = [t for t in db_get("task") if t.get('commessa_ref') == c.get('codice')]
        with st.expander(f"📂 {c['codice']}"):
            for tc in tasks:
                st.write(f"- {tc.get('assegnato_a')}: {tc.get('descrizione')} | {tc.get('stato')}")

# --- ASSEGNA ---
elif scelta == "🎯 Assegna":
    st.header("Nuova Assegnazione")
    with st.form("a"):
        c_r = st.selectbox("Commessa", [c['codice'] for c in db_get("commesse")])
        desc = st.selectbox("Attività", TASK_STANDARD)
        chi = st.selectbox("Tecnico", [u['nome'] for u in db_get("utenti")])
        scad = st.date_input("Scadenza")
        if st.form_submit_button("Invia"):
            db_insert("task", {"commessa_ref": c_r, "descrizione": desc, "assegnato_a": chi, "scadenza": str(scad), "approvato_admin": (ruolo_u == "Admin"), "stato": "In corso"})
            st.success("Task inviato!")

# --- APPROVAZIONI ---
elif scelta == "⚖️ Approvazioni":
    st.header("Validazione")
    # PRENDIAMO TUTTO CIÒ CHE NON È TRUE
    da_val = [t for t in db_get("task") if t.get('approvato_admin') != True]
    if not da_val: st.info("Tutto approvato.")
    for v in da_val:
        st.warning(f"Richiesta: {v.get('assegnato_a')} - {v.get('descrizione')}")
        if st.button("APPROVA", key=f"ok_{v['id']}"):
            db_update("task", v['id'], {"approvato_admin": True})
            # Notifica mail al tecnico
            tec = next((usr for usr in db_get("utenti") if usr['nome'] == v['assegnato_a']), None)
            if tec and tec.get('email'):
                invia_mail(tec['email'], "Nuovo Task", "Il tuo task è stato approvato.")
            st.rerun()
