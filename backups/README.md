# Backup locali del codice

Questa cartella contiene snapshot versionati dei file principali dell'app prima delle modifiche.

## Script
Usa lo script:

```bash
./scripts/backup_versions.sh
```

## Comportamento
- Crea una cartella timestamp (`YYYYMMDD_HHMMSS`) dentro `backups/`.
- Salva una copia di:
  - `GestionaleMG.py`
  - `requirements.txt`
- Mantiene solo le ultime **4** versioni e rimuove automaticamente le più vecchie.
