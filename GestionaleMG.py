import streamlit as st
import httpx
import smtplib
from email.mime.text import MIMEText
from datetime import date, datetime

# --- [01] CONFIGURAZIONE & BRANDING ---
st.set_page_config(page_title="MasterGroup Cloud", page_icon="🏗️", layout="wide")

TASK_STANDARD = [
    "CME (Computo Metrico Estimativo)", "CILA / SCIA / PdC", "DOCFA (Variazione Catastale)", 
    "APE (Attestato Energetico)", "Relazione Legge 10", "Sopralluogo / Rilievo",
    "Contabilità (SAL)", "Sicurezza (PSC / POS)", "Pratica ENEA", "Redazione Elaborati Grafici"
]

# --- [02] MOTORE EMAIL ---
def invia_notifica_email(destinatario, oggetto, task_info):
    try:
        mittente = st.secrets.get("EMAIL_MITTENTE")
        password = st.secrets.get("EMAIL_PASSWORD")
        if not mittente or not password: return False
        
        corpo = f"""
        🤖 MESSAGGIO AUTOMATICO MASTERGROUP CLOUD
        
        Ciao, ti è stato assegnato o approvato un nuovo task:
        
        📌 ATTIVITÀ: {task_info.get('descrizione', 'N/D')}
        📂 COMMESSA: {task_info.get('commessa_ref', 'N/D')}
        📅 SCADENZA: {task_info.get('scadenza', 'N/D')}
        
        Accedi al gestionale per i dettagli. Buon lavoro!
        """
        msg = MIMEText(corpo)
        msg['Subject'] = oggetto
        msg['From'] = f"MasterGroup Cloud <{mittente}>"
        msg['To'] = destinatario

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(mittente, password)
            server.sendmail(mittente, destinatario, msg.as_string())
        return True
    except: return False

# --- [03] MOTORE DATABASE ---
URL = st.secrets.get("SUPABASE_URL")
KEY = st.secrets.get("SUPABASE_KEY")
headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

def db_get(tabella):
    try:
        res = httpx.get(f"{URL}/rest/v1/{tabella}?select=*", headers=headers)
        return res.json() if res.status_code == 200 else []
    except: return []

def db_update(tabella, id_riga, payload):
    return httpx.patch(f"{URL}/rest/v1/{tabella}?id=eq.{id_riga}", headers=headers, json=payload)

def db_insert(tabella, payload):
    return httpx.post(f"{URL}/rest/v1/{tabella}", headers=headers, json=payload)

# --- [04] GESTIONE ACCESSO ---
if "u" not in st.session_state:
    st.title("🏗️ MasterGroup Cloud")
    with st.form("login"):
        mail = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Accedi"):
            users = db_get("utenti")
            user = next((x for x in users if x.get('email')==mail and x.get('password')==pwd), None)
            if user:
                st.session_state.u = user
                st.rerun()
            else: st.error("Email o Password errati.")
    st.stop()

u = st.session_state.u
st.sidebar.title(f"👤 {u['nome']}")
menu = ["📊 Monitoraggio", "🎯 Assegnazione", "📋 I miei Task"]
if u['ruolo'] == "Admin": menu.append("⚖️ Approvazioni")
scelta = st.sidebar.radio("Menu", menu, key="nav_menu")

if st.sidebar.button("Logout"):
    del st.session_state.u
    st.rerun()

# --- [05] MONITORAGGIO (CON FIX SICUREZZA) ---
if scelta == "📊 Monitoraggio":
    st.header("Avanzamento Progetti")
    commesse = db_get("commesse")
    tasks = db_get("task")
    oggi = date.today()

    for c in commesse:
        # FIX: Filtriamo solo task che hanno una commessa_ref valida
        t_c = [t for t in tasks if t.get('commessa_ref') == c.get('codice')]
        
        with st.expander(f"📂 {c.get('codice')} - {c.get('cliente')}"):
            if not t_c: st.write("Nessun task assegnato.")
            for tc in t_c:
                try:
                    dt = datetime.strptime(tc['scadenza'], '%Y-%m-%d').date()
                    diff = (dt - oggi).days
                    if tc['stato'] == 'Completato': status = "✅ OK"
                    elif diff < 0: status = f"⏰ RITARDO ({abs(diff)} gg)"
                    elif diff <= 2: status = f"⏳ IN SCADENZA ({diff} gg)"
                    else: status = f"🟢 OK ({diff} gg)"
                except: status = "📅 Data non valida"
                
                blocco = "🛑 BLOCCATO!" if tc.get('stato') == 'Bloccato' else ""
                st.write(f"**{tc.get('assegnato_a')}**: {tc.get('descrizione')} | {status} {blocco}")

# --- [06] ASSEGNAZIONE ---
elif scelta == "🎯 Assegnazione":
    st.header("Nuovo Task")
    comm_list = [c.get('codice') for c in db_get("commesse") if c.get('codice')]
    user_list = [usr.get('nome') for usr in db_get("utenti") if usr.get('nome')]
    
    with st.form("new_task"):
        comm = st.selectbox("Commessa", comm_list)
        tipo = st.selectbox("Attività Standard", TASK_STANDARD)
        note = st.text_input("Note specifiche")
        tecnico = st.selectbox("Assegna a", user_list)
        scad = st.date_input("Scadenza")
        if st.form_submit_button("Crea Task"):
            payload = {
                "commessa_ref": comm, 
                "descrizione": f"{tipo}: {note}", 
                "assegnato_a": tecnico, 
                "scadenza": str(scad),
                "stato": "In corso",
                "approvato_admin": (u['ruolo'] == "Admin")
            }
            db_insert("task", payload)
            st.success("Task creato con successo!")

# --- [07] APPROVAZIONI (FIXED & TESTED) ---
elif scelta == "⚖️ Approvazioni":
    st.header("Task in attesa di validazione")
    all_tasks = db_get("task")
    # Filtriamo task non approvati ignorando record rotti
    da_approvare = [t for t in all_tasks if t.get('approvato_admin') == False and t.get('id')]
    utenti = db_get("utenti")

    if not da_approvare:
        st.info("Nessun task da approvare.")
    else:
        for t in da_approvare:
            with st.container():
                col1, col2 = st.columns([4, 1])
                col1.warning(f"📌 **{t.get('assegnato_a')}**: {t.get('descrizione')} (Scadenza: {t.get('scadenza')})")
                if col2.button("✅ APPROVA", key=f"app_{t['id']}"):
                    db_update("task", t['id'], {"approvato_admin": True})
                    # Notifica Email
                    tecnico_info = next((usr for usr in utenti if usr.get('nome') == t.get('assegnato_a')), None)
                    if tecnico_info and tecnico_info.get('email'):
                        invia_notifica_email(tecnico_info['email'], "Nuovo Task MasterGroup", t)
                    st.rerun()
