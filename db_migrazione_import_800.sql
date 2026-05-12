-- =============================================================
-- MIGRAZIONE: allineamento DB per import Esportazione 800
-- File sorgente: 08_da 800 a 899_maggio 2026.xlsx
-- 16 commesse | 584 task | 78 assegnazioni | 217 SAL | ...
-- Idempotente: usa ADD COLUMN IF NOT EXISTS / CREATE TABLE IF NOT EXISTS
-- =============================================================


-- =============================================================
-- 1. ESTENSIONE TABELLA commesse
-- =============================================================

ALTER TABLE commesse ADD COLUMN IF NOT EXISTS titolo               TEXT;
ALTER TABLE commesse ADD COLUMN IF NOT EXISTS oggetto              TEXT;
ALTER TABLE commesse ADD COLUMN IF NOT EXISTS indirizzo_intervento TEXT;
ALTER TABLE commesse ADD COLUMN IF NOT EXISTS area_pratica         TEXT;
ALTER TABLE commesse ADD COLUMN IF NOT EXISTS tipo_pratica         TEXT;
ALTER TABLE commesse ADD COLUMN IF NOT EXISTS importo_contratto    NUMERIC(12,2);
ALTER TABLE commesse ADD COLUMN IF NOT EXISTS contratto_stato      TEXT;
ALTER TABLE commesse ADD COLUMN IF NOT EXISTS totale_fatturato     NUMERIC(12,2) DEFAULT 0;
ALTER TABLE commesse ADD COLUMN IF NOT EXISTS totale_pagato        NUMERIC(12,2) DEFAULT 0;
ALTER TABLE commesse ADD COLUMN IF NOT EXISTS totale_spese         NUMERIC(12,2) DEFAULT 0;
ALTER TABLE commesse ADD COLUMN IF NOT EXISTS cassa                NUMERIC(12,2);
ALTER TABLE commesse ADD COLUMN IF NOT EXISTS note                 TEXT;


-- =============================================================
-- 2. ESTENSIONE TABELLA task
-- =============================================================

ALTER TABLE task ADD COLUMN IF NOT EXISTS id_commessa             TEXT;
ALTER TABLE task ADD COLUMN IF NOT EXISTS codice_commessa         TEXT;
ALTER TABLE task ADD COLUMN IF NOT EXISTS ordine_in_scheda       INTEGER;
ALTER TABLE task ADD COLUMN IF NOT EXISTS id_prestazione_catalogo TEXT;
ALTER TABLE task ADD COLUMN IF NOT EXISTS descrizione_libera      BOOLEAN DEFAULT FALSE;
ALTER TABLE task ADD COLUMN IF NOT EXISTS priorita               TEXT;
ALTER TABLE task ADD COLUMN IF NOT EXISTS approvato_admin         BOOLEAN DEFAULT FALSE;
ALTER TABLE task ADD COLUMN IF NOT EXISTS motivazione_blocco      TEXT;
ALTER TABLE task ADD COLUMN IF NOT EXISTS stima_ore_interne       NUMERIC(8,2) DEFAULT 0;
ALTER TABLE task ADD COLUMN IF NOT EXISTS ore_consuntive_interne  NUMERIC(8,2) DEFAULT 0;
ALTER TABLE task ADD COLUMN IF NOT EXISTS costo_task_esterno      NUMERIC(12,2) DEFAULT 0;
ALTER TABLE task ADD COLUMN IF NOT EXISTS spese_task_excel        NUMERIC(12,2) DEFAULT 0;
ALTER TABLE task ADD COLUMN IF NOT EXISTS incarico_excel          NUMERIC(12,2) DEFAULT 0;
ALTER TABLE task ADD COLUMN IF NOT EXISTS note                    TEXT;

CREATE INDEX IF NOT EXISTS idx_task_id_commessa_800
    ON task(id_commessa);

CREATE INDEX IF NOT EXISTS idx_task_commessa_ordine_800
    ON task(commessa_ref, ordine_in_scheda);

CREATE OR REPLACE FUNCTION normalize_task_import_800_defaults()
RETURNS trigger AS $$
BEGIN
    NEW.stato := COALESCE(NULLIF(BTRIM(NEW.stato), ''), 'In corso');
    NEW.descrizione_libera := COALESCE(NEW.descrizione_libera, FALSE);
    NEW.approvato_admin := COALESCE(NEW.approvato_admin, FALSE);
    NEW.stima_ore_interne := COALESCE(NEW.stima_ore_interne, 0);
    NEW.ore_consuntive_interne := COALESCE(NEW.ore_consuntive_interne, 0);
    NEW.costo_task_esterno := COALESCE(NEW.costo_task_esterno, 0);
    NEW.spese_task_excel := COALESCE(NEW.spese_task_excel, 0);
    NEW.incarico_excel := COALESCE(NEW.incarico_excel, 0);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_task_import_800_defaults ON task;
