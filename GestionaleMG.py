import streamlit as st
import httpx
import smtplib
import os
import json
from email.mime.text import MIMEText
from datetime import date, datetime
from urllib.parse import urlencode
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
def _safe_secret(key):
    try:
        return st.secrets.get(key)
    except Exception:
        return os.getenv(key)

URL = _safe_secret("SUPABASE_URL")
KEY = _safe_secret("SUPABASE_KEY")
DB_READY = bool(URL and KEY)
HEADERS = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"} if DB_READY else {}

AI_API_URL = _safe_secret("AI_API_URL")
AI_API_KEY = _safe_secret("AI_API_KEY")
AI_MODEL = _safe_secret("AI_MODEL") or "gpt-4o-mini"

HUGGINGFACE_API_KEY = _safe_secret("HUGGINGFACE_API_KEY")
HUGGINGFACE_MODEL = _safe_secret("HUGGINGFACE_MODEL") or "meta-llama/Llama-3.1-8B-Instruct"
HUGGINGFACE_API_URL = _safe_secret("HUGGINGFACE_API_URL") or "https://router.huggingface.co/v1/chat/completions"
AI_PROVIDER = (_safe_secret("AI_PROVIDER") or ("huggingface" if HUGGINGFACE_API_KEY else "openai_compatible")).lower()

SMTP_HOST = _safe_secret("SMTP_HOST")
SMTP_PORT = int(_safe_secret("SMTP_PORT") or 587)
SMTP_USER = _safe_secret("SMTP_USER")
SMTP_PASSWORD = _safe_secret("SMTP_PASSWORD")
SMTP_FROM = _safe_secret("SMTP_FROM") or SMTP_USER
SMTP_USE_TLS = str(_safe_secret("SMTP_USE_TLS") or "true").lower() in ["1", "true", "yes", "on"]

