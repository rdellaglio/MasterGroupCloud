import streamlit as st
import httpx
from datetime import date, datetime
import random

# ==========================================
# [01_CONFIGURAZIONE & BRANDING]
# ==========================================
st.set_page_config(page_title="MasterGroup Cloud", page_icon="🏗️", layout="wide")
URL_LOGO = "LogoMG.png" 

st.markdown("""
    <style>
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stHeader"] {background-color: rgba(0,0,0,0); height: 3rem;}
    [data-testid="stSidebarNav"] {padding-top: 20px;}
    </style>
    """, unsafe_allow_html=True)

try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    URL = "https://clauyljovenkcqemswfk.supabase.co"
    KEY = "sb_publishable_WetwA7q8dmctM2a-VDBfTg_M46vnFi0"

headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

# ==========================================
# [02_MOTORE INTELLIGENTE (METEO & DATI)]
# ==========================================
def get_meteo_bari():
    """Recupera meteo reale per Bari via Open-Meteo (Gratuito)"""
    try:
        # Coordinate Bari: 41.11, 16.87
        res = httpx.get("https://api.open-meteo.com/v1/forecast?latitude=41.1171&longitude=16.8719&current_weather=true").json()
        curr = res["current_weather"]
        temp = curr["temperature"]
        code = curr["weathercode"]
        
        # Interpretazione codici meteo WMO
        if code == 0: desc, icon, sugg = "Sereno", "☀️", "Perfetto per sopralluoghi e rilievi!"
        elif code in [1, 2, 3]: desc, icon, sugg = "Poco Nuvoloso", "🌤️", "Buona visibilità per il cantiere."
        elif code in [61, 63, 65, 80]: desc, icon, sugg = "Pioggia", "🌧️", "Meteo avverso: meglio lavorare su CME e DOCFA in ufficio."
        else: desc, icon, sugg = "Variabile", "☁️", "Controlla bene le attrezzature prima di uscire."
        
        return f"{icon} **Bari: {desc} ({temp}°C)**. {sugg}"
    except:
        return "🌤️ Meteo Bari non disponibile. Buon lavoro a tutto il team!"

def leggi_tabella(tabella):
    try:
        with httpx.Client() as client:
            res = client.get(f"{URL}/rest/v1/{tabella}?select=*", headers=headers)
            return res.json()
    except: return []

def aggiorna_db(tabella, id_riga, payload):
    try:
        with httpx.Client() as client:
            return client.patch(f"{URL}/rest/v1/{tabella}?id=eq.{id_riga}", headers=headers, json=payload)
    except: return None

def scrivi_dati(tabella, dati_json):
    try:
        with httpx.Client() as client:
            return client.post(f"{URL}/rest/v1/{tabella}", headers=headers, json=dati_json)
    except: return None

# ==========================================
# [03_ACCESSO]
# ==========================================
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🏗️ MasterGroup Cloud")
    with st.form("login_form"):
        e = st.text_input("Email Aziendale", key="l_email")
        p = st.text_input("Password", type="password", key="l_pass")
        if st.form_submit_button("Entra"):
            utenti = leggi_tabella("utenti")
            u = next((x for x in utenti if x.get('email')==e and x.get('password')==p), None)
            if u: 
                st.session_state.autenticato = True
                st.session_state.u = u
                st.rerun()
            else: st.error("Credenziali errate.")
    st.stop()

u_log = st.session_state.u
ruolo = u_log['ruolo']
nome_log = u_log['nome']

# ==========================================
# [04_SIDEBAR]
# ==========================================
try: st.sidebar.image(URL_LOGO, use_container_width=True)
except: st.sidebar.title("MasterGroup Cloud")
st.sidebar.markdown(f"👤 **{nome_log}** ({ruolo})")
st.sidebar.divider()

menu = ["🏠 Dashboard", "📋 Gestione Task"]
if ruolo in ["Admin", "PM"]:
    menu.extend(["📊 Analisi Commesse", "🎯 Assegnazione"])
if ruolo == "Admin":
    menu.append("⚖️ Approvazioni")

scelta = st.sidebar.radio("Navigazione", menu, key="nav_radio")
if st.sidebar.button("Logout"):
    st.session_state.autenticato = False
    st.rerun()

