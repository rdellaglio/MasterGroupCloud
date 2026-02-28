import streamlit as st
import httpx
from datetime import date
import random

# ==========================================
# [01_CONFIGURAZIONE & SECRETS]
# ==========================================
st.set_page_config(page_title="MasterGroup Cloud 🏗️", layout="wide")

# Recupero chiavi dai Secrets (o valori di default per test locale)
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    URL = "https://clauyljovenkcqemswfk.supabase.co"
    KEY = "sb_publishable_WetwA7q8dmctM2a-VDBfTg_M46vnFi0"

headers = {
    "apikey": KEY, 
    "Authorization": f"Bearer {KEY}", 
    "Content-Type": "application/json"
}

ATTIVITA_STANDARD = [
    "Sopralluogo e Rilievo Strumentale", "Redazione Elaborati Grafici",
    "Pratica Edilizia (CILA/SCIA/PdC)", "Pratica Catastale (DOCFA)",
    "APE (Prestazione Energetica)", "Direzione Lavori", "Contabilità Lavori", "Altro..."
]

# ==========================================
# [02_MOTORE_CLOUD]
# ==========================================
def leggi_tabella(tabella):
    try:
        with httpx.Client() as client:
            res = client.get(f"{URL}/rest/v1/{tabella}?select=*", headers=headers)
            return res.json()
    except: return []

def scrivi_dati(tabella, dati_json):
    try:
        with httpx.Client() as client:
            res = client.post(f"{URL}/rest/v1/{tabella}", headers=headers, json=dati_json)
            return res
    except: return None

def aggiorna_db(tabella, id_riga, payload):
    try:
        with httpx.Client() as client:
            return client.patch(f"{URL}/rest/v1/{tabella}?id=eq.{id_riga}", headers=headers, json=payload)
    except: return None

# ==========================================
# [03_LOGICA DI AUTENTICAZIONE]
# ==========================================
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False
    st.session_state.u = None

if not st.session_state.autenticato:
    st.title("🏗️ MasterGroup in Cloud")
    st.subheader("Accesso Area Riservata")
    with st.form("login_form"):
        email_in = st.text_input("Email Aziendale")
        pass_in = st.text_input("Password", type="password")
        if st.form_submit_button("Accedi"):
            utenti = leggi_tabella("utenti")
            user = next((u for u in utenti if u.get('email') == email_in and u.get('password') == pass_in), None)
            if user:
                st.session_state.autenticato = True
                st.session_state.u = user
                st.rerun()
            else:
                st.error("Credenziali non valide.")
    st.stop()

# --- DATI UTENTE LOGGATO ---
u_log = st.session_state.u
nome_u = u_log['nome']
ruolo_u = u_log['ruolo']

# ==========================================
# [04_SIDEBAR & NAVIGAZIONE]
# ==========================================
st.sidebar.title("🏗️ MasterGroup")
st.sidebar.info(f"👤 **{nome_u}**\n\n🔑 Ruolo: **{ruolo_u}**")

menu = ["🏠 Dashboard", "📋 Gestione Task"]
if ruolo_u in ["Admin", "PM"]:
    menu.extend(["🏗️ Nuova Commessa", "🎯 Assegna Lavoro"])
if ruolo_u == "Admin":
    menu.append("⚖️ Approvazioni")

scelta = st.sidebar.radio("Vai a:", menu)

if st.sidebar.button("Esci (Logout)"):
    st.session_state.autenticato = False
    st.rerun()

# ==========================================
# [05_DASHBOARD & CRITICITÀ]
# ==========================================
if scelta == "🏠 Dashboard":
    st.header(f"Stato Generale Studio")
    
    t_db = leggi_tabella("task")
    c_db = leggi_tabella("commesse")
    
    # SEZIONE CRITICITÀ (Solo per Admin e PM)
    if ruolo_u in ["Admin", "PM"]:
        bloccati = [t for t in t_db if t.get('stato') == 'Bloccato']
        oggi_str = str(date.today())
        scaduti = [t for t in t_db if t.get('scadenza') < oggi_str and t.get('stato') != 'Completato']
        
        if bloccati or scaduti:
            st.error(f"🚨 **Alert Criticità:** {len(bloccati)} task bloccati | {len(scaduti)} task scaduti")
            with st.expander("Dettaglio Blocchi"):
                for b in bloccati:
                    st.write(f"⚠️ **{b['assegnato_a']}** su **{b['commessa_ref']}**: {b.get('motivo_blocco', 'Nessuna nota')}")

    st.divider()
    
    # ELENCO COMMESSE IN CORSO
    st.subheader("📂 Commesse Attive")
    if not c_db:
        st.info("Nessuna commessa registrata.")
    else:
        for c in c_db:
            col_a, col_b = st.columns([3, 1])
            col_a.write(f"**{c['codice']}** - {c['cliente']} (Scadenza: {c['scadenza']})")
            col_b.write(f"Budget: €{c.get('budget', 0)}")
            st.progress(40) # Placeholder avanzamento

