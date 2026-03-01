import streamlit as st
import httpx
import smtplib
from email.mime.text import MIMEText
from datetime import date, datetime

# ==========================================
# [01] CONFIGURAZIONE & BRANDING
# ==========================================
st.set_page_config(page_title="MasterGroup Cloud", page_icon="🏗️", layout="wide")

# Elenco Attività Standard Blindato
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
# [02] RECUPERO SEGRETI & CONNESSIONE
# ==========================================
URL = st.secrets.get("SUPABASE_URL")
KEY = st.secrets.get("SUPABASE_KEY")
MAIL_USER = st.secrets.get("EMAIL_MITTENTE")
MAIL_PASS = st.secrets.get("EMAIL_PASSWORD")

if not URL or not KEY:
    st.error("⚠️ Chiavi SUPABASE mancanti nei Secrets!")
    st.stop()

HEADERS = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

# ==========================================
# [03] MOTORE FUNZIONI (DB, MAIL, METEO)
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
    except Exception as e: st.error(f"Errore mail: {e}")

def get_meteo_bari():
    try:
        res = httpx.get("https://api.open-meteo.com/v1/forecast?latitude=41.11&longitude=16.87&current_weather=true").json()
        temp = res["current_weather"]["temperature"]
        return f"☀️ Bari: {temp}°C. Buon lavoro al team MasterGroup!"
    except: return "🌤️ MasterGroup Cloud pronto."

# ==========================================
# [04] GESTIONE ACCESSO
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
# [05] SIDEBAR
# ==========================================
try: st.sidebar.image("LogoMG.png", use_container_width=True)
except: st.sidebar.title("MasterGroup")

st.sidebar.write(f"👤 **{nome_u}** ({ruolo})")
st.sidebar.divider()

menu = ["🏠 Dashboard", "📋 Gestione Task"]
if ruolo in ["Admin", "PM"]: menu.extend(["📊 Analisi Commesse", "🎯 Assegnazione"])
if ruolo == "Admin": menu.append("⚖️ Approvazioni")

scelta = st.sidebar.radio("Navigazione", menu, key="main_nav")
if st.sidebar.button("Logout"):
    del st.session_state.u
    st.rerun()

# ==========================================
# [06] DASHBOARD
# ==========================================
if scelta == "🏠 Dashboard":
    st.header(f"Benvenuto, {nome_u}")
    st.info(get_meteo_bari())
    ts = db_get("task")
    miei = [t for t in ts if t.get('assegnato_a') == nome_u and t.get('stato') != 'Completato']
    st.metric("I tuoi Task aperti", len(miei))

