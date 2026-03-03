-- Migrazione supporto blocco task (idempotente)
-- Aggiunge il campo motivazione blocco su tabella task.

ALTER TABLE task
ADD COLUMN IF NOT EXISTS motivazione_blocco TEXT;