# ==========================================
# [05_DASHBOARD DINAMICA]
# ==========================================
if scelta == "🏠 Dashboard":
    st.header(f"Area Personale - {nome_log}")
    
    # BOX METEO & IA SUGGESTION
    info_meteo = get_meteo_bari()
    st.success(info_meteo)
    
    t_db = leggi_tabella("task")
    bloccati = [t for t in t_db if t.get('stato') == 'Bloccato']
    scaduti = [t for t in t_db if t['stato'] != 'Completato' and datetime.strptime(t['scadenza'], '%Y-%m-%d').date() < date.today()]
    
    # Messaggio Motivazionale Basato sui Dati
    if len(scaduti) > 0:
        st.warning(f"💡 **Focus del giorno:** MasterGroup ha {len(scaduti)} task scaduti. Diamo priorità assoluta alle urgenze 🔴!")
    elif len(bloccati) > 0:
        st.error(f"🚨 **Criticità:** Ci sono {len(bloccati)} attività ferme. Admin e PM devono sbloccarle per procedere.")
    else:
        st.info("✨ **Ottimo lavoro:** Lo studio non ha blocchi critici. Continuiamo così!")

    c1, c2 = st.columns(2)
    miei_task = [t for t in t_db if t['assegnato_a'] == nome_log and t['stato'] != 'Completato']
    c1.metric("I tuoi Task aperti", len(miei_task))
    if ruolo in ["Admin", "PM"]:
        c2.metric("SOS Studio (Blocchi)", len(bloccati))

# ==========================================
# [06_GESTIONE TASK]
# ==========================================
elif scelta == "📋 Gestione Task":
    st.header("Monitoraggio Operativo")
    t_db = leggi_tabella("task")
    c_db = leggi_tabella("commesse")
    utenti = leggi_tabella("utenti")
    oggi = date.today()

    col1, col2, col3 = st.columns(3)
    f_nome = nome_log if ruolo == "Operatore" else col1.selectbox("Tecnico", ["Tutti"] + [u['nome'] for u in utenti])
    f_comm = col2.selectbox("Commessa", ["Tutte"] + [c['codice'] for c in c_db])
    f_stato = col3.selectbox("Stato", ["Tutti", "In corso", "Bloccato", "Completato"])

    tasks = t_db
    if f_nome != "Tutti" and ruolo != "Operatore": tasks = [t for t in tasks if t['assegnato_a'] == f_nome]
    elif ruolo == "Operatore": tasks = [t for t in tasks if t['assegnato_a'] == nome_log]
    if f_comm != "Tutte": tasks = [t for t in tasks if t['commessa_ref'] == f_comm]
    if f_stato != "Tutti": tasks = [t for t in tasks if t['stato'] == f_stato]

    tasks.sort(key=lambda x: x.get('scadenza','9999-12-31'))

    for t in tasks:
        try:
            scad_dt = datetime.strptime(t['scadenza'], '%Y-%m-%d').date()
            diff = (scad_dt - oggi).days
            countdown = f"⏳ {diff}gg" if diff >= 0 else f"⏰ SCADUTO ({abs(diff)}gg)"
        except: countdown = "📅 Data n.d."

        p_color = "🔴" if t['priorita'] == "Alta" else "🟡" if t['priorita'] == "Media" else "🟢"
        prefix = "🚨 " if t['stato'] == "Bloccato" else ""
        
        with st.expander(f"{prefix}{p_color} [{countdown}] {t['commessa_ref']} - {t['descrizione']}"):
            if ruolo in ["Admin", "PM"]:
                c_a, c_b, c_c = st.columns(3)
                nuovo_tecnico = c_a.selectbox("Riassegna", [u['nome'] for u in utenti], index=[u['nome'] for u in utenti].index(t['assegnato_a']), key=f"te_{t['id']}")
                nuova_prio = c_b.selectbox("Priorità", ["Bassa", "Media", "Alta"], index=["Bassa", "Media", "Alta"].index(t['priorita']), key=f"pr_{t['id']}")
                nuova_scad = c_c.date_input("Scadenza", value=scad_dt, key=f"sc_{t['id']}")
                if st.button("Salva Modifica", key=f"save_{t['id']}"):
                    appr = (ruolo == "Admin")
                    aggiorna_db("task", t['id'], {"assegnato_a": nuovo_tecnico, "priorita": nuova_prio, "scadenza": str(nuova_scad), "approvato_admin": appr})
                    st.rerun()

            st.divider()
            lista_stati = ["In corso", "Completato", "Bloccato"]
            idx_st = lista_stati.index(t['stato']) if t['stato'] in lista_stati else 0
            nuovo_st = st.selectbox("Stato", lista_stati, index=idx_st, key=f"st_{t['id']}")
            nota = st.text_area("Motivo blocco", value=t.get('motivo_blocco',''), key=f"n_{t['id']}") if nuovo_st == "Bloccato" else ""
            if st.button("Aggiorna", key=f"up_{t['id']}"):
                aggiorna_db("task", t['id'], {"stato": nuovo_st, "motivo_blocco": nota})
                st.rerun()

