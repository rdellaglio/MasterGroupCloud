import streamlit as st
import httpx
import smtplib
from email.mime.text import MIMEText
from datetime import date, datetime

# --- CONFIGURAZIONE & TASK STANDARD ---
st.set_page_config(page_title="MasterGroup Cloud", page_icon="🏗️", layout="wide")

TASK_STANDARD = [
    "CME (Computo Metrico Estimativo)", "CILA / SCIA / PdC", "DOCFA (Variazione Catastale)", 
    "APE (Attestato Energetico)", "Relazione Legge 10", "Sopralluogo / Rilievo",
    "Contabilità (SAL)", "Sicurezza (PSC / POS)", "Pratica ENEA", "Redazione Elaborati Grafici"
]

# --- MOTORE EMAIL ---
def invia_notifica_email(destinatario, oggetto, task_info):
    try:
        mittente = st.secrets["EMAIL_MITTENTE"]
        password = st.secrets["EMAIL_PASSWORD"]
        
        corpo = f"""
        🤖 MESSAGGIO AUTOMATICO MASTERGROUP CLOUD
        
        Ciao, ti è stato assegnato o approvato un nuovo task:
        
        📌 ATTIVITÀ: {task_info['descrizione']}
        📂 COMMESSA: {task_info['commessa_ref']}
        📅 SCADENZA: {task_info['scadenza']}
        
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
    except Exception as e:
        st.error(f"Errore invio mail: {e}")
        return False

# --- MOTORE DATABASE (SUPABASE) ---
URL = st.secrets.get("SUPABASE_URL", "https://clauyljovenkcqemswfk.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "tua_chiave_qui")
headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

def db_get(tabella):
    return httpx.get(f"{URL}/rest/v1/{tabella}?select=*", headers=headers).json()

def db_update(tabella, id_riga, payload):
    return httpx.patch(f"{URL}/rest/v1/{tabella}?id=eq.{id_riga}", headers=headers, json=payload)

def db_insert(tabella, payload):
    return httpx.post(f"{URL}/rest/v1/{tabella}", headers=headers, json=payload)

# --- LOGIN ---
if "u" not in st.session_state:
    st.title("🏗️ MasterGroup Cloud")
    with st.form("login"):
        mail = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Accedi"):
            users = db_get("utenti")
            user = next((x for x in users if x['email']==mail and x['password']==pwd), None)
            if user:
                st.session_state.u = user
                st.rerun()
    st.stop()

u = st.session_state.u
st.sidebar.title(f"👤 {u['nome']}")
menu = ["📊 Monitoraggio", "🎯 Assegnazione", "📋 I miei Task"]
if u['ruolo'] == "Admin": menu.append("⚖️ Approvazioni")
scelta = st.sidebar.radio("Naviga", menu)

# --- 1. MONITORAGGIO AVANZAMENTO ---
if scelta == "📊 Monitoraggio":
    st.header("Avanzamento Progetti")
    commesse = db_get("commesse")
    tasks = db_get("task")
    oggi = date.today()

    for c in commesse:
        t_c = [t for t in tasks if t['commessa_ref'] == c['codice']]
        with st.expander(f"📂 {c['codice']} - {c['cliente']}"):
            for tc in t_c:
                dt = datetime.strptime(tc['scadenza'], '%Y-%m-%d').date()
                diff = (dt - oggi).days
                
                # Logica icone e messaggi richiesta
                if tc['stato'] == 'Completato': status = "✅ OK"
                elif diff < 0: status = f"⏰ RITARDO ({abs(diff)} gg)"
                elif diff <= 2: status = f"⏳ IN SCADENZA ({diff} gg)"
                else: status = f"🟢 OK ({diff} gg)"
                
                st.write(f"**{tc['assegnato_a']}**: {tc['descrizione']} | Scadenza: {tc['scadenza']} | {status}")

# --- 2. ASSEGNAZIONE TASK ---
elif scelta == "🎯 Assegnazione":
    st.header("Nuovo Task")
    with st.form("new_task"):
        comm = st.selectbox("Commessa", [c['codice'] for c in db_get("commesse")])
        tipo = st.selectbox("Attività Standard", TASK_STANDARD)
        note = st.text_input("Note specifiche")
        tecnico = st.selectbox("Assegna a", [usr['nome'] for usr in db_get("utenti")])
        scad = st.date_input("Scadenza")
        if st.form_submit_button("Crea Task"):
            payload = {
                "commessa_ref": comm, 
                "descrizione": f"{tipo}: {note}", 
                "assegnato_a": tecnico, 
                "scadenza": str(scad),
                "stato": "In corso",
                "approvato_admin": (u['ruolo'] == "Admin") # Auto-approvato se lo fai tu
            }
            db_insert("task", payload)
            st.success("Task creato!")

# --- 3. APPROVAZIONI (FIXED) ---
elif scelta == "⚖️ Approvazioni":
    st.header("Task in attesa di validazione")
    da_approvare = [t for t in db_get("task") if t.get('approvato_admin') == False]
    utenti = db_get("utenti")

    if not da_approvare:
        st.info("Tutto in ordine! Nessun task da approvare.")
    else:
        for t in da_approvare:
            col1, col2 = st.columns([4, 1])
            col1.write(f"📌 **{t['assegnato_a']}**: {t['descrizione']} (Scadenza: {t['scadenza']})")
            if col2.button("✅ APPROVA", key=f"app_{t['id']}"):
                # Update DB
                db_update("task", t['id'], {"approvato_admin": True})
                # Notifica Mail
                tecnico_info = next((usr for usr in utenti if usr['nome'] == t['assegnato_a']), None)
                if tecnico_info and tecnico_info.get('email'):
                    invia_notifica_email(tecnico_info['email'], "Nuovo Task MasterGroup", t)
                st.success("Approvato e Notificato!")
                st.rerun()
