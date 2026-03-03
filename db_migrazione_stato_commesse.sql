-- Migrazione stato commesse (idempotente)
-- Esegue:
-- 1) aggiunta colonna `stato` se assente
-- 2) normalizzazione valori null/vuoti
-- 3) vincolo valori ammessi
-- 4) backfill stato in base ai task esistenti

ALTER TABLE commesse
ADD COLUMN IF NOT EXISTS stato TEXT;

UPDATE commesse
SET stato = 'Aperto'
WHERE stato IS NULL OR btrim(stato) = '';

ALTER TABLE commesse
ALTER COLUMN stato SET DEFAULT 'Aperto';

ALTER TABLE commesse
ALTER COLUMN stato SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'commesse_stato_check'
    ) THEN
        ALTER TABLE commesse
        ADD CONSTRAINT commesse_stato_check
        CHECK (stato IN ('Aperto', 'Bloccato', 'Concluso'));
    END IF;
END
$$;

-- Backfill da task -> commesse
-- Regole:
-- - Se tutti i task sono Completato -> Concluso
-- - Se almeno un task è Bloccato -> Bloccato
-- - Altrimenti -> Aperto
-- - Se non ci sono task -> Aperto
WITH agg AS (
    SELECT
        c.id,
        COUNT(t.id) AS task_tot,
        BOOL_AND(t.stato = 'Completato') AS tutti_completati,
        BOOL_OR(t.stato = 'Bloccato') AS almeno_bloccato
    FROM commesse c
    LEFT JOIN task t ON t.commessa_ref = c.codice
    GROUP BY c.id
)
UPDATE commesse c
SET stato = CASE
    WHEN agg.task_tot = 0 THEN 'Aperto'
    WHEN agg.tutti_completati THEN 'Concluso'
    WHEN agg.almeno_bloccato THEN 'Bloccato'
    ELSE 'Aperto'
END
FROM agg
WHERE c.id = agg.id;
