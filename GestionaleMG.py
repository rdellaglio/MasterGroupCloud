import streamlit as st
import httpx
from datetime import date
import random

# ==========================================
# [01_CONFIGURAZIONE & ICONA]
# ==========================================
# Impostiamo l'icona CANTIERE 🏗️ come richiesto
st.set_page_config(page_title="MasterGroup Cloud 🏗️", layout="wide")

URL = "https://clauyljovenkcqemswfk.supabase.co"
KEY = "sb_publishable_WetwA7q8dmctM2a-VDBfTg_M46vnFi0"
headers = {
    "apikey": KEY, 
    "Authorization": f"Bearer {KEY}", 
    "Content-Type": "application/json"
}

# ==========================================
# [02_LIBRERIA CITAZIONI & LOGICA IA]
# ==========================================
CITAZIONI = [
    {"testo": "L'architettura è un cristallo.", "autore": "Gio Ponti"},
    {"testo": "Dio è nei dettagli.", "autore": "Mies van der Rohe"},
    {"testo": "L'architettura deve commuovere. La costruzione è per tener su.", "autore": "Le Corbusier"},
    {"testo": "Il modo migliore per predire il futuro è progettarlo.", "autore": "B. Fuller"},
    {"testo": "Usate la matita come se fosse una spada.", "autore": "Franco Albini"},
    {"testo": "La bellezza è l'armonia tra le parti.", "autore": "Leon Battista Alberti"},
    {"testo": "Non si può pensare un'architettura senza pensare alla gente.", "autore": "Richard Rogers"},
    {"testo": "L'architettura è il gioco sapiente, rigoroso e magnifico dei volumi sotto la luce.", "autore": "Le Corbusier"},
    {"testo": "Meno è più (Less is more).", "autore": "Mies van der Rohe"},
    {"testo": "La forma segue la funzione.", "autore": "Louis Sullivan"}
]

def saluto_dinamico_ia(nome, task_chiusi):
    giorno_sett = date.today().strftime("%A")
    diz_giorni = {
        "Monday": "Lunedì", "Tuesday": "Martedì", "Wednesday": "Mercoledì", 
        "Thursday": "Giovedì", "Friday": "Venerdì", "Saturday": "Sabato", "Sunday": "Domenica"
    }
    giorno_it = diz_giorni.get(giorno_sett, giorno_sett)
    
    msg = f"Buongiorno {nome}, felice {giorno_it}! "
    
    if task_chiusi > 10:
        msg += f"🚀 Lo studio sta volando: abbiamo già {task_chiusi} attività completate in archivio!"
    elif task_chiusi > 0:
        msg += f"🔥 Ottimo ritmo, abbiamo smarcato {task_chiusi} task con successo recentemente."
    else:
        msg += "☕ Caffè in mano? È il momento perfetto per tracciare nuove linee di progetto."
    
    msg += " Oggi a Bari il clima è ideale per costruire il futuro di MasterGroup."
    return msg

# ==========================================
# [03_MOTORE_CLOUD]
# ==========================================
def leggi_tabella(tabella):
    try:
        with httpx.Client() as client:
            res = client.get(f"{URL}/rest/v1/{tabella}?select=*", headers=headers)
            return res.json()
    except: return []

def leggi_task_filtrati(nome_utente):
    try:
        with httpx.Client() as client:
            res = client.get(f"{URL}/rest/v1/task?assegnato_a=eq.{nome_utente}", headers=headers)
            return res.json()
    except: return []

def scrivi_dati(tabella, dati_json):
    try:
        with httpx.Client() as client:
            res = client.post(f"{URL}/rest/v1/{tabella}", headers=headers, json=dati_json)
            return res
    except: return None

def aggiorna_stato_db(id_task, nuovo_stato, nota_blocco=""):
    try:
        payload = {"stato": nuovo_stato, "motivo_blocco": nota_blocco}
        with httpx.Client() as client:
            res = client.patch(f"{URL}/rest/v1/task?id=eq.{id_task}", headers=headers, json=payload)
            return res.status_code
    except: return 500

# ==========================================
# [04_LOGICA_ACCESSO]
# ==========================================
st.title("🏗️ MasterGroup in Cloud")
st.markdown("---")

utenti_db = leggi_tabella("utenti")
ATTIVITA_STANDARD = [
    "Sopralluogo e Rilievo Strumentale", "Redazione Elaborati Grafici",
    "Pratica Edilizia (CILA/SCIA/PdC)", "Pratica Catastale (DOCFA)",
    "APE (Prestazione Energetica)", "Direzione Lavori", "Contabilità Lavori", "Altro..."
]

if not utenti_db:
    st.error("⚠️ Connessione al Cloud fallita. Controlla le chiavi API.")
