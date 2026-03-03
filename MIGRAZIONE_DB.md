# Aggiornamento DB (Supabase)

Per applicare la migrazione `db_migrazione_stato_commesse.sql` al database reale:

1. Apri Supabase → **SQL Editor**.
2. Crea una nuova query.
3. Incolla il contenuto di `db_migrazione_stato_commesse.sql`.
4. Esegui la query.

## Verifica rapida
Esegui poi:

```sql
SELECT stato, COUNT(*)
FROM commesse
GROUP BY stato
ORDER BY stato;
```

e:

```sql
SELECT column_name, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'commesse' AND column_name = 'stato';
```

Atteso:
- `stato` presente su `commesse`
- `NOT NULL`
- default `Aperto`
- valori solo `Aperto`, `Bloccato`, `Concluso`.

## Ripopolamento dati demo (commesse + task)
Per fare debug rapido con dati fittizi, puoi usare lo script:

```bash
python scripts/reseed_demo_data.py
```

Prerequisiti (variabili ambiente):

```bash
export SUPABASE_URL='https://<project>.supabase.co'
export SUPABASE_KEY='<service-role-or-anon-key>'
```

Cosa fa lo script:
- elimina i dati esistenti in `task` e `commesse`;
- inserisce **50 commesse** con nomi/clienti di fantasia;
- inserisce **200 task** (4 per commessa) con attività/stati casuali di fantasia.
