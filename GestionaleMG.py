import streamlit as st
import httpx
import smtplib
from email.mime.text import MIMEText
from datetime import date, datetime

# --- [01] CONFIGURAZIONE ---
st.set_page_config(page_title="MasterGroup Cloud", page_icon="🏗️", layout="wide")

# --- [02] MOTORE DATABASE (CON DIAGNOSTICA) ---
# Recupero forzato dei segreti
URL = st.secrets.get("SUPABASE_URL")
KEY = st.secrets.get("SUPABASE_KEY")
headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

def db_get(tabella):
    try:
        with httpx.Client() as client:
            res = client.get(f"{URL}/rest/v1/{tabella}?select=*", headers=headers, timeout=10.0)
            if res.status_code == 200:
                return res.json()
            else:
                st.error(f"Errore Database ({tabella}): Stato {res.status_code}")
                return []
    except Exception as e:
        st.error(f"Errore di connessione al Cloud: {e}")
        return []

# --- [03] SISTEMA DI LOGIN RINFORZATO ---
if "u" not in st.session_state:
    st.title("🏗️ MasterGroup Cloud")
    st.subheader("Accesso Utente")
    
    with st.form("login_form"):
        mail_input = st.text_input("Inserisci la tua Email Aziendale").strip().lower()
        pwd_input = st.text_input("Inserisci la Password", type="password")
        submit = st.form_submit_button("Accedi al Sistema")
        
        if submit:
            with st.spinner("Verifica credenziali in corso..."):
                lista_utenti = db_get("utenti")
                
                if not lista_utenti:
                    st.error("❌ Impossibile leggere la tabella utenti. Controlla la connessione Supabase.")
                else:
                    # Cerchiamo l'utente ignorando maiuscole/minuscole nell'email
                    user = next((x for x in lista_utenti if str(x.get('email')).lower() == mail_input and str(x.get('password')) == pwd_input), None)
                    
                    if user:
                        st.session_state.u = user
                        st.success(f"Benvenuto {user.get('nome')}!")
                        st.rerun()
                    else:
                        st.error("❌ Email o Password non riconosciute. Verifica i dati su Supabase.")
    st.stop()

# --- [04] SEZIONE DOPO IL LOGIN (MENU E FUNZIONI) ---
u = st.session_state.u
nome_u = u.get('nome', 'Utente')
ruolo_u = u.get('ruolo', 'Operatore')

st.sidebar.title(f"👤 {nome_u}")
st.sidebar.write(f"Ruolo: **{ruolo_u}**")

# Definizione Menu
menu = ["📊 Monitoraggio", "🎯 Assegnazione", "📋 I miei Task"]
if ruolo_u == "Admin":
    menu.append("⚖️ Approvazioni")

scelta = st.sidebar.radio("Vai a:", menu, key="nav_main")

if st.sidebar.button("Esci dal sistema"):
    del st.session_state.u
    st.rerun()

# --- [05] LOGICA MONITORAGGIO ---
if scelta == "📊 Monitoraggio":
    st.header("Avanzamento Progetti")
    commesse = db_get("commesse")
    tasks = db_get("task")
    oggi = date.today()

    for c in commesse:
        cod_c = c.get('codice')
        t_c = [t for t in tasks if t.get('commessa_ref') == cod_c]
        
        with st.expander(f"📂 {cod_c} - {c.get('cliente', 'N/D')}"):
            if not t_c:
                st.write("Nessuna attività pianificata.")
            for tc in t_c:
                # Calcolo icone scadenza
                try:
                    dt = datetime.strptime(tc.get('scadenza'), '%Y-%m-%d').date()
                    diff = (dt - oggi).days
                    if tc.get('stato') == 'Completato': status = "✅ OK"
                    elif diff < 0: status = f"⏰ RITARDO ({abs(diff)} gg)"
                    elif diff <= 2: status = f"⏳ IN SCADENZA ({diff} gg)"
                    else: status = f"🟢 OK ({diff} gg)"
                except:
                    status = "📅 Data n.d."
                
                st.write(f"**{tc.get('assegnato_a')}**: {tc.get('descrizione')} | {status}")

# (Qui seguono gli altri moduli: Assegnazione, I miei Task, Approvazioni...)
# Per brevità riutilizza la logica corretta dell'ultimo messaggio per le email
