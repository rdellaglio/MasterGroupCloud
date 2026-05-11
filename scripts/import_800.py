"""
Import Esportazione 800 → Supabase
===================================
Legge i CSV dalla cartella locale e li carica nel DB via API REST Supabase.

Uso:
    export SUPABASE_URL='https://<project>.supabase.co'
    export SUPABASE_KEY='<service-role-key>'
    python scripts/import_800.py --csv-dir /percorso/Esportazione_800

I CSV devono essere quelli prodotti dall'esportazione normalizzata:
    commesse.csv, clienti.csv, utenti_collaboratori.csv,
    catalogo_prestazioni.csv, task.csv, assegnazioni_task.csv,
    contratti.csv, sal_commessa.csv, spese.csv, note_commessa.csv

Prerequisito: eseguire db_migrazione_import_800.sql su Supabase prima di questo script.
"""

import argparse
import csv
import os
import sys
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
URL = os.getenv("SUPABASE_URL", "").rstrip("/")
KEY = os.getenv("SUPABASE_KEY", "")

if not URL or not KEY:
    sys.exit("Errore: imposta SUPABASE_URL e SUPABASE_KEY nelle variabili ambiente.")

HEADERS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates",  # upsert su PK
}

CLIENT = httpx.Client(timeout=30)

