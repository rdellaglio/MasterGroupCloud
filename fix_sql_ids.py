"""
Corregge import_800_data.sql:
- commesse: rimuove 'id' (intero auto-gen), usa WHERE NOT EXISTS su codice
- task: rimuove 'id' (intero auto-gen), aggiunge commessa_ref, usa WHERE NOT EXISTS
"""

import re

with open("import_800_data.sql", "r", encoding="utf-8") as f:
    content = f.read()

lines = content.splitlines()
out = []

for line in lines:
    # ── COMMESSE ──────────────────────────────────────────────────────────────
    # Prima: INSERT INTO commesse (id, codice, ...) VALUES ('C824', '824', ...) ON CONFLICT (id) DO NOTHING;
    # Dopo:  INSERT INTO commesse (codice, ...) SELECT '824', ... WHERE NOT EXISTS (SELECT 1 FROM commesse WHERE codice='824');
    m_c = re.match(
        r"INSERT INTO commesse \(id, (.+?)\) VALUES \('C\d+', '(\d+)', (.+?)\) ON CONFLICT \(id\) DO NOTHING;",
        line
    )
    if m_c:
        cols   = m_c.group(1)          # "codice, cliente, ..."
        codice = m_c.group(2)          # "824"
        vals   = m_c.group(3)          # "'ILE DE BEAUTE SRL', ..."
        new = (
            f"INSERT INTO commesse ({cols}) "
            f"SELECT '{codice}', {vals} "
            f"WHERE NOT EXISTS (SELECT 1 FROM commesse WHERE codice = '{codice}');"
        )
        out.append(new)
        continue

    # ── TASK ──────────────────────────────────────────────────────────────────
    # Prima: INSERT INTO task (id, id_commessa, codice_commessa, ordine_in_scheda, ...) VALUES ('T824_001', 'C824', '824', 1, ...) ON CONFLICT (id) DO NOTHING;
    # Dopo:  INSERT INTO task (commessa_ref, id_commessa, codice_commessa, ordine_in_scheda, ...) SELECT '824', 'C824', '824', 1, ... WHERE NOT EXISTS (SELECT 1 FROM task WHERE commessa_ref='824' AND ordine_in_scheda=1);
    m_t = re.match(
        r"INSERT INTO task \(id, id_commessa, codice_commessa, ordine_in_scheda, (.+?)\) VALUES \('T\d+_\d+', '(C\d+)', '(\d+)', (\d+), (.+?)\) ON CONFLICT \(id\) DO NOTHING;",
        line
    )
    if m_t:
        extra_cols  = m_t.group(1)   # "id_prestazione_catalogo, descrizione, ..."
        id_commessa = m_t.group(2)   # "C824"
        codice_c    = m_t.group(3)   # "824"
        ordine      = m_t.group(4)   # "1"
        extra_vals  = m_t.group(5)   # "'P001', 'STUDIO DI FATTIBILITA''', ..."
        new = (
            f"INSERT INTO task (commessa_ref, id_commessa, codice_commessa, ordine_in_scheda, {extra_cols}) "
            f"SELECT '{codice_c}', '{id_commessa}', '{codice_c}', {ordine}, {extra_vals} "
            f"WHERE NOT EXISTS (SELECT 1 FROM task WHERE commessa_ref = '{codice_c}' AND ordine_in_scheda = {ordine});"
        )
        out.append(new)
        continue

    out.append(line)

result = "\n".join(out)
with open("import_800_data.sql", "w", encoding="utf-8") as f:
    f.write(result)

# Verifica
commesse_ok = result.count("INSERT INTO commesse (codice,")
task_ok     = result.count("INSERT INTO task (commessa_ref,")
commesse_bad = result.count("INSERT INTO commesse (id,")
task_bad     = result.count("INSERT INTO task (id,")

print(f"commesse corrette:  {commesse_ok}  (bad: {commesse_bad})")
print(f"task corrette:      {task_ok}  (bad: {task_bad})")
print("Fatto." if commesse_bad == 0 and task_bad == 0 else "ATTENZIONE: righe non corrette trovate!")
