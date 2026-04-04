import sqlite3
conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()
try:
    meds = list(c.execute('SELECT id, usuario_id FROM core_medicamento'))
    print('Meds:', meds)
except Exception as e:
    print('Meds error:', e)
try:
    perfils = list(c.execute('SELECT id, user_id FROM core_perfil'))
    print('Perfils:', perfils)
except Exception as e:
    print('Perfils error:', e)
conn.close()
