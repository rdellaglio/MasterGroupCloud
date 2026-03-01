import streamlit as st
import httpx
import smtplib
from email.mime.text import MIMEText
from datetime import date, datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="MasterGroup Cloud", page_icon="🏗️", layout="wide")

URL = st.secrets.get("SUPABASE_URL")
KEY = st.secrets.get("SUPABASE_KEY")
MAIL_USER = st.secrets.get("EMAIL_MITTENTE")
MAIL_PASS = st.secrets.get("EMAIL_PASSWORD")
HEADERS = {
    "apikey": KEY, 
    "Authorization": f"Bearer {KEY}", 
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

# --- FUNZIONI CORE (POTENZIATE) ---
def db_get(tab):
    try:
        # Aggiungiamo un parametro casuale per evitare la cache del browser
        res = httpx.get(f"{URL}/rest/v1/{tab}?select=*&t={datetime.now().timestamp()}", headers=HEADERS, timeout=10)
        return res.json() if res.status_code == 200 else []
    except: return []

def db_update(tab, id_r, pay):
    try:
        with httpx.Client() as client:
            # Usiamo PATCH per aggiornare solo i campi inviati
            return client.patch(f"{URL}/rest/v1/{tab}?id=eq.{id_r}", headers=HEADERS, json=pay)
    except Exception as e:
        st.error(f"Errore connessione: {e}")
        return None

def invia_mail(dest, subj, body):
    if not MAIL_USER or not MAIL_PASS: return
    try:
        msg = MIMEText(body)
        msg['Subject'] = subj
        msg['From'] = MAIL_USER
        msg['To'] = dest
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(MAIL_USER, MAIL_PASS)
            s.sendmail(MAIL_USER, dest, msg.as_string())
    except: pass

# --- LOGIN ---
if "u" not in st.session_state:
    st.title("🏗️ MasterGroup Cloud")
    with st.form("login_form"):
        m = st.text_input("Email").strip().lower()
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Accedi"):
            usrs = db_get("utenti")
            user = next((x for x in usrs if str(x.get('email')).lower() == m and str(x.get('password')) == p), None)
            if user: 
                st.session_state.u = user
                st.rerun()
            else: st.error("Email o Password errati.")
    st.stop()

u = st.session_state.u
nome_u, ruolo_u = u.get('nome'), u.get('ruolo')

# --- SIDEBAR ---
st.sidebar.title(f"👤 {nome_u}")
menu = ["📋 Task"]
if ruolo_u in ["Admin", "PM"]: menu.append("🎯 Assegna")
if ruolo_u == "Admin": menu.append("⚖️ Approvazioni")
scelta = st.sidebar.radio("Naviga", menu)

# --- SEZIONE TASK ---
if scelta == "📋 Task":
    st.header("Gestione Attività")
    ts = db_get("task")
    us = db_get("utenti")
    
    # Se operatore, vede solo i suoi. Se Admin/PM, vede tutti.
    f_t = [t for t in ts if t.get('assegnato_a') == nome_u] if ruolo_u == "Operatore" else ts
    
    for t in f_t:
        with st.expander(f"📌 {t.get('commessa_ref')} - {t.get('descrizione')}"):
            if ruolo_u in ["Admin", "PM"]:
                st.subheader("Modifica Assegnazione")
                l_n = [usr.get('nome') for usr in us]
                nuovo_t = st.selectbox("Cambia Tecnico", l_n, index=l_n.index(t['assegnato_a']) if t['assegnato_a'] in l_n else 0, key=f"sel_{t['id']}")
                
                if st.button("Richiedi Approvazione Modifica", key=f"btn_{t['id']}"):
                    # LOGICA CRUCIALE: Se è PM, approvato_admin deve diventare FALSE (0)
                    is_adm = (ruolo_u == "Admin")
                    res = db_update("task", t['id'], {"assegnato_a": nuovo_t, "approvato_admin": is_adm})
                    
                    if res and res.status_code in [200, 204]:
                        st.success("Richiesta inviata! Ora l'Admin deve approvare.")
                        if not is_adm:
                            invia_mail(MAIL_USER, "Richiesta Modifica", f"Il PM {nome_u} ha cambiato tecnico al task {t['id']}. Vai in Approvazioni.")
                        st.rerun()
                    else:
                        st.error(f"Errore DB: {res.status_code if res else 'No Response'}")

            st.write(f"Stato attuale: **{t.get('stato')}**")

# --- SEZIONE APPROVAZIONI ---
elif scelta == "⚖️ Approvazioni":
    st.header("Validazione Modifiche")
    # Prendiamo TUTTI i task e filtriamo quelli dove approvato_admin NON è True
    t_all = db_get("task")
    da_val = [t for t in t_all if t.get('approvato_admin') != True]
    
    if not da_val:
        st.info("Tutte le modifiche sono state approvate.")
    else:
        for v in da_val:
            st.warning(f"MODIFICA: {v.get('assegnato_a')} su {v.get('descrizione')}")
            if st.button("✅ APPROVA", key=f"ok_{v['id']}"):
                resp = db_update("task", v['id'], {"approvato_admin": True})
                if resp and resp.status_code in [200, 204]:
                    st.success("Approvato!")
                    st.rerun()
                else:
                    st.error("Errore nell'approvazione.")

# --- ASSEGNA ---
elif scelta == "🎯 Assegna":
    st.header("Nuova Assegnazione")
    with st.form("new_task"):
        c_r = st.text_input("Commessa")
        desc = st.text_input("Descrizione")
        chi = st.selectbox("Tecnico", [u['nome'] for u in db_get("utenti")])
        if st.form_submit_button("Crea"):
            # I nuovi task partono come NON APPROVATI se fatti da PM
            db_update("task", "new", {"commessa_ref": c_r, "descrizione": desc, "assegnato_a": chi, "approvato_admin": (ruolo_u == "Admin"), "stato": "In corso"})
            st.success("Creato!")
