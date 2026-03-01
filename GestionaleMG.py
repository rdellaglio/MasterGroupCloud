import streamlit as st
import httpx
import smtplib
from email.mime.text import MIMEText
from datetime import date, datetime
# REV 01.05
# ==========================================
# [01] CONFIGURAZIONE & BRANDING
# ==========================================
st.set_page_config(page_title="MasterGroup Cloud", page_icon="🏗️", layout="wide")

TASK_STANDARD = [
    "CME (Computo Metrico Estimativo)", "CILA / SCIA / PdC", "DOCFA (Variazione Catastale)", 
    "APE (Attestato Energetico)", "Relazione Legge 10", "Sopralluogo / Rilievo",
    "Contabilità (SAL)", "Sicurezza (PSC / POS)", "Pratica ENEA", "Redazione Elaborati Grafici"
]

# ==========================================
# [02] CONNESSIONE DATABASE (DATI DIRETTI)
# ==========================================
URL = st.secrets.get("SUPABASE_URL")
KEY = st.secrets.get("SUPABASE_KEY")
HEADERS = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

def db_get(tabella):
    try:
        res = httpx.get(f"{URL}/rest/v1/{tabella}?select=*", headers=HEADERS, timeout=10)
        return res.json() if res.status_code == 200 else []
    except: return []

def db_update(tabella, id_riga, payload):
    return httpx.patch(f"{URL}/rest/v1/{tabella}?id=eq.{id_riga}", headers=HEADERS, json=payload)

def db_insert(tabella, payload):
    return httpx.post(f"{URL}/rest/v1/{tabella}", headers=HEADERS, json=payload)

# ==========================================
# [03] ACCESSO (LOGIN)
# ==========================================
if "u" not in st.session_state:
    st.title("🏗️ MasterGroup Cloud")
    with st.form("login"):
        m = st.text_input("Email").strip().lower()
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
st.sidebar.write(f"👤 **{nome_u}**")
st.sidebar.divider()

menu = ["🏠 Dashboard", "📋 Gestione Task"]
if ruolo in ["Admin", "PM"]: menu.extend(["📊 Analisi Commesse", "🎯 Assegnazione"])

scelta = st.sidebar.radio("Navigazione", menu)
if st.sidebar.button("Logout"):
    del st.session_state.u
    st.rerun()

# ==========================================
# [05] DASHBOARD (REV 01.07)
# ==========================================
if scelta == "🏠 Dashboard":
    st.header(f"Ciao {nome_u}, bentornato/a in Studio")
    
    # 1. Meteo Bari
    try:
        res_m = httpx.get("https://api.open-meteo.com/v1/forecast?latitude=41.11&longitude=16.87&current_weather=true").json()
        temp = res_m["current_weather"]["temperature"]
        st.info(f"☀️ Bari: {temp}°C. Una splendida giornata per progettare!")
    except:
        st.info("🌤️ MasterGroup Cloud pronto all'azione.")

    # 2. Recupero Dati per Task e Scadenze
    ts = db_get("task")
    oggi = date.today()
    
    # Task aperti del singolo utente
    miei_aperti = [t for t in ts if t.get('assegnato_a') == nome_u and t.get('stato') != 'Completato']
    
    # Calcolo scadenze imminenti (entro 3 giorni)
    imminenti = 0
    for t in miei_aperti:
        try:
            d_scad = date.fromisoformat(t['scadenza'])
            if 0 <= (d_scad - oggi).days <= 3:
                imminenti += 1
        except: pass

    # 3. Visualizzazione Metriche
    col1, col2, col3 = st.columns(3)
    col1.metric("I tuoi Task aperti", len(miei_aperti))
    col2.metric("Scadenze imminenti (3gg)", imminenti, delta_color="inverse" if imminenti > 0 else "normal")
    
    if ruolo == "Admin":
        cs = db_get("commesse")
        tot_b = sum(float(c.get('budget', 0)) for c in cs)
        col3.metric("Budget Totale Commesse", f"€ {tot_b:,.2f}")

    st.divider()

    # 4. Frase Motivazionale Generativa (Logica interna)
    import random
    citazioni = [
        f"Forza {nome_u}, ogni grande progetto inizia con un piccolo passo.",
        f"L'eccellenza non è un atto, ma un'abitudine. Buon lavoro, {nome_u}!",
        "Il design è l'anima di ogni creazione umana. Rendila straordinaria oggi.",
        f"Ehi {nome_u}, la precisione è la chiave di un buon ingegnere.",
        "Le sfide di oggi sono i successi di domani. MasterGroup conta su di te!"
    ]
    st.markdown(f"**💡 Pensiero del giorno:** *{random.choice(citazioni)}*")