# ==========================================
# [07] GESTIONE TASK (OPERATIVITÀ & RIASSEGNAZIONE)
# ==========================================
elif scelta == "📋 Gestione Task":
    st.header("Monitoraggio Attività")
    ts, cs, us = db_get("task"), db_get("commesse"), db_get("utenti")
    oggi = date.today()

    c1, c2, c3 = st.columns(3)
    f_nome = nome_u if ruolo == "Operatore" else c1.selectbox("Tecnico", ["Tutti"] + [usr['nome'] for usr in us])
    f_comm = c2.selectbox("Commessa", ["Tutte"] + [cm['codice'] for cm in cs])
    f_stato = c3.selectbox("Stato", ["Tutti", "In corso", "Bloccato", "Completato"])

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
        except: label = "📅 Data n.d."
        
        prefix = "🚨 " if t.get('stato') == 'Bloccato' else ""
        with st.expander(f"{prefix}{label} | {t.get('commessa_ref')} - {t.get('descrizione')}"):
            
            # SEZIONE ADMIN/PM: Riassegnazione e Modifiche (Blocco Rev 01.1)
            if ruolo in ["Admin", "PM"]:
                st.subheader("Modifica parametri task")
                col_te, col_pr, col_sc = st.columns(3)
                
                # Liste per i menu
                lista_nomi = [usr.get('nome') for usr in us]
                idx_tec = lista_nomi.index(t.get('assegnato_a')) if t.get('assegnato_a') in lista_nomi else 0
                
                nuovo_tec = col_te.selectbox("Riassegna a", lista_nomi, index=idx_tec, key=f"re_{t['id']}")
                nuova_prio = col_pr.selectbox("Priorità", ["Bassa", "Media", "Alta"], index=["Bassa", "Media", "Alta"].index(t.get('priorita','Media')), key=f"rp_{t['id']}")
                nuova_scad = col_sc.date_input("Cambia Scadenza", value=d_scad, key=f"rs_{t['id']}")
                
                if st.button("Salva e Richiedi Approvazione", key=f"btn_mod_{t['id']}"):
                    is_admin = (ruolo == "Admin")
                    
                    # Aggiornamento Database
                    db_update("task", t['id'], {
                        "assegnato_a": nuovo_tec, 
                        "priorita": nuova_prio, 
                        "scadenza": str(nuova_scad),
                        "approvato_admin": is_admin  # Se PM, diventa False (va in Approvazioni)
                    })
                    
                    # Notifica Email all'Admin se la modifica è di un PM
                    if not is_admin:
                        corpo_avviso = f"""
                        🏗️ RICHIESTA MODIFICA TASK
                        L'utente {nome_u} (PM) ha modificato un task:
                        
                        Task: {t.get('descrizione')}
                        Nuovo Operatore: {nuovo_tec}
                        Nuova Scadenza: {nuova_scad}
                        
                        Accedi alla sezione 'Approvazioni' per validare.
                        """
                        invia_mail(st.secrets["EMAIL_MITTENTE"], f"[MasterGroup] Modifica da approvare - {t.get('commessa_ref')}", corpo_avviso)
                        st.info("Richiesta inviata all'Admin per validazione.")
                    else:
                        st.success("Modifica applicata e confermata.")
                    
                    st.rerun()
            # SEZIONE OPERATORE: Stato
            nuovo_st = st.selectbox("Aggiorna Stato", ["In corso", "Completato", "Bloccato"], index=["In corso", "Completato", "Bloccato"].index(t.get('stato', 'In corso')), key=f"st_{t['id']}")
            nota = st.text_area("Nota blocco", value=t.get('motivo_blocco', ''), key=f"nt_{t['id']}") if nuovo_st == "Bloccato" else ""
            if st.button("Aggiorna Stato Operativo", key=f"btn_st_{t['id']}"):
                db_update("task", t['id'], {"stato": nuovo_st, "motivo_blocco": nota})
                st.rerun()

# ==========================================
# [08] ANALISI COMMESSE (ICONE)
# ==========================================
elif scelta == "📊 Analisi Commesse":
    st.header("Avanzamento Progetti")
    cs, ts, oggi = db_get("commesse"), db_get("task"), date.today()

    for c in cs:
        t_comm = [t for t in ts if t.get('commessa_ref') == c.get('codice')]
        perc = (len([t for t in t_comm if t['stato'] == 'Completato']) / len(t_comm) * 100) if t_comm else 0
        with st.expander(f"📂 {c['codice']} - {c['cliente']} ({int(perc)}%)"):
            st.progress(perc / 100)
            for tc in t_comm:
                try:
                    d_s = datetime.strptime(tc['scadenza'], '%Y-%m-%d').date()
                    diff = (d_s - oggi).days
                    if tc['stato'] == 'Completato': status = "✅ COMPLETATO"
                    elif diff < 0: status = f"⏰ RITARDO ({abs(diff)} gg)"
                    elif diff <= 2: status = f"⏳ IN SCADENZA ({diff} gg)"
                    else: status = f"🟢 OK ({diff} gg)"
                except: status = "📅 N.D."
                blocco = "🛑 BLOCCATO!" if tc.get('stato') == 'Bloccato' else ""
                st.write(f"- **{tc.get('assegnato_a')}**: {tc.get('descrizione')} | Scadenza: {tc['scadenza']} | {status} {blocco}")