class DbResult:
    def __init__(self, status_code=503, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload

@st.cache_data(ttl=30, show_spinner=False)
def db_get(tabella, select="*", filtri=None, order=None, limit=None):
    if not DB_READY:
        return []
    try:
        params = {"select": select}
        if filtri:
            params.update(filtri)
        if order:
            params["order"] = order
        if limit is not None:
            params["limit"] = str(limit)

        query = urlencode(params, doseq=True, safe=",().")
        res = httpx.get(f"{URL}/rest/v1/{tabella}?{query}", headers=HEADERS, timeout=10)
        return res.json() if res.status_code == 200 else []
    except:
        return []

def db_update(tabella, id_riga, payload):
    if not DB_READY:
        return DbResult(text="DB non configurato. Imposta SUPABASE_URL e SUPABASE_KEY in secrets.toml.")
    try:
        result = httpx.patch(f"{URL}/rest/v1/{tabella}?id=eq.{id_riga}", headers=HEADERS, json=payload, timeout=10)
        db_get.clear()
        return result
    except Exception as e:
        return DbResult(text=f"Errore update DB: {e}")

def db_insert(tabella, payload):
    if not DB_READY:
        return DbResult(text="DB non configurato. Imposta SUPABASE_URL e SUPABASE_KEY in secrets.toml.")
    try:
        result = httpx.post(f"{URL}/rest/v1/{tabella}", headers=HEADERS, json=payload, timeout=10)
        db_get.clear()
        return result
    except Exception as e:
        return DbResult(text=f"Errore insert DB: {e}")


def errore_colonna_mancante(res, colonna_attesa):
    """Rileva errori PostgREST di colonna non presente in schema cache."""
    if not res:
        return False
    payload_text = (getattr(res, "text", "") or "")
    return (
        getattr(res, "status_code", None) in [400, 404]
        and "PGRST204" in payload_text
        and colonna_attesa in payload_text
    )

def calcola_stato_commessa(task_commessa):
    if not task_commessa:
        return "Aperto"

    stati_task = [t.get("stato") for t in task_commessa]
    if all(s == "Completato" for s in stati_task):
        return "Concluso"
    if any(s == "Bloccato" for s in stati_task):
        return "Bloccato"
    return "Aperto"

def icona_stato_commessa(stato):
    mapping = {
        "Aperto": "🟢",
        "Bloccato": "🚨",
        "Concluso": "✅"
    }
    return mapping.get(stato, "📂")

def icona_stato_task(stato):
    mapping = {
        "In corso": "🟡",
        "Bloccato": "🚨",
        "Completato": "✅"
    }
    return mapping.get(stato, "❓")

def etichetta_scadenza(task, oggi):
    try:
        d_scad = date.fromisoformat(task.get('scadenza'))
        diff = (d_scad - oggi).days
        if diff < 0:
            return f"⏰ Scaduto da {abs(diff)}gg"
        if diff <= 3:
            return f"⏳ In scadenza tra {diff}gg"
        return f"📅 Scade tra {diff}gg"
    except:
        return "❓ Scadenza non definita"

def sync_stato_commessa(codice_commessa, commesse_cache=None, task_cache=None):
    commesse = commesse_cache if commesse_cache is not None else db_get("commesse")
    tasks = task_cache if task_cache is not None else db_get("task")

    commessa = next((c for c in commesse if c.get("codice") == codice_commessa), None)
    if not commessa or "id" not in commessa:
        return

    task_commessa = [t for t in tasks if t.get("commessa_ref") == codice_commessa]
    nuovo_stato = calcola_stato_commessa(task_commessa)
    if commessa.get("stato") != nuovo_stato:
        db_update("commesse", commessa["id"], {"stato": nuovo_stato})

def periodo_giornata(adesso=None):
    now = adesso or datetime.now()
    return "mattina" if now.hour < 13 else "pomeriggio"

def riepilogo_task_dashboard(task_utente):
    oggi = date.today()
    imminenti, scaduti = [], []

    for t in task_utente:
        scad = t.get("scadenza")
        if not scad:
            continue
        try:
            data_scad = date.fromisoformat(scad)
        except Exception:
            continue

        diff = (data_scad - oggi).days
        if diff < 0:
            scaduti.append(t)
        elif diff <= 3:
            imminenti.append(t)

    imminenti.sort(key=lambda x: x.get("scadenza") or "9999-12-31")
    scaduti.sort(key=lambda x: x.get("scadenza") or "9999-12-31")
    return imminenti, scaduti



def ai_chat_completion(system_prompt, user_payload, temperature=0.4, timeout=12):
    if AI_PROVIDER == "huggingface":
        if not HUGGINGFACE_API_KEY:
            return None
        try:
            response = httpx.post(
                HUGGINGFACE_API_URL,
                headers={
                    "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": HUGGINGFACE_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_payload},
                    ],
                    "temperature": temperature,
                },
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip() or None
        except Exception:
            return None

    if not AI_API_URL or not AI_API_KEY:
        return None

    try:
        response = httpx.post(
            AI_API_URL,
            headers={
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": AI_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_payload},
                ],
                "temperature": temperature,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip() or None
    except Exception:
        return None

def genera_testo_mail_blocco_ai(evento):
    fallback = (
        f"È stato segnalato un blocco operativo sulla commessa {evento.get('commessa_codice')}.\n\n"
        f"Task: {evento.get('task_descrizione')}\n"
        f"Tecnico: {evento.get('tecnico')}\n"
        f"Data: {evento.get('data_evento')}\n"
        f"Motivazione: {evento.get('motivazione')}\n\n"
        "Si richiede presa in carico del blocco e definizione delle azioni correttive."
    )

    system_prompt = (
        "Sei un assistente per comunicazioni aziendali. Scrivi un'email in italiano, tono professionale e operativo, "
        "max 160 parole, senza markdown, con: riepilogo evento, impatto e prossimi passi consigliati."
    )
    content = ai_chat_completion(system_prompt, json.dumps(evento, ensure_ascii=False), temperature=0.4, timeout=12)
    return content or fallback

def invia_mail_blocco(destinatari, oggetto, corpo):
    if not destinatari:
        return False, "Nessun destinatario email valido (PM/Admin) trovato."
    if not (SMTP_HOST and SMTP_FROM):
        return False, "SMTP non configurato. Imposta SMTP_HOST, SMTP_FROM, SMTP_USER e SMTP_PASSWORD in secrets."

    msg = MIMEText(corpo, "plain", "utf-8")
    msg["Subject"] = oggetto
    msg["From"] = SMTP_FROM
    msg["To"] = ", ".join(destinatari)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            if SMTP_USE_TLS:
                server.starttls()
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, destinatari, msg.as_string())
        return True, "Email inviata con successo a PM/Admin."
    except Exception as e:
        return False, f"Errore invio email: {e}"

