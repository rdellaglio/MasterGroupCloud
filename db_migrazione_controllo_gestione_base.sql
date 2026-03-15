-- Migrazione controllo gestione base (idempotente)
-- Obiettivo:
-- 1) Interni: costo orario + ore rendicontate su task
-- 2) Esterni: costo task fisso

-- =========================
-- UTENTI
-- =========================
ALTER TABLE utenti
ADD COLUMN IF NOT EXISTS costo_orario NUMERIC(10,2);

UPDATE utenti
SET costo_orario = 30.00
WHERE costo_orario IS NULL;

ALTER TABLE utenti
ALTER COLUMN costo_orario SET NOT NULL,
ALTER COLUMN costo_orario SET DEFAULT 30.00;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'utenti_costo_orario_nonneg_check'
    ) THEN
        ALTER TABLE utenti
        ADD CONSTRAINT utenti_costo_orario_nonneg_check
        CHECK (costo_orario >= 0);
    END IF;
END;
$$;

-- =========================
-- TASK
-- =========================
ALTER TABLE task
ADD COLUMN IF NOT EXISTS stima_ore_interne NUMERIC(8,2),
ADD COLUMN IF NOT EXISTS ore_consuntive_interne NUMERIC(8,2),
ADD COLUMN IF NOT EXISTS costo_task_esterno NUMERIC(12,2);

UPDATE task
SET stima_ore_interne = 0
WHERE stima_ore_interne IS NULL;

UPDATE task
SET ore_consuntive_interne = 0
WHERE ore_consuntive_interne IS NULL;

UPDATE task
SET costo_task_esterno = 0
WHERE costo_task_esterno IS NULL;

ALTER TABLE task
ALTER COLUMN stima_ore_interne SET NOT NULL,
ALTER COLUMN stima_ore_interne SET DEFAULT 0,
ALTER COLUMN ore_consuntive_interne SET NOT NULL,
ALTER COLUMN ore_consuntive_interne SET DEFAULT 0,
ALTER COLUMN costo_task_esterno SET NOT NULL,
ALTER COLUMN costo_task_esterno SET DEFAULT 0;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'task_stima_ore_interne_nonneg_check'
    ) THEN
        ALTER TABLE task
        ADD CONSTRAINT task_stima_ore_interne_nonneg_check
        CHECK (stima_ore_interne >= 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'task_ore_consuntive_interne_nonneg_check'
    ) THEN
        ALTER TABLE task
        ADD CONSTRAINT task_ore_consuntive_interne_nonneg_check
        CHECK (ore_consuntive_interne >= 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'task_costo_task_esterno_nonneg_check'
    ) THEN
        ALTER TABLE task
        ADD CONSTRAINT task_costo_task_esterno_nonneg_check
        CHECK (costo_task_esterno >= 0);
    END IF;
END;
$$;
