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