def notifica_blocco_task(task, commesse, utenti, motivazione):
    commessa = next((c for c in commesse if c.get("codice") == task.get("commessa_ref")), None)
    pm_nome = commessa.get("pm_assegnato") if commessa else None

    admin_users = [u for u in utenti if u.get("ruolo") == "Admin"]
    destinatari = set()
    if pm_nome:
        pm_user = next((u for u in utenti if u.get("nome") == pm_nome), None)
        if pm_user and pm_user.get("email"):
            destinatari.add(pm_user.get("email"))
    for adm in admin_users:
        if adm.get("email"):
            destinatari.add(adm.get("email"))

    # Formato oggetto richiesto: nome commessa - Attività in Blocco - nome tecnico
    nome_commessa = task.get("commessa_ref") or (commessa.get("cliente") if commessa else "N/D")
    oggetto = f"{nome_commessa} - Attività in Blocco - {task.get('assegnato_a')}"
    evento = {
        "commessa_codice": task.get("commessa_ref"),
        "commessa_cliente": commessa.get("cliente") if commessa else "N/D",
        "task_descrizione": task.get("descrizione"),
        "tecnico": task.get("assegnato_a"),
        "data_evento": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "motivazione": motivazione,
    }
    corpo = genera_testo_mail_blocco_ai(evento)
    return invia_mail_blocco(sorted(destinatari), oggetto, corpo)


def routine_invio_mail_blocco(prev_stato, nuovo_stato, task, commesse, utenti, motivazione_blocco):
    """Invia email solo alla transizione verso stato Bloccato, evitando invii duplicati."""
    if nuovo_stato != "Bloccato":
        return False, "Nessuna notifica: stato non bloccato."
    if prev_stato == "Bloccato":
        return False, "Nessuna notifica: task già bloccato (evitato invio duplicato)."
    return notifica_blocco_task(task, commesse, utenti, motivazione_blocco)

def genera_contenuti_motivazionali(nome, task_aperti, imminenti, scaduti):
    fallback = {
        "welcome": f"Buon {periodo_giornata()} {nome}, imposta le priorità e parti dal task più vicino alla scadenza.",
        "programma_oggi": (
            f"Programma del {periodo_giornata()}: completa almeno 1 attività critica, "
            "aggiorna gli stati bloccati e pianifica il prossimo step della commessa."
        ),
        "frase_motivazionale": "Ogni task chiuso oggi rende il progetto più solido domani.",
        "mini_riepilogo": f"Task aperti: {len(task_aperti)} · Imminenti: {len(imminenti)} · Scaduti: {len(scaduti)}"
    }

    payload_prompt = {
        "nome": nome,
        "periodo": periodo_giornata(),
        "totale_task_aperti": len(task_aperti),
        "task_imminenti": [{"descrizione": t.get("descrizione"), "scadenza": t.get("scadenza")} for t in imminenti[:5]],
        "task_scaduti": [{"descrizione": t.get("descrizione"), "scadenza": t.get("scadenza")} for t in scaduti[:5]],
    }

    system_prompt = (
        "Sei l'assistente motivazionale di un gestionale tecnico. "
        "Rispondi SOLO in JSON valido con chiavi: welcome, programma_oggi, frase_motivazionale, mini_riepilogo. "
        "Massimo 25 parole per campo, tono professionale ed energico, in italiano."
    )

    content = ai_chat_completion(system_prompt, json.dumps(payload_prompt, ensure_ascii=False), temperature=0.7, timeout=12)
    if not content:
        return fallback

    try:
        parsed = json.loads(content)
        return {
            "welcome": parsed.get("welcome") or fallback["welcome"],
            "programma_oggi": parsed.get("programma_oggi") or fallback["programma_oggi"],
            "frase_motivazionale": parsed.get("frase_motivazionale") or fallback["frase_motivazionale"],
            "mini_riepilogo": parsed.get("mini_riepilogo") or fallback["mini_riepilogo"],
        }
    except Exception:
        return fallback

