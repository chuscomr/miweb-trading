import sqlite3
import os

DB_PATH = "alertas/alertas.db"

# Crear carpeta si no existe
os.makedirs("alertas", exist_ok=True)

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

# Crear tabla alertas
cur.execute("""
    CREATE TABLE IF NOT EXISTS alertas (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker          TEXT    NOT NULL,
        nombre          TEXT,
        tipo            TEXT    NOT NULL,
        nivel           REAL,
        umbral          REAL,
        descripcion     TEXT,
        activa          INTEGER NOT NULL DEFAULT 1,
        disparada       INTEGER NOT NULL DEFAULT 0,
        fecha_creacion  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
        fecha_disparo   TEXT,
        precio_disparo  REAL,
        notas           TEXT
    )
""")

con.commit()
print("✅ Tabla 'alertas' creada correctamente")

# Verificar
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alertas'")
if cur.fetchone():
    print("✅ Verificación exitosa: tabla existe")
    
    # Mostrar estructura
    cur.execute("PRAGMA table_info(alertas)")
    print("\n=== ESTRUCTURA ===")
    for col in cur.fetchall():
        print(f"  {col[1]} ({col[2]})")
else:
    print("❌ Error: tabla no se creó")

con.close()