# Mappatura stato CSV → stato DB (vincolo CHECK)
STATO_MAP = {
    "Da verificare": "Aperto",
    "Aperto":        "Aperto",
    "In corso":      "Aperto",
    "Bloccato":      "Bloccato",
    "Concluso":      "Concluso",
    "":              "Aperto",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def leggi_csv(percorso: Path) -> list[dict]:
    with open(percorso, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def val_num(s: str) -> float | None:
    s = (s or "").strip()
    return float(s) if s else None


def val_bool(s: str) -> bool:
    return str(s).strip().upper() in ("TRUE", "1", "YES", "SI")


def val_date(s: str) -> str | None:
    s = (s or "").strip()
    return s if s else None


def upsert(tabella: str, righe: list[dict], batch: int = 200) -> int:
    """Inserisce/aggiorna righe in batch. Restituisce il numero totale inserito."""
    totale = 0
    for i in range(0, len(righe), batch):
        chunk = righe[i:i + batch]
        res = CLIENT.post(f"{URL}/rest/v1/{tabella}", headers=HEADERS, json=chunk)
        if res.status_code not in (200, 201):
            print(f"  ✗ Errore su {tabella} batch {i//batch + 1}: {res.status_code} – {res.text[:300]}")
        else:
            totale += len(chunk)
    return totale


def stampa(label: str, n: int):
    print(f"  ✓ {label}: {n} record")


# ---------------------------------------------------------------------------
# Import per tabella
# ---------------------------------------------------------------------------

def import_clienti(righe: list[dict]) -> int:
    payload = []
    for r in righe:
        payload.append({
            "id":            r["id_cliente"],
            "denominazione": r["denominazione"],
            "tipo_cliente":  r.get("tipo_cliente") or None,
            "codice_fiscale": r.get("codice_fiscale") or None,
            "partita_iva":   r.get("partita_iva") or None,
            "email":         r.get("email") or None,
            "telefono":      r.get("telefono") or None,
            "indirizzo":     r.get("indirizzo") or None,
            "note":          r.get("note") or None,
        })
    return upsert("clienti", payload)


def import_utenti(righe: list[dict]) -> int:
    """
    Aggiorna/inserisce utenti nel DB esistente.
    Usa nome_visualizzato come chiave per il campo 'nome' del DB.
    """
    payload = []
    for r in righe:
        nome = r.get("nome_visualizzato") or r.get("nome") or ""
        if not nome.strip():
            continue
        payload.append({
            "nome":            nome,
            "interno_esterno": r.get("interno_esterno") or "Interno",
            "costo_orario":    val_num(r.get("costo_orario", "")) or 30.0,
        })
    # upsert su nome (non ha PK esplicita nell'export → insert con on_conflict=ignore)
    headers_no_merge = {**HEADERS, "Prefer": "resolution=ignore-duplicates"}
    totale = 0
    for i in range(0, len(payload), 200):
        chunk = payload[i:i + 200]
        res = CLIENT.post(f"{URL}/rest/v1/utenti", headers=headers_no_merge, json=chunk)
        if res.status_code not in (200, 201):
            print(f"  ✗ Errore utenti: {res.status_code} – {res.text[:300]}")
        else:
            totale += len(chunk)
    return totale


def import_catalogo(righe: list[dict]) -> int:
    payload = []
    for r in righe:
        payload.append({
            "id":                  r["id_prestazione_catalogo"],
            "codice":              r.get("codice") or None,
            "descrizione":         r["descrizione"],
            "categoria":           r.get("categoria") or None,
            "area_pratica":        r.get("area_pratica") or None,
            "attiva":              val_bool(r.get("attiva", "TRUE")),
            "ordinamento":         int(r["ordinamento"]) if r.get("ordinamento") else None,
            "chiave_normalizzata": r.get("chiave_normalizzata") or None,
        })
    return upsert("catalogo_prestazioni", payload)


def import_commesse(righe: list[dict]) -> int:
    payload = []
    for r in righe:
        stato_raw = (r.get("stato") or "").strip()
        payload.append({
            "codice":               r["codice"],
            "cliente":              r.get("cliente_testo") or "",
            "titolo":               r.get("titolo") or None,
            "oggetto":              r.get("oggetto") or None,
            "indirizzo_intervento": r.get("indirizzo_intervento") or None,
            "area_pratica":         r.get("area_pratica") or None,
            "tipo_pratica":         r.get("tipo_pratica") or None,
            "budget":               val_num(r.get("budget", "")),
            "importo_contratto":    val_num(r.get("importo_contratto", "")),
            "scadenza":             val_date(r.get("scadenza", "")),
            "pm_assegnato":         r.get("pm_assegnato") or None,
            "stato":                STATO_MAP.get(stato_raw, "Aperto"),
            "contratto_stato":      r.get("contratto_stato") or None,
            "note":                 r.get("note") or None,
            "totale_fatturato":     val_num(r.get("totale_fatturato_excel", "")),
            "totale_pagato":        val_num(r.get("totale_pagato_excel", "")),
            "totale_spese":         val_num(r.get("totale_spese_excel", "")),
            "cassa":                val_num(r.get("cassa_excel", "")),
        })
    # upsert su codice
    headers_codice = {**HEADERS, "Prefer": "resolution=merge-duplicates"}
    totale = 0
    for i in range(0, len(payload), 200):
        chunk = payload[i:i + 200]
        res = CLIENT.post(f"{URL}/rest/v1/commesse", headers=headers_codice, json=chunk)
        if res.status_code not in (200, 201):
            print(f"  ✗ Errore commesse: {res.status_code} – {res.text[:300]}")
        else:
            totale += len(chunk)
    return totale


def import_task(righe: list[dict]) -> int:
    payload = []
    for r in righe:
        stato_raw = (r.get("stato") or "").strip()
        # Mappa stato task: vuoto → "In corso"
        stato_task_map = {
            "In corso":   "In corso",
            "Bloccato":   "Bloccato",
            "Completato": "Completato",
            "":           "In corso",
        }
        payload.append({
            "commessa_ref":          r.get("codice_commessa") or "",
            "descrizione":           r.get("descrizione") or "",
            "assegnato_a":           r.get("assegnato_a_principale") or None,
            "scadenza":              val_date(r.get("scadenza", "")),
            "stato":                 stato_task_map.get(stato_raw, "In corso"),
            "motivazione_blocco":    r.get("motivazione_blocco") or None,
            "stima_ore_interne":     val_num(r.get("stima_ore_interne", "")) or 0,
            "ore_consuntive_interne": val_num(r.get("ore_consuntive_interne", "")) or 0,
            "costo_task_esterno":    val_num(r.get("costo_task_esterno", "")) or 0,
            "ordine_in_scheda":      int(r["ordine_in_scheda"]) if r.get("ordine_in_scheda") else None,
            "id_prestazione_catalogo": r.get("id_prestazione_catalogo") or None,
            "descrizione_libera":    val_bool(r.get("descrizione_libera", "FALSE")),
            "priorita":              r.get("priorita") or None,
            "approvato_admin":       val_bool(r.get("approvato_admin", "FALSE")),
            "spese_task_excel":      val_num(r.get("spese_task_excel", "")) or 0,
            "incarico_excel":        val_num(r.get("incarico_excel", "")) or 0,
            "note":                  r.get("note") or None,
        })
    return upsert("task", payload)


def import_assegnazioni(righe: list[dict]) -> int:
    payload = []
    for r in righe:
        payload.append({
            "id":               r["id_assegnazione"],
            "id_task":          r["id_task"],
            "id_commessa":      r.get("id_commessa") or None,
            "id_utente":        r.get("id_utente") or None,
            "nome_raw":         r.get("nome_raw") or None,
            "tipo_assegnazione": r.get("tipo_assegnazione") or None,
            "ruolo_operativo":  r.get("ruolo_operativo") or None,
            "ordine":           int(r["ordine"]) if r.get("ordine") else 1,
            "note":             r.get("note") or None,
        })
    return upsert("assegnazioni_task", payload)


def import_contratti(righe: list[dict]) -> int:
    payload = []
    for r in righe:
        payload.append({
            "id":              r["id_contratto"],
            "id_commessa":     r["id_commessa"],
            "codice_commessa": r.get("codice_commessa") or None,
            "stato":           r.get("stato") or None,
            "data_contratto":  val_date(r.get("data_contratto", "")),
            "importo":         val_num(r.get("importo_contratto", "")),
            "note":            r.get("note") or None,
            "file_url":        r.get("file_url") or None,
        })
    return upsert("contratti", payload)


def import_sal(righe: list[dict]) -> int:
    payload = []
    for r in righe:
        payload.append({
            "id":               r["id_sal"],
            "id_commessa":      r["id_commessa"],
            "codice_commessa":  r.get("codice_commessa") or None,
            "sezione":          r.get("sezione") or None,
            "fase":             r.get("fase") or None,
            "ordine":           int(r["ordine"]) if r.get("ordine") else None,
            "tipo_riga":        r.get("tipo_riga") or None,
            "importo_previsto": val_num(r.get("importo_previsto", "")),
            "importo_fatturato": val_num(r.get("importo_fatturato", "")),
            "importo_pagato":   val_num(r.get("importo_pagato", "")),
            "stato":            r.get("stato") or None,
            "note":             r.get("note") or None,
        })
    return upsert("sal_commessa", payload)


def import_spese(righe: list[dict]) -> int:
    payload = []
    for r in righe:
        payload.append({
            "id":              r["id_spesa"],
            "id_commessa":     r.get("id_commessa") or None,
            "codice_commessa": r.get("codice_commessa") or None,
            "id_task":         r.get("id_task") or None,
            "id_sal":          r.get("id_sal") or None,
            "data_spesa":      val_date(r.get("data_spesa", "")),
            "descrizione":     r.get("descrizione") or None,
            "categoria":       r.get("categoria") or None,
            "importo":         val_num(r.get("importo", "")),
            "pagata":          val_bool(r.get("pagata", "FALSE")),
            "note":            r.get("note") or None,
        })
    return upsert("spese", payload)


def import_note(righe: list[dict]) -> int:
    payload = []
    for r in righe:
        payload.append({
            "id":          r["id_nota"],
            "id_commessa": r["id_commessa"],
            "tipo_nota":   r.get("tipo_nota") or None,
            "contenuto":   r.get("contenuto") or None,
            "origine":     r.get("origine") or None,
        })
    return upsert("note_commessa", payload)


# ---------------------------------------------------------------------------
# Aggiornamento assegnato_a principale sui task
# ---------------------------------------------------------------------------

def aggiorna_assegnato_principale(assegnazioni: list[dict]) -> int:
    """
    Per ogni task imposta assegnato_a = nome del primo assegnatario (ordine=1).
    """
    # Raggruppa per id_task, prende ordine minimo
    per_task: dict[str, str] = {}
    for r in sorted(assegnazioni, key=lambda x: int(x.get("ordine") or 99)):
        tid = r.get("id_task", "")
        if tid and tid not in per_task and (r.get("nome_raw") or "").strip():
            per_task[tid] = r["nome_raw"].strip()

    aggiornati = 0
    for id_task, nome in per_task.items():
        # L'id_task nel CSV è come "T824_001" → nel DB il task non ha questo id
        # Il link è tramite commessa_ref + ordine_in_scheda
        # Usiamo il campo commessa_ref estratto dal prefisso: T824 → commessa 824
        # e ordine = numero finale: T824_001 → ordine 1
        try:
            parti = id_task.lstrip("T").split("_")
            codice_comm = parti[0]
            ordine = int(parti[1])
        except (ValueError, IndexError):
            continue

        res = CLIENT.patch(
            f"{URL}/rest/v1/task"
            f"?commessa_ref=eq.{codice_comm}&ordine_in_scheda=eq.{ordine}",
            headers={**HEADERS, "Prefer": ""},
            json={"assegnato_a": nome},
        )
        if res.status_code in (200, 204):
            aggiornati += 1

    return aggiornati


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Import Esportazione 800 → Supabase")
    parser.add_argument(
        "--csv-dir",
        default=".",
        help="Cartella contenente i CSV dell'esportazione (default: directory corrente)",
    )
    parser.add_argument(
        "--skip-utenti",
        action="store_true",
        help="Salta l'import degli utenti (se già presenti nel DB)",
    )
    args = parser.parse_args()

    base = Path(args.csv_dir)

    # Mappa file → funzione di import
    passi = [
        ("clienti.csv",              import_clienti,   "clienti"),
        ("catalogo_prestazioni.csv", import_catalogo,  "catalogo_prestazioni"),
        ("commesse.csv",             import_commesse,  "commesse"),
        ("task.csv",                 import_task,      "task"),
        ("assegnazioni_task.csv",    import_assegnazioni, "assegnazioni_task"),
        ("contratti.csv",            import_contratti, "contratti"),
        ("sal_commessa.csv",         import_sal,       "sal_commessa"),
        ("spese.csv",                import_spese,     "spese"),
        ("note_commessa.csv",        import_note,      "note_commessa"),
    ]

    if not args.skip_utenti:
        passi.insert(0, ("utenti_collaboratori.csv", import_utenti, "utenti"))

    print(f"\n{'='*55}")
    print(f"  IMPORT ESPORTAZIONE 800 → Supabase")
    print(f"  CSV dir: {base.resolve()}")
    print(f"{'='*55}\n")

    for nome_file, fn, label in passi:
        percorso = base / nome_file
        if not percorso.exists():
            print(f"  ⚠  {nome_file} non trovato – saltato")
            continue
        righe = leggi_csv(percorso)
        n = fn(righe)
        stampa(label, n)

    # Aggiorna assegnato_a principale sui task
    assegnazioni_path = base / "assegnazioni_task.csv"
    if assegnazioni_path.exists():
        assegnazioni = leggi_csv(assegnazioni_path)
        n_agg = aggiorna_assegnato_principale(assegnazioni)
        stampa("task.assegnato_a aggiornati", n_agg)

    print(f"\n{'='*55}")
    print("  Import completato.")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