# ==========================================
# [09] ASSEGNAZIONE (TAB RIPRISTINATI)
# ==========================================
elif scelta == "🎯 Assegnazione":
    st.header("Gestione Commesse e Task")
    tab1, tab2 = st.tabs(["🆕 Nuova Commessa", "📝 Nuovo Task"])
    
    with tab1:
        with st.form("f_nuova_comm"):
            c1, c2 = st.columns(2)
            nc_cod = c1.text_input("Codice Commessa")
            nc_cli = c1.text_input("Nome Cliente")
            ut_all = db_get("utenti")
            nc_pm = c2.selectbox("PM Responsabile", [u['nome'] for u in ut_all if u['ruolo'] in ['Admin', 'PM']])
            nc_scad = c2.date_input("Scadenza Commessa")
            if st.form_submit_button("Crea Progetto"):
                db_insert("commesse", {"codice": nc_cod, "cliente": nc_cli, "pm_assegnato": nc_pm, "scadenza": str(nc_scad)})
                st.success("Commessa creata!")

    with tab2:
        with st.form("f_nuovo_task"):
            c_list = db_get("commesse")
            nt_comm = st.selectbox("Seleziona Progetto", [c['codice'] for c in c_list])
            nt_tipo = st.selectbox("Attività Standard", TASK_STANDARD)
            nt_note = st.text_input("Specifiche attività")
            nt_tec = st.selectbox("Assegna a Tecnico", [u['nome'] for u in db_get("utenti")])
            nt_scad = st.date_input("Data Consegna")
            if st.form_submit_button("Assegna Task"):
                payload = {
                    "commessa_ref": nt_comm, 
                    "descrizione": f"{nt_tipo}: {nt_note}", 
                    "assegnato_a": nt_tec, 
                    "scadenza": str(nt_scad), 
                    "stato": "In corso", 
                    "approvato_admin": (ruolo == "Admin")
                }
                db_insert("task", payload)
                st.success("Task registrato!")

# ==========================================
# [10] APPROVAZIONI
# ==========================================
elif scelta == "⚖️ Approvazioni":
    st.header("Task e Modifiche da Validare")
    # Leggiamo tutti i task e filtriamo quelli NON approvati
    tutto_db = db_get("task")
    da_val = [t for t in tutto_db if t.get('approvato_admin') == False]
    
    us = db_get("utenti")
    if not da_val: 
        st.info("Nessuna pendenza. Tutti i task sono stati validati.")
    else:
        st.write(f"Ci sono {len(da_val)} attività che richiedono il tuo OK:")
        for v in da_val:
            with st.container():
                st.markdown("---")
                c_tx, c_bt = st.columns([4, 1])
                # Specifichiamo meglio cosa stiamo approvando
                info_task = f"📌 **{v.get('assegnato_a')}**: {v.get('descrizione')} \n\n SCADENZA: {v.get('scadenza')} | COMMESSA: {v.get('commessa_ref')}"
                c_tx.warning(info_task)
                
                if c_bt.button("✅ VALIDA MODIFICA", key=f"ok_{v['id']}"):
                    # Azione 1: Riporta approvato_admin a True
                    successo = db_update("task", v['id'], {"approvato_admin": True})
                    
                    # Azione 2: Notifica il tecnico del nuovo incarico
                    t_info = next((usr for usr in us if usr['nome'] == v['assegnato_a']), None)
                    if t_info and t_info.get('email'):
                        corpo = f"Ciao {v['assegnato_a']},\nIl task '{v['descrizione']}' è stato confermato dall'Admin.\nPuoi procedere con il lavoro."
                        invia_mail(t_info['email'], "[MasterGroup] Task Confermato", corpo)
                    
                    st.success("Task validato correttamente!")
                    st.rerun()