# ==========================================
# [03] ACCESSO (LOGIN)
# ==========================================
if "u" not in st.session_state:
    st.title("🏗️ MasterGroup Cloud")
    if not DB_READY:
        st.warning("⚠️ Configurazione DB mancante: aggiungi SUPABASE_URL e SUPABASE_KEY in `.streamlit/secrets.toml` per usare login e dati reali.")
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
    st.header("Dashboard Smart")
    
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

    imminenti_task, scaduti_task = riepilogo_task_dashboard(miei_aperti)
    contenuti_ai = genera_contenuti_motivazionali(nome_u, miei_aperti, imminenti_task, scaduti_task)

    st.subheader(f"👋 {contenuti_ai['welcome']}")
    st.caption(f"🗓️ {contenuti_ai['programma_oggi']}")

    # 3. Visualizzazione Metriche
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("I tuoi Task aperti", len(miei_aperti))
    col2.metric("Scadenze imminenti (3gg)", imminenti, delta_color="inverse" if imminenti > 0 else "normal")
    col3.metric("Task scaduti", len(scaduti_task), delta_color="inverse" if len(scaduti_task) > 0 else "normal")
    
    if ruolo == "Admin":
        cs = db_get("commesse")
        tot_b = sum(float(c.get('budget', 0)) for c in cs)
        bud_bloccate = sum(float(c.get('budget', 0)) for c in cs if c.get('stato') == 'Bloccato')
        col4.metric("Budget Totale Commesse", f"€ {tot_b:,.2f}")
        st.info(f"🔒 Budget commesse bloccate: **€ {bud_bloccate:,.2f}**")
    else:
        col4.metric("Task imminenti + scaduti", len(imminenti_task) + len(scaduti_task))

    st.divider()

    # 4. Motivazione e mini-riepilogo intelligente
    st.markdown(f"**💡 Pensiero del giorno:** *{contenuti_ai['frase_motivazionale']}*")
    st.markdown(f"**🧾 Mini riepilogo:** {contenuti_ai['mini_riepilogo']}")

    if imminenti_task:
        st.write("**⏳ Task imminenti**")
        for t in imminenti_task[:3]:
            st.write(f"- {t.get('commessa_ref')} · {t.get('descrizione')} (scad. {t.get('scadenza')})")

    if scaduti_task:
        st.write("**🚨 Task scaduti**")
        for t in scaduti_task[:3]:
            st.write(f"- {t.get('commessa_ref')} · {t.get('descrizione')} (scad. {t.get('scadenza')})")