CREATE TRIGGER trg_task_import_800_defaults
BEFORE INSERT OR UPDATE ON task
FOR EACH ROW
EXECUTE FUNCTION normalize_task_import_800_defaults();


-- =============================================================
-- 3. NUOVA TABELLA: clienti
-- =============================================================

CREATE TABLE IF NOT EXISTS clienti (
    id              TEXT PRIMARY KEY,
    denominazione   TEXT NOT NULL,
    tipo_cliente    TEXT,
    codice_fiscale  TEXT,
    partita_iva     TEXT,
    email           TEXT,
    telefono        TEXT,
    indirizzo       TEXT,
    note            TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);


-- =============================================================
-- 4. NUOVA TABELLA: catalogo_prestazioni
-- =============================================================

CREATE TABLE IF NOT EXISTS catalogo_prestazioni (
    id                  TEXT PRIMARY KEY,
    codice              TEXT,
    descrizione         TEXT NOT NULL,
    categoria           TEXT,
    area_pratica        TEXT,
    attiva              BOOLEAN DEFAULT TRUE,
    ordinamento         INTEGER,
    chiave_normalizzata TEXT
);


-- =============================================================
-- 5. NUOVA TABELLA: assegnazioni_task
--    Supporta più assegnatari per singolo task
-- =============================================================

CREATE TABLE IF NOT EXISTS assegnazioni_task (
    id                TEXT PRIMARY KEY,
    id_task           TEXT NOT NULL,
    id_commessa       TEXT,
    id_utente         TEXT,
    nome_raw          TEXT,
    tipo_assegnazione TEXT,   -- 'Interno' | 'Interno 2' | 'Esterno'
    ruolo_operativo   TEXT,
    ordine            INTEGER DEFAULT 1,
    note              TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assegnazioni_task_id_task
    ON assegnazioni_task(id_task);

CREATE INDEX IF NOT EXISTS idx_assegnazioni_task_id_commessa
    ON assegnazioni_task(id_commessa);


-- =============================================================
-- 6. NUOVA TABELLA: contratti
-- =============================================================

CREATE TABLE IF NOT EXISTS contratti (
    id               TEXT PRIMARY KEY,
    id_commessa      TEXT NOT NULL,
    codice_commessa  TEXT,
    stato            TEXT,
    data_contratto   DATE,
    importo          NUMERIC(12,2),
    note             TEXT,
    file_url         TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contratti_id_commessa
    ON contratti(id_commessa);


-- =============================================================
-- 7. NUOVA TABELLA: sal_commessa
--    Fasi di fatturazione / SAL per commessa
-- =============================================================

CREATE TABLE IF NOT EXISTS sal_commessa (
    id               TEXT PRIMARY KEY,
    id_commessa      TEXT NOT NULL,
    codice_commessa  TEXT,
    sezione          TEXT,
    fase             TEXT,
    ordine           INTEGER,
    tipo_riga        TEXT,   -- 'fase' | 'contratto' | 'totale' | 'cassa'
    importo_previsto  NUMERIC(12,2),
    importo_fatturato NUMERIC(12,2),
    importo_pagato    NUMERIC(12,2),
    stato            TEXT,
    note             TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sal_commessa_id_commessa
    ON sal_commessa(id_commessa);


-- =============================================================
-- 8. NUOVA TABELLA: spese
-- =============================================================

CREATE TABLE IF NOT EXISTS spese (
    id               TEXT PRIMARY KEY,
    id_commessa      TEXT,
    codice_commessa  TEXT,
    id_task          TEXT,
    id_sal           TEXT,
    data_spesa       DATE,
    descrizione      TEXT,
    categoria        TEXT,
    importo          NUMERIC(12,2),
    pagata           BOOLEAN DEFAULT FALSE,
    note             TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_spese_id_commessa
    ON spese(id_commessa);


-- =============================================================
-- 9. NUOVA TABELLA: note_commessa
-- =============================================================

CREATE TABLE IF NOT EXISTS note_commessa (
    id          TEXT PRIMARY KEY,
    id_commessa TEXT NOT NULL,
    tipo_nota   TEXT,   -- 'Nota documentale' | 'Contabilità' | 'Nota operativa' | 'Anomalia assegnazione'
    contenuto   TEXT,
    origine     TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_note_commessa_id_commessa
    ON note_commessa(id_commessa);


-- =============================================================
-- VERIFICA RAPIDA (eseguire dopo la migrazione)
-- =============================================================
-- SELECT column_name, data_type
-- FROM information_schema.columns
-- WHERE table_name IN ('commesse','task')
--   AND column_name IN (
--       'titolo','oggetto','area_pratica','importo_contratto',
--       'id_commessa','codice_commessa','ordine_in_scheda',
--       'id_prestazione_catalogo','priorita','stima_ore_interne'
--   )
-- ORDER BY table_name, column_name;
--
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public'
--   AND table_name IN (
--     'clienti','catalogo_prestazioni','assegnazioni_task',
--     'contratti','sal_commessa','spese','note_commessa'
--   )
-- ORDER BY table_name;
