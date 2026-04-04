import sqlite3
conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()
c.execute('PRAGMA table_info(core_medicamento);')
for row in c.fetchall():
    print(row)
conn.close()