# ==========================================
# [07_ANALISI COMMESSE]
# ==========================================
elif scelta == "📊 Analisi Commesse":
    st.header("Monitoraggio Avanzamento")
    c_db = leggi_tabella("commesse")
    t_db = leggi_tabella("task")
    oggi = date.today()

    for c in c_db:
        t_comm = [t for t in t_db if t.get('commessa_ref') == c['codice']]
        chiusi = len([t for t in t_comm if t['stato'] == 'Completato'])
        perc = (chiusi / len(t_comm) * 100) if t_comm else 0
        with st.expander(f"📂 {c['codice']} - {c['cliente']} ({int(perc)}%)"):
            st.progress(perc / 100)
            for tc in t_comm:
                st_icon = "🛑 BLOCCATO" if tc['stato'] == 'Bloccato' else ""
                try:
                    if tc['stato'] != 'Completato' and datetime.strptime(tc['scadenza'], '%Y-%m-%d').date() < oggi:
                        st_icon = "⏰ RITARDO"
                except: pass
                st.write(f"- {tc['assegnato_a']}: {tc['descrizione']} | Scadenza: {tc['scadenza']} **{st_icon}**")

# ==========================================
# [08_ASSEGNAZIONE]
# ==========================================
elif scelta == "🎯 Assegnazione":
    tab1, tab2 = st.tabs(["Nuova Commessa", "Nuovo Task"])
    with tab1:
        with st.form("f_c"):
            cod = st.text_input("Codice")
            cli = st.text_input("Cliente")
            ut = leggi_tabella("utenti")
            pm = st.selectbox("PM", [u['nome'] for u in ut if u['ruolo'] in ['Admin', 'PM']])
            scad_c = st.date_input("Scadenza")
            if st.form_submit_button("Crea"):
                scrivi_dati("commesse", {"codice": cod, "cliente": cli, "pm_assegnato": pm, "scadenza": str(scad_c)})
                st.rerun()
    with tab2:
        with st.form("f_t"):
            c_db = leggi_tabella("commesse")
            sel_c = st.selectbox("Progetto", [c['codice'] for c in c_db])
            desc = st.text_input("Attività")
            ut = leggi_tabella("utenti")
            chi = st.selectbox("Tecnico", [u['nome'] for u in ut])
            prio = st.selectbox("Priorità", ["Bassa", "Media", "Alta"])
            scad = st.date_input("Consegna")
            if st.form_submit_button("Assegna"):
                scrivi_dati("task", {"commessa_ref": sel_c, "descrizione": desc, "assegnato_a": chi, "priorita": prio, "scadenza": str(scad), "stato": "In corso", "approvato_admin": (ruolo=="Admin")})
                st.rerun()

elif scelta == "⚖️ Approvazioni":
    st.header("Richieste PM")
    da_val = [t for t in leggi_tabella("task") if t.get('approvato_admin') == False]
    for v in da_val:
        st.warning(f"Modifica su: {v['descrizione']}")
        if st.button("Approva", key=f"ok_{v['id']}"):
            aggiorna_db("task", v['id'], {"approvato_admin": True})
            st.rerun()
