import os
import random
from datetime import date, timedelta

import httpx

URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_KEY")

if not URL or not KEY:
    raise SystemExit("Errore: imposta SUPABASE_URL e SUPABASE_KEY nelle variabili ambiente.")

HEADERS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

client = httpx.Client(timeout=30)

aggettivi = [
    "Aurora", "Nebula", "Titan", "Miraggio", "Zenith", "Orizzonte", "Ametista", "Corallo", "Atlas", "Vortice",
    "Smeraldo", "Aria", "Luna", "Cometa", "Quasar", "Veliero", "Obelisco", "Prisma", "Nettuno", "Eclisse"
]

luoghi = [
    "Borgo Antico", "Porto Nuovo", "Parco delle Querce", "Lungomare Est", "Piazza del Faro", "Valle Serena", "Riva Sud",
    "Colle Blu", "Centro Storico", "Zona Artigiana", "Marina Alta", "Viale dei Tigli", "Distretto 7", "Corte Nova",
    "Pianura Verde", "Via dei Cedri", "Quartiere Aurora", "Canale Vecchio", "Polo Innovazione", "Rione San Marco"
]

clienti = [
    "Famiglia Bellini", "Condominio Le Magnolie", "Studio Vetro", "Officine Delta", "Residenza I Gelsi", "Hotel Il Molo",
    "Fondazione Ardea", "Cooperativa Tramontana", "Casa Editrice Polare", "Clinica San Luca", "Atelier Novecento",
    "Frantoio Solealto", "Tenuta delle Vigne", "Farmacia Centrale", "Panificio Moderno", "Associazione Marina Viva"
]

pm_list = ["Francesca Riva", "Luca De Santis", "Giulia Conte", "Marco Neri"]
tecnici = ["Alessio Romano", "Chiara Fontana", "Davide Serra", "Elena Guidi", "Federico Sala", "Irene Vitali"]

attivita_pool = [
    "Rilievo laser e restituzione 3D",
    "Bozza layout distributivo",
    "Verifica pratiche edilizie",
    "Computo metrico estimativo",
    "Progetto illuminotecnico creativo",
    "Piano sicurezza cantiere",
    "Mockup materiali e finiture",
    "Coordinamento fornitori locali",
    "Revisione cronoprogramma",
    "Report fotografico avanzamento",
    "Validazione impianto elettrico",
    "Check documentazione catastale",
]

stati_task = ["In corso", "Bloccato", "Completato"]

# 1) Pulizia dati esistenti (solo tabelle richieste)
for tabella in ["task", "commesse"]:
    r = client.delete(f"{URL}/rest/v1/{tabella}?id=not.is.null", headers=HEADERS)
    if r.status_code not in (200, 204):
        raise RuntimeError(f"Delete fallita su {tabella}: {r.status_code} - {r.text}")

# 2) Creazione 50 commesse demo
oggi = date.today()
commesse = []
for i in range(1, 51):
    codice = f"CM-{i:03d}"
    nome_fantasia = f"Progetto {random.choice(aggettivi)} {random.choice(luoghi)}"
    commesse.append(
        {
            "codice": codice,
            "cliente": f"{random.choice(clienti)} · {nome_fantasia}",
            "budget": float(random.randrange(25000, 220000, 2500)),
            "scadenza": str(oggi + timedelta(days=random.randint(40, 300))),
            "pm_assegnato": random.choice(pm_list),
            "stato": "Aperto",
        }
    )

r = client.post(f"{URL}/rest/v1/commesse", headers=HEADERS, json=commesse)
if r.status_code not in (200, 201):
    raise RuntimeError(f"Insert commesse fallita: {r.status_code} - {r.text}")

# 3) Creazione task demo (4 task per ogni commessa = 200 task)
tasks = []
for c in commesse:
    descrizioni = random.sample(attivita_pool, k=4)
    for idx, desc in enumerate(descrizioni, start=1):
        tasks.append(
            {
                "commessa_ref": c["codice"],
                "descrizione": f"{desc} #{idx}",
                "assegnato_a": random.choice(tecnici),
                "scadenza": str(oggi + timedelta(days=random.randint(5, 240))),
                "stato": random.choices(stati_task, weights=[60, 15, 25], k=1)[0],
            }
        )

r = client.post(f"{URL}/rest/v1/task", headers=HEADERS, json=tasks)
if r.status_code not in (200, 201):
    raise RuntimeError(f"Insert task fallita: {r.status_code} - {r.text}")

print("✅ Ripopolamento completato: 50 commesse e 200 task inseriti.")
