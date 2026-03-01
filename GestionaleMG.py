import streamlit as st
import httpx
import smtplib
from email.mime.text import MIMEText
from datetime import date, datetime

# --- [01] CONFIGURAZIONE & BRANDING ---
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

# --- [02] FUNZIONI DB (CON RESET CACHE) ---
def db_get(tab):
    try:
        # Il timestamp serve a forzare il database a darci dati nuovi ogni volta
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
        msg['From'] = f"MasterGroup <{MAIL_USER}>"
        msg['To'] = dest
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(MAIL_USER, MAIL_PASS)
            s.sendmail(MAIL_USER, dest, msg.as_string())
    except: pass

# --- [03] LOGIN ---
if "u" not in st.session_state:
    st.title("🏗️ MasterGroup Cloud")
    with st.form("l"):
        m = st.text_input("Email").strip().lower()
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Accedi"):
            usrs = db_get("utenti")
            user = next((x for x in usrs if str(x.get('email')).lower() == m and str(x.get('password')) == p), None)
            if user: st.session_state.u = user; st.rerun()
            else: st.error("Credenziali errate.")
    st.stop()

u = st.session_state.u
nome_u, ruolo_u = u.get('nome'), u.get('ruolo')

# --- [04] SIDEBAR ---
st.sidebar.title(f"👤 {nome_u}")
st.sidebar.write(f"Ruolo: **{ruolo_u}**")
menu = ["🏠 Dashboard", "📋 Gestione Task"]
if ruolo_u in ["Admin", "PM"]: menu.extend(["📊 Analisi", "🎯 Assegnazione"])
if ruolo_u == "Admin": menu.append("⚖️ Approvazioni")
scelta = st.sidebar.radio("Naviga", menu)

if st.sidebar.button("Logout"):
    del st.session_state.u
    st.rerun()

# --- [05] GESTIONE TASK (VISIBILITÀ PM RIPRISTINATA) ---
if scelta == "📋 Gestione Task":
    st.header("Monitoraggio Attività")
    ts, us, cs = db_get("task"), db_get("utenti"), db_get("commesse")
    oggi = date.today()

    # Logica Filtro: L'operatore vede solo i suoi, Admin e PM vedono tutto
    f_t = ts if ruolo_u in ["Admin", "PM"] else [t for t in ts if t.get('assegnato_a') == nome_u]
    f_t.sort(key=lambda x: x.get('scadenza', '9999-12-31'))

    for t in f_t:
        try:
            d_s = datetime.strptime(t['scadenza'], '%Y-%m-%d').date()
            diff = (d_s - oggi).days
            label = f"⏳ {diff}gg" if diff >= 0 else f"⏰ SCADUTO ({abs(diff)}gg)"
        except: label, d_s = "📅 Data n.d.", oggi
        
        with st.expander(f"{label} | {t.get('commessa_ref')} - {t.get('descrizione')}"):
            # Sezione per Admin e PM: Modifica e Riassegnazione
            if ruolo_u in ["Admin", "PM"]:
                st.subheader("🛠️ Modifica parametri")
                l_nomi = [usr.get('nome') for usr in us]
                nuovo_tec = st.selectbox("Cambia Tecnico", l_nomi, index=l_nomi.index(t['assegnato_a']) if t['assegnato_a'] in l_nomi else 0, key=f"tec_{t['id']}")
                nuova_scad = st.date_input("Cambia Scadenza", value=d_s, key=f"dat_{t['id']}")
                
                if st.button("Salva e Richiedi Approvazione", key=f"sav_{t['id']}"):
                    is_adm = (ruolo_u == "Admin")
                    res = db_update("task", t['id'], {"assegnato_a": nuovo_tec, "scadenza": str(nuova_scad), "approvato_admin": is_adm})
                    if res and res.status_code in [200, 204]:
                        if not is_adm:
                            invia_mail(MAIL_USER, "[MG] Richiesta Modifica", f"Il PM {nome_u} ha modificato il task {t['id']}.")
                            st.info("Inviato a Raffaele per l'OK finale.")
                        else: st.success("Modifica applicata.")
                        st.rerun()

            st.divider()
            # Sezione per Operatore: Aggiornamento Stato
            stati = ["In corso", "Completato", "Bloccato"]
            cur_st = t.get('stato', 'In corso')
            idx_s = stati.index(cur_st) if cur_st in stati else 0
            n_st = st.selectbox("Stato", stati, index=idx_s, key=f"st_{t['id']}")
            if st.button("Aggiorna Stato", key=f"upd_{t['id']}"):
                db_update("task", t['id'], {"stato": n_st})
                st.rerun()

# --- [06] ASSEGNAZIONE (TAB RIPRISTINATI) ---
elif scelta == "🎯 Assegnazione":
    st.header("Nuova Commessa o Task")
    t1, t2 = st.tabs(["🆕 Commessa", "📝 Task"])
    with t1:
        with st.form("fc"):
            c_c = st.text_input("Codice Commessa")
            c_l = st.text_input("Cliente")
            if st.form_submit_button("Crea Progetto"):
                db_insert("commesse", {"codice": c_c, "cliente": c_l})
                st.success("Commessa creata!")
    with t2:
        with st.form("ft"):
            c_list = [c['codice'] for c in db_get("commesse")]
            t_c = st.selectbox("Commessa", c_list)
            t_d = st.selectbox("Attività", TASK_STANDARD)
            t_n = st.selectbox("Tecnico", [u['nome'] for u in db_get("utenti")])
            t_s = st.date_input("Scadenza")
            if st.form_submit_button("Assegna"):
                db_insert("task", {"commessa_ref": t_c, "descrizione": t_d, "assegnato_a": t_n, "scadenza": str(t_s), "approvato_admin": (ruolo_u == "Admin"), "stato": "In corso"})
                st.success("Richiesta inviata!")

# --- [07] APPROVAZIONI ---
elif scelta == "⚖️ Approvazioni":
    st.header("Validazione Modifiche Admin")
    tasks = db_get("task")
    # Mostra tutto ciò che NON è approvato
    da_val = [t for t in tasks if t.get('approvato_admin') != True]
    
    if not da_val:
        st.info("Nessuna pendenza.")
    else:
        for v in da_val:
            st.warning(f"📌 {v.get('assegnato_a')}: {v.get('descrizione')} ({v.get('commessa_ref')})")
            if st.button("APPROVA", key=f"ok_{v['id']}"):
                db_update("task", v['id'], {"approvato_admin": True})
                st.rerun()

elif scelta == "📊 Analisi":
    st.header("Avanzamento Progetti")
    for c in db_get("commesse"):
        st.subheader(f"📂 {c.get('codice')}")
        tk = [t for t in db_get("task") if t.get('commessa_ref') == c.get('codice')]
        for x in tk: st.write(f"- {x.get('assegnato_a')}: {x.get('descrizione')} [{x.get('stato')}]")

else: # Dashboard
    st.header(f"Benvenuto {nome_u}")
    st.write("Usa il menu laterale per gestire il lavoro.")
