-- ================================================================
-- FIX DATI IMPORT 800: rende i task visibili e funzionanti nel gestionale
-- Eseguire nell'SQL Editor di Supabase
-- Idempotente: può essere rieseguito senza danni
-- ================================================================

-- ================================================================
-- 1. STATO TASK: imposta 'In corso' dove NULL
--    (l'app filtra sul campo stato; NULL causa righe invisibili)
-- ================================================================
UPDATE task
SET stato = 'In corso'
WHERE stato IS NULL
  AND commessa_ref IN (
    '800','803','805','806','808','811','812',
    '814','817','818','819','820','821','822','823','824'
  );


-- ================================================================
-- 2. ASSEGNATO_A: copia il primo assegnatario da assegnazioni_task
--    Logica: id_task = 'T824_001' → commessa_ref='824', ordine_in_scheda=1
--    Aggiorna solo i task che hanno almeno un'assegnazione registrata
-- ================================================================
UPDATE task t
SET assegnato_a = (
    SELECT at.nome_raw
    FROM assegnazioni_task at
    WHERE
        -- estrae il codice commessa da 'T824_001' → '824'
        SUBSTRING(at.id_task, 2, POSITION('_' IN at.id_task) - 2) = t.commessa_ref
        -- estrae il numero ordine da '001' → 1
        AND CAST(SPLIT_PART(at.id_task, '_', 2) AS INTEGER) = t.ordine_in_scheda
        AND at.ordine = 1   -- solo il primo assegnatario (principale)
    LIMIT 1
)
WHERE t.commessa_ref IN (
    '800','803','805','806','808','811','812',
    '814','817','818','819','820','821','822','823','824'
)
AND t.assegnato_a IS NULL;


-- ================================================================
-- 3. FIX PM_ASSEGNATO: corregge la commessa 824 con valore errato
-- ================================================================
UPDATE commesse
SET pm_assegnato = NULL
WHERE codice = '824'
  AND pm_assegnato = 'La mail risale al 30 marzo 2026';


-- ================================================================
-- 4. VERIFICA RISULTATI
-- ================================================================
SELECT
    'task con stato NULL rimasti' AS check_name,
    COUNT(*) AS valore
FROM task
WHERE stato IS NULL
  AND commessa_ref IN (
    '800','803','805','806','808','811','812',
    '814','817','818','819','820','821','822','823','824'
  )

UNION ALL

SELECT
    'task con assegnato_a impostato',
    COUNT(*)
FROM task
WHERE assegnato_a IS NOT NULL
  AND commessa_ref IN (
    '800','803','805','806','808','811','812',
    '814','817','818','819','820','821','822','823','824'
  )

UNION ALL

SELECT
    'task totali importati',
    COUNT(*)
FROM task
WHERE commessa_ref IN (
    '800','803','805','806','808','811','812',
    '814','817','818','819','820','821','822','823','824'
  )

UNION ALL

SELECT
    'commesse 800-824 presenti',
    COUNT(*)
FROM commesse
WHERE codice IN (
    '800','803','805','806','808','811','812',
    '814','817','818','819','820','821','822','823','824'
);
