-- Aggiunge classificazione interno/esterno agli utenti
ALTER TABLE utenti
ADD COLUMN IF NOT EXISTS interno_esterno TEXT;

-- Valorizza record esistenti con default operativo
UPDATE utenti
SET interno_esterno = 'Interno'
WHERE interno_esterno IS NULL;

-- Vincoli di qualità dato
ALTER TABLE utenti
ALTER COLUMN interno_esterno SET NOT NULL,
ALTER COLUMN interno_esterno SET DEFAULT 'Interno';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'utenti_interno_esterno_check'
    ) THEN
        ALTER TABLE utenti
        ADD CONSTRAINT utenti_interno_esterno_check
        CHECK (interno_esterno IN ('Interno', 'Esterno'));
    END IF;
END;
$$;