# ==========================================
# [06] GESTIONE TASK (OPERATIVITÀ & PRIORITÀ) REV 01.08
# ==========================================
elif scelta == "📋 Gestione Task":
    st.header("Monitoraggio Attività")
    cs, us = db_get("commesse"), db_get("utenti")
    oggi = date.today()

    # --- FILTRI INCROCIATI ---
    f1, f2, f3, f4 = st.columns([1, 1, 1, 1])
    
    # Filtro Tecnico: Solo Admin e PM scelgono, Operatore vede solo i suoi
    if ruolo in ["Admin", "PM"]:
        sel_tec = f1.selectbox("Filtra Tecnico", ["Tutti"] + [usr.get('nome') for usr in us])
    else:
        sel_tec = nome_u
        f1.write(f"**Tecnico:** {nome_u}")

    sel_com = f2.selectbox("Filtra Commessa", ["Tutte"] + [cm.get('codice') for cm in cs])
    opzioni_stato = [
        "In corso (incl. bloccati)",
        "In corso (solo non bloccati)",
        "Bloccato",
        "Completato",
        "Tutti"
    ]
    sel_sta = f3.selectbox("Filtra Stato", opzioni_stato, index=0)
    limite_visualizzazione = f4.number_input("Max task da mostrare", min_value=20, max_value=500, value=120, step=20)

    # --- LOGICA FILTRO (SERVER-SIDE SU SUPABASE) ---
    filtri = {}

    if sel_tec != "Tutti":
        filtri["assegnato_a"] = f"eq.{sel_tec}"

    if sel_com != "Tutte":
        filtri["commessa_ref"] = f"eq.{sel_com}"

    if sel_sta == "In corso (incl. bloccati)":
        filtri["or"] = "(stato.eq.In corso,stato.eq.Bloccato)"
    elif sel_sta == "In corso (solo non bloccati)":
        filtri["stato"] = "eq.In corso"
    elif sel_sta in ["Bloccato", "Completato"]:
        filtri["stato"] = f"eq.{sel_sta}"

    f_t = db_get("task", filtri=filtri, order="scadenza.asc.nullslast", limit=limite_visualizzazione)

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
            motivazione_blocco = ""
            if n_stato == "Bloccato":
                motivazione_blocco = st.text_area(
                    "Motivazione blocco (obbligatoria)",
                    value=t.get("motivazione_blocco") or "",
                    key=f"mb_{t['id']}",
                    placeholder="Descrivi impedimento, impatto e supporto richiesto..."
                ).strip()
            
            if st.button("Conferma Cambio Stato", key=f"up_{t['id']}"):
                if n_stato == "Bloccato" and not motivazione_blocco:
                    st.warning("Inserisci una motivazione prima di impostare il task come Bloccato.")
                    st.stop()

                payload_update = {"stato": n_stato}
                if n_stato == "Bloccato":
                    payload_update["motivazione_blocco"] = motivazione_blocco
                else:
                    payload_update["motivazione_blocco"] = None

                res_up = db_update("task", t['id'], payload_update)
                motivazione_salvata = True

                # Fallback compatibilità: se la migrazione DB non è stata ancora applicata,
                # aggiorniamo almeno lo stato task evitando errore bloccante in UI.
                if errore_colonna_mancante(res_up, "motivazione_blocco"):
                    motivazione_salvata = False
                    res_up = db_update("task", t['id'], {"stato": n_stato})

                if res_up.status_code not in [200, 204]:
                    st.error(f"Errore aggiornamento task: {res_up.text}")
                    st.stop()

                sync_stato_commessa(t.get('commessa_ref'))

                if n_stato == "Bloccato":
                    if not motivazione_salvata:
                        st.warning(
                            "Stato aggiornato, ma la motivazione non è stata salvata: "
                            "applica la migrazione `db_migrazione_blocco_task.sql`."
                        )

                    ok_mail, msg_mail = routine_invio_mail_blocco(
                        prev_stato=t.get("stato"),
                        nuovo_stato=n_stato,
                        task=t,
                        commesse=cs,
                        utenti=us,
                        motivazione_blocco=motivazione_blocco,
                    )
                    if ok_mail:
                        st.success("Stato aggiornato. " + msg_mail)
                    else:
                        st.info("Stato aggiornato. " + msg_mail)
                else:
                    st.success("Stato task e commessa aggiornati!")
                st.rerun()
