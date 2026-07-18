import sqlite3
conn = sqlite3.connect('goldbot_checkpoints.db')
schema = conn.execute("SELECT sql FROM sqlite_master WHERE name='analysis_history'").fetchone()
print('SCHEMA:', schema)
rows = conn.execute("SELECT * FROM analysis_history LIMIT 3").fetchall()
for r in rows:
    print(r)
count = conn.execute("SELECT COUNT(*) FROM analysis_history").fetchone()
print('TOTAL ROWS:', count)
conn.close()