# ==========================================
# [06_GESTIONE TASK (FILTRI & PRIORITÀ)]
# ==========================================
elif scelta == "📋 Gestione Task":
    st.header("Visualizzazione e Aggiornamento Task")
    t_db = leggi_tabella("task")
    utenti_list = leggi_tabella("utenti")
    
    # Filtro visualizzazione per Admin/PM
    filtro_nome = nome_u
    if ruolo_u in ["Admin", "PM"]:
        nomi_per_filtro = ["Tutti"] + [ut['nome'] for ut in utenti_list]
        filtro_nome = st.selectbox("Visualizza task di:", nomi_per_filtro)

    # Applicazione Filtro
    mostra_task = t_db
    if filtro_nome != "Tutti":
        mostra_task = [t for t in t_db if t['assegnato_a'] == filtro_nome and t['stato'] != 'Completato']
    else:
        mostra_task = [t for t in t_db if t['stato'] != 'Completato']

    # ORDINAMENTO: Priorità (Alta > Media > Bassa) e poi Scadenza
    mappa_prio = {"Alta": 0, "Media": 1, "Bassa": 2}
    mostra_task.sort(key=lambda x: (mappa_prio.get(x.get('priorita', 'Bassa'), 3), x.get('scadenza', '9999-12-31')))

    if not mostra_task:
        st.success("Nessun task attivo trovato.")
    else:
        for t in mostra_task:
            icona = "🔴" if t.get('priorita') == "Alta" else "🟡" if t.get('priorita') == "Media" else "🟢"
            with st.expander(f"{icona} [{t['scadenza']}] {t['commessa_ref']} - {t['descrizione']} ({t['assegnato_a']})"):
                st.write(f"**Priorità:** {t['priorita']} | **Stato:** {t['stato']}")
                
                # Permetti aggiornamento se è il proprio task o se Admin/PM
                if ruolo_u in ["Admin", "PM"] or t['assegnato_a'] == nome_u:
                    col_s, col_n = st.columns(2)
                    nuovo_st = col_s.selectbox("Cambia Stato", ["In corso", "Completato", "Bloccato"], key=f"st_{t['id']}")
                    nota_bl = ""
                    if nuovo_st == "Bloccato":
                        nota_bl = col_n.text_area("Motivo blocco", value=t.get('motivo_blocco', ""), key=f"nt_{t['id']}")
                    
                    if st.button("Salva Modifiche", key=f"save_{t['id']}"):
                        aggiorna_db("task", t['id'], {"stato": nuovo_st, "motivo_blocco": nota_bl})
                        st.rerun()

# ==========================================
# [07_NUOVA COMMESSA]
# ==========================================
elif scelta == "🏗️ Nuova Commessa":
    st.header("Apertura Nuova Pratica")
    with st.form("form_commessa", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cod = c1.text_input("Codice Commessa")
        cli = c1.text_input("Cliente")
        bud = c2.number_input("Budget (€)", min_value=0.0)
        scad = c2.date_input("Scadenza Contrattuale")
        if st.form_submit_button("Registra Progetto"):
            scrivi_dati("commesse", {"codice": cod, "cliente": cli, "budget": bud, "scadenza": str(scad)})
            st.success(f"Commessa {cod} creata correttamente!")

# ==========================================
# [08_ASSEGNAZIONE TASK]
# ==========================================
elif scelta == "🎯 Assegna Lavoro":
    st.header("Distribuzione Attività ai Tecnici")
    comm_list = leggi_tabella("commesse")
    codici_c = [c['codice'] for c in comm_list] if comm_list else ["Nessuna"]
    ut_list = leggi_tabella("utenti")
    nomi_t = [ut['nome'] for ut in ut_list]

    with st.form("form_task"):
        sel_c = st.selectbox("Seleziona Progetto", codici_c)
        att = st.selectbox("Attività", ATTIVITA_STANDARD)
        chi = st.selectbox("Assegna a", nomi_t)
        prio_scelta = st.select_slider("Livello Priorità", options=["Bassa", "Media", "Alta"])
        scad_t = st.date_input("Scadenza Task")
        
        if st.form_submit_button("Invia Task"):
            # Se un PM assegna un'Alta priorità, il task parte come "Non approvato"
            approvato = True if ruolo_u == "Admin" else False
            payload_task = {
                "commessa_ref": sel_c, "descrizione": att, "assegnato_a": chi,
                "priorita": prio_scelta, "scadenza": str(scad_t), "stato": "In corso",
                "approvato_admin": approvato
            }
            scrivi_dati("task", payload_task)
            st.success("Task assegnato con successo!")

# ==========================================
# [09_APPROVAZIONI ADMIN]
# ==========================================
elif scelta == "⚖️ Approvazioni":
    st.header("Validazione Task Prioritari")
    t_all = leggi_tabella("task")
    da_validare = [t for t in t_all if t.get('approvato_admin') == False]
    
    if not da_validare:
        st.success("Tutti i task sono stati verificati.")
    else:
        for t in da_validare:
            with st.warning(f"Task da PM: {t['descrizione']} | Destinatario: {t['assegnato_a']} | Priorità: {t['priorita']}"):
                col_y, col_n = st.columns(2)
                if col_y.button("✅ Approva", key=f"ok_{t['id']}"):
                    aggiorna_db("task", t['id'], {"approvato_admin": True})
                    st.rerun()
                if col_n.button("❌ Rifiuta", key=f"no_{t['id']}"):
                    # Qui si potrebbe aggiungere logica di eliminazione
                    pass