# ==========================================
# [07] ANALISI COMMESSE
# ==========================================
elif scelta == "📊 Analisi Commesse":
    st.header("Avanzamento Progetti")
    cs, ts = db_get("commesse"), db_get("task")
    oggi = date.today()

    c_fil1, c_fil2 = st.columns([1, 2])
    filtro_stato = c_fil1.selectbox("Filtra stato commessa", ["Tutti", "Aperto", "Bloccato", "Concluso"], index=0)
    query_cerca = c_fil2.text_input("🔎 Cerca commessa (codice, cliente, PM)").strip().lower()

    if filtro_stato != "Tutti":
        cs = [c for c in cs if c.get('stato', 'Aperto') == filtro_stato]

    if query_cerca:
        cs = [
            c for c in cs
            if query_cerca in str(c.get("codice", "")).lower()
            or query_cerca in str(c.get("cliente", "")).lower()
            or query_cerca in str(c.get("pm_assegnato", "")).lower()
        ]

    # Default: commesse più recenti prima (se c'è timestamp), altrimenti prefisso numerico codice desc.
    cs = sorted(cs, key=chiave_ordinamento_commessa_desc, reverse=True)

    if not cs:
        st.info("Nessuna commessa trovata con questo filtro/ricerca.")

    for c in cs:
        t_comm = [t for t in ts if t.get('commessa_ref') == c.get('codice')]
        stato_calcolato = calcola_stato_commessa(t_comm)
        stato_commessa = c.get('stato') or stato_calcolato

        if c.get('stato') != stato_calcolato and c.get('codice'):
            sync_stato_commessa(c.get('codice'), commesse_cache=cs, task_cache=ts)
            stato_commessa = stato_calcolato

        chiusi = len([t for t in t_comm if t['stato'] == 'Completato'])
        perc = (chiusi / len(t_comm) * 100) if t_comm else 0
        icona_commessa = icona_stato_commessa(stato_commessa)
        pm_commessa = c.get("pm_assegnato") or "Non assegnato"
        with st.expander(f"{icona_commessa} {c['codice']} - {c['cliente']} | PM: {pm_commessa} | Stato: {stato_commessa} ({int(perc)}%)"):
            if ruolo == "Admin":
                st.write(f"💰 Budget: **€ {c.get('budget', 0)}**")
            st.write(f"👤 PM incaricato: **{pm_commessa}**")
            st.write(f"📌 Stato commessa: **{icona_commessa} {stato_commessa}**")
            st.progress(perc / 100)
            for tc in t_comm:
                stato_task = tc.get('stato')
                icona_task = icona_stato_task(stato_task)
                scadenza_task = etichetta_scadenza(tc, oggi)
                st.write(
                    f"- **{tc.get('assegnato_a')}**: {tc.get('descrizione')} "
                    f"[{icona_task} {stato_task}] · {scadenza_task}"
                )

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
            elenco_pm = [usr.get('nome') for usr in us if usr.get('ruolo') == 'PM']
            sel_pm = st.selectbox("Seleziona PM Responsabile", elenco_pm)
            
            if st.form_submit_button("Crea Commessa"):
                if cod_c and cli_c:
                    payload_c = {
                        "codice": cod_c, 
                        "cliente": cli_c, 
                        "budget": bud_c, 
                        "scadenza": str(scad_c),
                        "pm_assegnato": sel_pm,  # Nome colonna corretto del tuo DB
                        "stato": "Aperto"
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
                        sync_stato_commessa(t_comm_ref)
                        if alert_mostra:
                            st.warning(f"⚠️ Task creato, ma supera la fine commessa ({scad_max_str})!")
                        else:
                            st.success(f"✅ Task assegnato a {t_tec}!")
                        st.rerun() # Ricarica per mostrare i valori salvati
                    else:
                        st.error("Errore creazione task.")