else:
    nomi_utenti = [u['nome'] for u in utenti_db]
    utente_loggato = st.sidebar.selectbox("Accedi come:", nomi_utenti, key="main_login")
    info_u = next(u for u in utenti_db if u['nome'] == utente_loggato)
    ruolo = info_u['ruolo']
    
    st.sidebar.info(f"👤 **{utente_loggato}**\n\n🔑 Ruolo: **{ruolo}**")
    
    menu = ["🏠 Dashboard", "📋 I Miei Task"]
    if ruolo in ["Admin", "PM"]:
        menu.extend(["🏗️ Nuova Commessa", "🎯 Assegna Lavoro"])
    scelta = st.sidebar.radio("Navigazione:", menu)

    # ==========================================
    # [05_DASHBOARD DINAMICA]
    # ==========================================
    if scelta == "🏠 Dashboard":
        t_db = leggi_tabella("task")
        chiusi = len([t for t in t_db if t.get('stato') == 'Completato']) if t_db else 0
        
        # 🟢 MESSAGGIO IA DINAMICO
        st.info(saluto_dinamico_ia(utente_loggato, chiusi))
        
        # 📜 CITAZIONE RANDOM
        cit = random.choice(CITAZIONI)
        st.subheader("💡 Il pensiero del Maestro")
        st.markdown(f"> *\"{cit['testo']}\"* — **{cit['autore']}**")
        
        st.divider()
        
        # METRICHE REALI
        c_db = leggi_tabella("commesse")
        col1, col2, col3 = st.columns(3)
        col1.metric("Progetti Attivi", len(c_db) if c_db else 0)
        col2.metric("Lavori Chiusi", chiusi)
        col3.metric("Stato Server", "✅ Online")

    # ==========================================
    # [06_MODULO_COMMESSE]
    # ==========================================
    elif scelta == "🏗️ Nuova Commessa":
        st.header("Apertura Nuova Pratica")
        with st.form("f_c", clear_on_submit=True):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                cod = st.text_input("Codice Commessa")
                cli = st.text_input("Cliente")
            with col_c2:
                bud = st.number_input("Budget (€)", min_value=0.0)
                scad_c = st.date_input("Scadenza Contrattuale")
            if st.form_submit_button("Registra Progetto"):
                scrivi_dati("commesse", {"codice": cod, "cliente": cli, "budget": bud, "scadenza": str(scad_c)})
                st.success("Progetto registrato con successo!")

    # ==========================================
    # [07_MODULO_TASK]
    # ==========================================
    elif scelta == "🎯 Assegna Lavoro":
        st.header("Distribuzione Attività")
        comm_db = leggi_tabella("commesse")
        codici = [c['codice'] for c in comm_db] if comm_db else ["Nessuna commessa"]
        
        default_idx = 0
        if "ultimo_progetto" in st.session_state and st.session_state.ultimo_progetto in codici:
            default_idx = codici.index(st.session_state.ultimo_progetto)

        with st.form("f_t", clear_on_submit=False):
            sel_c = st.selectbox("Progetto", codici, index=default_idx)
            att = st.selectbox("Attività", ATTIVITA_STANDARD)
            chi = st.selectbox("Tecnico", nomi_utenti)
            prio = st.select_slider("Priorità", options=["Bassa", "Media", "Alta"])
            scad_t = st.date_input("Scadenza Task")
            
            if st.form_submit_button("Invia Task"):
                st.session_state.ultimo_progetto = sel_c
                res = scrivi_dati("task", {
                    "commessa_ref": sel_c, "descrizione": att, "assegnato_a": chi, 
                    "priorita": prio, "scadenza": str(scad_t),
                    "approvato_admin": True if ruolo == "Admin" else False,
                    "stato": "In corso"
                })
                if res: st.success(f"Task assegnato a {chi}!")

    # ==========================================
    # [08_MODULO_OPERATORE]
    # ==========================================
    elif scelta == "📋 I Miei Task":
        st.header(f"📅 Scrivania di {utente_loggato}")
        tutti_task = leggi_task_filtrati(utente_loggato)
        
        if not tutti_task:
            st.info("Nessun compito assegnato al momento.")
        else:
            task_attivi = [t for t in tutti_task if t['stato'] != 'Completato']
            task_finiti = [t for t in tutti_task if t['stato'] == 'Completato']

            for t in task_attivi:
                with st.expander(f"📁 PROGETTO: {t.get('commessa_ref', 'N.D.')} | 📍 {t['descrizione']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nuovo_st = st.selectbox("Stato", ["In corso", "Completato", "Bloccato"], 
                                               index=["In corso", "Completato", "Bloccato"].index(t['stato']) if t['stato'] in ["In corso", "Completato", "Bloccato"] else 0,
                                               key=f"st_{t['id']}")
                    
                    if nuovo_st == "Bloccato":
                        nota = st.text_area("Nota blocco:", value=t.get('motivo_blocco', ""), key=f"nt_{t['id']}")
                    else: nota = ""

                    if st.button("💾 AGGIORNA", key=f"btn_{t['id']}"):
                        if aggiorna_stato_db(t['id'], nuovo_st, nota) in [200, 204]:
                            st.success("Aggiornato!")
                            st.rerun()

            st.divider()
            with st.expander("📜 Archivio Storico"):
                for f in task_finiti:
                    st.write(f"✅ **{f.get('commessa_ref', 'N.D.')}**: {f['descrizione']}")