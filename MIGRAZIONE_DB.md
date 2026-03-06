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


## Migrazione blocco task + motivazione
Per abilitare la motivazione obbligatoria quando un task va in **Bloccato**, esegui anche:

1. Apri Supabase → **SQL Editor**.
2. Crea una nuova query.
3. Incolla il contenuto di `db_migrazione_blocco_task.sql`.
4. Esegui la query.

Verifica rapida:

> Se vedi l'errore `PGRST204` su `motivazione_blocco`, significa che la migrazione non è stata applicata nel DB corrente.
> L'app ora aggiorna comunque lo stato task, ma devi eseguire `db_migrazione_blocco_task.sql` per salvare la motivazione su DB.


```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'task' AND column_name = 'motivazione_blocco';
```

## Configurazione manuale notifiche email
Aggiungi in `.streamlit/secrets.toml` (o variabili ambiente) i seguenti parametri:

```toml
SMTP_HOST = "smtp.tuodominio.it"
SMTP_PORT = 587
SMTP_USER = "noreply@tuodominio.it"
SMTP_PASSWORD = "<password-o-app-password>"
SMTP_FROM = "noreply@tuodominio.it"
SMTP_USE_TLS = true
# opzionale: forza un solo admin destinatario
NOTIFY_ADMIN_EMAIL = "admin@tuodominio.it"
```

> Nota: i destinatari vengono presi automaticamente dalla tabella `utenti`:
> - PM della commessa (`commesse.pm_assegnato`)
> - tutti gli utenti con ruolo `Admin`
> 
> Assicurati che la colonna `email` sia valorizzata per questi utenti.

## Configurazione manuale AI con Hugging Face (step-by-step)
Per usare Hugging Face come provider AI (sia dashboard che corpo email), segui questi passi:

1. Crea o accedi al tuo account su Hugging Face.
2. Vai in **Settings → Access Tokens** e crea un token con permessi di inferenza.
3. Scegli un modello chat compatibile (esempio: `meta-llama/Llama-3.1-8B-Instruct`).
4. Nel file `.streamlit/secrets.toml` inserisci:

```toml
AI_PROVIDER = "huggingface"
HUGGINGFACE_API_KEY = "hf_xxx"
HUGGINGFACE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
# opzionale (default già impostato in codice)
HUGGINGFACE_API_URL = "https://router.huggingface.co/v1/chat/completions"
```

5. Riavvia l'app Streamlit.
6. Fai un test pratico:
   - apri un task,
   - imposta stato `Bloccato`,
   - inserisci motivazione,
   - verifica che il testo email venga generato e inviato a PM/Admin.

### Alternativa: provider OpenAI-compatible
Se non vuoi usare Hugging Face, puoi continuare con endpoint compatibile OpenAI:

```toml
AI_PROVIDER = "openai_compatible"
AI_API_URL = "https://.../chat/completions"
AI_API_KEY = "<chiave-api>"
AI_MODEL = "gpt-4o-mini"
```

Se AI non è configurata, il sistema invia testo fallback statico.


## Routine invio mail blocco task
La notifica email parte automaticamente **solo quando il task passa da uno stato diverso a `Bloccato`**.
Se il task è già `Bloccato` e viene salvato di nuovo, l'app evita invii duplicati.


## Ricerca e ordinamento in Analisi Commesse
- È disponibile la ricerca per **codice**, **cliente** e **PM**.
- Il PM incaricato è visibile direttamente nella card/expander commessa.
- Ordinamento di default: commesse più recenti prima (se esiste un timestamp `created_at` o equivalente), altrimenti ordinamento per prefisso numerico del codice commessa in ordine decrescente.


## Struttura contenuto email blocco
La mail contiene sempre un riepilogo tabellare iniziale con i dati minimi utili al PM:
- Commessa
- Cliente
- Task
- Operatore
- Data/Ora segnalazione
- Motivazione del blocco

Segue una comunicazione sintetica in stile operatore → PM con:
- impatto operativo del blocco
- proposta di azioni concrete per lo sblocco

## Destinatari notifica blocco
- 1 solo PM: quello assegnato nella commessa (`pm_assegnato`)
