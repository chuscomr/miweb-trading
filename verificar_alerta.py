import sqlite3

con = sqlite3.connect('alertas/alertas.db')
cur = con.cursor()

cur.execute("SELECT ticker, tipo, nivel, activa FROM alertas")
print("=== ALERTAS GUARDADAS ===")
for row in cur.fetchall():
    print(f"{row[0]} | {row[1]} | {row[2]}€ | Activa: {row[3]}")

cur.execute("SELECT COUNT(*) FROM alertas")
print(f"\nTotal: {cur.fetchone()[0]} alertas")

con.close()