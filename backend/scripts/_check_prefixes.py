import sqlite3
from pathlib import Path
conn = sqlite3.connect(r'd:\testing2\backend\specmatch.db')
rows = conn.execute("SELECT standard_number FROM standards WHERE standard_number NOT LIKE 'IS %' LIMIT 12").fetchall()
for r in rows:
    print(repr(r[0]))
print('--- prefix counts ---')
rows = conn.execute("SELECT substr(standard_number,1,4) p, COUNT(*) c FROM standards GROUP BY p ORDER BY c DESC LIMIT 12").fetchall()
for p,c in rows:
    print(p, c)