# ==========================================
# [06] GESTIONE TASK
# ==========================================
elif scelta == "📋 Gestione Task":
    st.header("Monitoraggio Attività")
    ts, cs, us = db_get("task"), db_get("commesse"), db_get("utenti")
    oggi = date.today()

    f1, f2, f3 = st.columns(3)
    s_tec = nome_u if ruolo == "Operatore" else f1.selectbox("Tecnico", ["Tutti"] + [usr.get('nome') for usr in us])
    s_com = f2.selectbox("Commessa", ["Tutte"] + [cm.get('codice') for cm in cs])
    s_sta = f3.selectbox("Stato", ["Tutti", "In corso", "Bloccato", "Completato"])

    f_t = ts
    if s_tec != "Tutti" and ruolo != "Operatore": f_t = [t for t in f_t if t.get('assegnato_a') == s_tec]
    elif ruolo == "Operatore": f_t = [t for t in f_t if t.get('assegnato_a') == nome_u]
    if s_com != "Tutte": f_t = [t for t in f_t if t.get('commessa_ref') == s_com]
    if s_sta != "Tutti": f_t = [t for t in f_t if t.get('stato') == s_sta]
    
    for t in f_t:
        with st.expander(f"📌 {t.get('commessa_ref')} - {t.get('descrizione')} ({t.get('stato')})"):
            # MODIFICA SOLO PER ADMIN
            if ruolo == "Admin":
                st.subheader("🛠️ Modifica Task")
                l_utenti = [usr.get('nome') for usr in us]
                n_tec = st.selectbox("Riassegna a", l_utenti, index=l_utenti.index(t['assegnato_a']) if t['assegnato_a'] in l_utenti else 0, key=f"te_{t['id']}")
                n_sca = st.date_input("Nuova Scadenza", value=date.fromisoformat(t['scadenza']) if t.get('scadenza') else oggi, key=f"sc_{t['id']}")
                if st.button("Salva Modifiche", key=f"bt_{t['id']}"):
                    db_update("task", t['id'], {"assegnato_a": n_tec, "scadenza": str(n_sca)})
                    st.success("Aggiornato!"); st.rerun()
            
            st.divider()
            # AGGIORNAMENTO STATO PER TUTTI
            n_st = st.selectbox("Cambia Stato", ["In corso", "Completato", "Bloccato"], key=f"st_{t['id']}")
            if st.button("Aggiorna Stato", key=f"up_{t['id']}"):
                db_update("task", t['id'], {"stato": n_st})
                st.success("Stato salvato!"); st.rerun()

# ==========================================
# [07] ANALISI COMMESSE
# ==========================================
elif scelta == "📊 Analisi Commesse":
    st.header("Avanzamento Progetti")
    cs, ts = db_get("commesse"), db_get("task")
    for c in cs:
        t_comm = [t for t in ts if t.get('commessa_ref') == c.get('codice')]
        chiusi = len([t for t in t_comm if t['stato'] == 'Completato'])
        perc = (chiusi / len(t_comm) * 100) if t_comm else 0
        with st.expander(f"📂 {c['codice']} - {c['cliente']} ({int(perc)}%)"):
            if ruolo == "Admin": st.write(f"💰 Budget: **€ {c.get('budget', 0)}**")
            st.progress(perc / 100)
            for tc in t_comm:
                st.write(f"- {tc.get('assegnato_a')}: {tc.get('descrizione')} [{tc.get('stato')}]")

# ==========================================
# [08] ASSEGNAZIONE
# ==========================================
elif scelta == "🎯 Assegnazione":
    st.header("Nuova Gestione")
    tab1, tab2 = st.tabs(["🆕 Nuova Commessa", "📝 Nuovo Task"])
    with tab1:
        with st.form("c"):
            c1, c2, c3 = st.text_input("Codice"), st.text_input("Cliente"), st.number_input("Budget (€)", min_value=0)
            if st.form_submit_button("Crea"):
                db_insert("commesse", {"codice": c1, "cliente": c2, "budget": c3})
                st.success("Creata!"); st.rerun()
    with tab2:
        with st.form("t"):
            t1 = st.selectbox("Commessa", [c['codice'] for c in db_get("commesse")])
            t2 = st.selectbox("Attività", TASK_STANDARD)
            t3 = st.selectbox("Tecnico", [u['nome'] for u in db_get("utenti")])
            t4 = st.date_input("Scadenza")
            if st.form_submit_button("Assegna"):
                db_insert("task", {"commessa_ref": t1, "descrizione": t2, "assegnato_a": t3, "scadenza": str(t4), "stato": "In corso"})
                st.success("Assegnato!"); st.rerun()

