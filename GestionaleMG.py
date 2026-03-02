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
# --- [01.A] STILE GRAFICO MASTERGROUP ---
st.markdown("""
    <style>
    /* 1. Sfondo generale e Font */
    [data-testid="stAppViewContainer"] {
        background-color: #fcfcfc;
    }
    
    /* 2. Titoli Blu MasterGroup */
    h1, h2, h3 { 
        color: #003366 !important; 
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 700;
    }
    
    /* 3. Sidebar (Barra Laterale) più elegante */
    [data-testid="stSidebar"] {
        background-color: #f0f2f6;
        border-right: 2px solid #003366;
    }
    
    /* 4. Pulsanti arrotondati e professionali */
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        border: 2px solid #003366;
        color: #003366;
        background-color: white;
        font-weight: bold;
        padding: 0.5rem;
    }
    .stButton>button:hover {
        background-color: #003366;
        color: white;
        border: 2px solid #003366;
    }
    
    /* 5. Contenitori Task (Expander) */
    .streamlit-expanderHeader {
        background-color: white !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 12px !important;
        padding: 10px !important;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    
    /* 6. Tabelle e Metriche */
    [data-testid="stMetricValue"] {
        color: #003366;
        font-size: 1.8rem;
    }
    </style>
""", unsafe_allow_html=True)
TASK_STANDARD = [
    "--- 1. AMMINISTRAZIONE ---",
    "Contratto e Incarico Professionale",
    "Preventivo e Computo Preliminare",
    "Pratiche Detrazioni Fiscali",
    "--- 2. RILIEVI E DIAGNOSI ---",
    "Sopralluogo e Rilievo Architettonico",
    "Rilievo Materico e del Degrado",
    "Indagini Tecniche e Strutturali",
    "--- 3. PROGETTAZIONE E GRAFICA ---",
    "Elaborati Stato di Fatto",
    "Progetto di Variante (Giallo/Rossi)",
    "Progetto Esecutivo / Stato di Progetto",
    "Rendering e Fotoinserimenti",
    "--- 4. IMPIANTI ---",
    "Relazione Energetica (Legge 10)",
    "Progetto Impianto Idrico-Sanitario",
    "Progetto Impianto Elettrico / Domotico",
    "Progetto VMC e Climatizzazione",
    "--- 5. PRATICHE E AUTORIZZAZIONI ---",
    "Pratica Edilizia (CILA/SCIA/PdC)",
    "Pratica Sismica (Genio Civile)",
    "Autorizzazione Paesaggistica / Soprintendenza",
    "Variazione Catastale (DOCFA)",
    "Segnalazione Certificata Agibilità (SCA)",
    "Attestato di Prestazione Energetica (APE)",
    "--- 6. CANTIERE E CHIUSURA ---",
    "Direzione Lavori",
    "Coordinamento Sicurezza (PSC/POS)",
    "Contabilità Lavori (SAL/Libretto)",
    "Collaudo e Fine Lavori",
    "--- 7. EXTRA ---",
    "Altro (Specifica nel campo personalizzato...)"
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
# [06] GESTIONE TASK (OPERATIVITÀ & PRIORITÀ) REV 01.08
# ==========================================
elif scelta == "📋 Gestione Task":
    st.header("Monitoraggio Attività")
    ts, cs, us = db_get("task"), db_get("commesse"), db_get("utenti")
    oggi = date.today()

    # --- FILTRI INCROCIATI ---
    f1, f2, f3, f4 = st.columns(4)
    
    # Filtro Tecnico: Solo Admin e PM scelgono, Operatore vede solo i suoi
    if ruolo in ["Admin", "PM"]:
        sel_tec = f1.selectbox("Filtra Tecnico", ["Tutti"] + [usr.get('nome') for usr in us])
    else:
        sel_tec = nome_u
        f1.write(f"**Tecnico:** {nome_u}")

    sel_com = f2.selectbox("Filtra Commessa", ["Tutte"] + [cm.get('codice') for cm in cs])
    sel_sta = f3.selectbox("Filtra Stato", ["In corso", "Bloccato", "Completato", "Tutti"], index=0)
    mostra_chiusi = f4.checkbox("Mostra Completati", value=False)

    # --- LOGICA FILTRO ---
    f_t = ts
    # 1. Filtro Tecnico
    if sel_tec != "Tutti": 
        f_t = [t for t in f_t if t.get('assegnato_a') == sel_tec]
    # 2. Filtro Commessa
    if sel_com != "Tutte": 
        f_t = [t for t in f_t if t.get('commessa_ref') == sel_com]
    # 3. Filtro Stato e Chiusi
    if not mostra_chiusi:
        f_t = [t for t in f_t if t.get('stato') != 'Completato']
    elif sel_sta != "Tutti":
        f_t = [t for t in f_t if t.get('stato') == sel_sta]

    # --- ORDINAMENTO CRONOLOGICO (Scaduti e Imminenti prima) ---
    def calcola_priorita(task):
        try:
            d = date.fromisoformat(task.get('scadenza'))
            return d
        except:
            return date(9999, 12, 31)

    f_t.sort(key=calcola_priorita)

    # --- VISUALIZZAZIONE TASK ---
    if not f_t:
        st.info("Nessun task trovato con questi filtri.")
    
    for t in f_t:
        try:
            d_scad = date.fromisoformat(t['scadenza'])
            diff = (d_scad - oggi).days
            if t.get('stato') == 'Completato':
                icona, label = "✅", "COMPLETATO"
            elif diff < 0:
                icona, label = "⏰", f"SCADUTO ({abs(diff)}gg)"
            elif diff <= 3:
                icona, label = "⏳", f"IMMINENTE ({diff}gg)"
            else:
                icona, label = "📅", f"In scadenza tra {diff}gg"
        except:
            icona, label = "❓", "Data non definita"

        titolo_expander = f"{icona} {label} | {t.get('commessa_ref')} - {t.get('descrizione')}"
        
        with st.expander(titolo_expander):
            st.write(f"**Assegnato a:** {t.get('assegnato_a')}")
            
            # 🛠️ RIASSEGNAZIONE (SOLO ADMIN)
            if ruolo == "Admin":
                st.divider()
                st.subheader("🛠️ Modifica Avanzata (Admin)")
                l_nomi = [usr.get('nome') for usr in us]
                idx_u = l_nomi.index(t['assegnato_a']) if t['assegnato_a'] in l_nomi else 0
                
                c_u, c_d = st.columns(2)
                nuovo_u = c_u.selectbox("Cambia Tecnico", l_nomi, index=idx_u, key=f"re_{t['id']}")
                nuova_d = c_d.date_input("Cambia Scadenza", value=d_scad, key=f"sc_{t['id']}")
                
                if st.button("Salva modifiche Admin", key=f"btn_adm_{t['id']}"):
                    db_update("task", t['id'], {"assegnato_a": nuovo_u, "scadenza": str(nuova_d)})
                    st.success("Task aggiornato!")
                    st.rerun()

            st.divider()
            
            # 📈 AGGIORNAMENTO STATO (PER TUTTI)
            st.subheader("📈 Aggiorna Stato")
            stati_lista = ["In corso", "Bloccato", "Completato"]
            idx_s = stati_lista.index(t['stato']) if t['stato'] in stati_lista else 0
            n_stato = st.selectbox("Nuovo Stato", stati_lista, index=idx_s, key=f"st_{t['id']}")
            
            if st.button("Conferma Cambio Stato", key=f"up_{t['id']}"):
                db_update("task", t['id'], {"stato": n_stato})
                st.success("Stato aggiornato!")
                st.rerun()
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
# [08] ASSEGNAZIONE (REV 01.11 - CON MEMORIA)
# ==========================================
elif scelta == "🎯 Assegnazione":
    st.header("Pianificazione Nuove Attività")
    ts, cs, us = db_get("task"), db_get("commesse"), db_get("utenti")
    
    # Inizializzazione Memoria (Session State) se vuota
    if "last_comm" not in st.session_state: st.session_state.last_comm = None
    if "last_tec" not in st.session_state: st.session_state.last_tec = None
    if "last_desc" not in st.session_state: st.session_state.last_desc = None
    if "last_date" not in st.session_state: st.session_state.last_date = date.today()

    tab1, tab2 = st.tabs(["🆕 Nuova Commessa", "📝 Nuovo Task"])
    
   # --- TAB 1: CREAZIONE COMMESSA (REV 01.13) ---
    with tab1:
        with st.form("form_nuova_commessa", clear_on_submit=True):
            st.subheader("Anagrafica Progetto")
            c1, c2 = st.columns(2)
            cod_c = c1.text_input("Codice Commessa")
            cli_c = c2.text_input("Cliente")
            
            c3, c4 = st.columns(2)
            bud_c = c3.number_input("Budget Previsto (€)", min_value=0.0, step=500.0)
            scad_c = c4.date_input("Scadenza Globale Commessa", value=date.today())
            
            # --- SELEZIONE PM (Filtro per Ruolo) ---
            # Filtriamo gli utenti qualificati come PM o Admin dall'elenco 'us' caricato a inizio sezione
            elenco_pm = [usr.get('nome') for usr in us if usr.get('ruolo') in ['PM', 'Admin']]
            sel_pm = st.selectbox("Seleziona PM Responsabile", elenco_pm)
            
            if st.form_submit_button("Crea Commessa"):
                if cod_c and cli_c:
                    payload_c = {
                        "codice": cod_c, 
                        "cliente": cli_c, 
                        "budget": bud_c, 
                        "scadenza": str(scad_c),
                        "pm_assegnato": sel_pm  # Nome colonna corretto del tuo DB
                    }
                    res_c = db_insert("commesse", payload_c)
                    if res_c.status_code in [200, 201]:
                        st.success(f"✅ Commessa {cod_c} creata e affidata a {sel_pm}!")
                        st.rerun()
                    else:
                        st.error(f"Errore DB: {res_c.status_code}. Verifica la tabella 'commesse'.")
                else:
                    st.warning("Codice e Cliente sono obbligatori.")
    # --- TAB 2: CREAZIONE TASK (CON MEMORIA) ---
    with tab2:
        if not cs:
            st.warning("⚠️ Crea prima una commessa.")
        else:
            with st.form("form_nuovo_task"):
                st.subheader("Dettaglio Attività")
                
                # Liste per indici
                l_comms = [c['codice'] for c in cs]
                l_tecnici = [usr.get('nome') for usr in us]
                
                # Recupero Indici dalla memoria
                idx_c = l_comms.index(st.session_state.last_comm) if st.session_state.last_comm in l_comms else 0
                idx_t = l_tecnici.index(st.session_state.last_tec) if st.session_state.last_tec in l_tecnici else 0
                idx_d = TASK_STANDARD.index(st.session_state.last_desc) if st.session_state.last_desc in TASK_STANDARD else 0

                t_comm_ref = st.selectbox("Seleziona Commessa", l_comms, index=idx_c)
                t_desc = st.selectbox("Tipo Attività", TASK_STANDARD, index=idx_d)
                t_tec = st.selectbox("Assegna Tecnico", l_tecnici, index=idx_t)
                t_scad_task = st.date_input("Data Scadenza Task", value=st.session_state.last_date)
                
                if st.form_submit_button("Invia Task"):
                    # Salvataggio in memoria per il prossimo task
                    st.session_state.last_comm = t_comm_ref
                    st.session_state.last_tec = t_tec
                    st.session_state.last_desc = t_desc
                    st.session_state.last_date = t_scad_task

                    # Controllo Alert Scadenza
                    scad_max_str = next((c['scadenza'] for c in cs if c['codice'] == t_comm_ref), None)
                    alert_mostra = False
                    if scad_max_str:
                        try:
                            if t_scad_task > date.fromisoformat(scad_max_str): alert_mostra = True
                        except: pass
                    
                    # Inserimento
                    res_t = db_insert("task", {"commessa_ref": t_comm_ref, "descrizione": t_desc, "assegnato_a": t_tec, "scadenza": str(t_scad_task), "stato": "In corso"})
                    
                    if res_t.status_code in [200, 201]:
                        if alert_mostra:
                            st.warning(f"⚠️ Task creato, ma supera la fine commessa ({scad_max_str})!")
                        else:
                            st.success(f"✅ Task assegnato a {t_tec}!")
                        st.rerun() # Ricarica per mostrare i valori salvati
                    else:
                        st.error("Errore creazione task.")




