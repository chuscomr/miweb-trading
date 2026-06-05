# Test directo de la función crear_alerta
import sys
sys.path.insert(0, 'D:\\a\\MiWeb')

from alertas.alertas_db import AlertasDB

db = AlertasDB()

print("=== TEST CREAR ALERTA ===")

try:
    alerta_id = db.crear_alerta(
        ticker="TEST.MC",
        tipo="OBJETIVO",
        nivel=10.50,
        nombre="Test",
        descripcion="Prueba"
    )
    print(f"✅ Alerta creada con ID: {alerta_id}")
    
    # Verificar que se guardó
    import sqlite3
    con = sqlite3.connect('alertas/alertas.db')
    cur = con.cursor()
    cur.execute("SELECT * FROM alertas WHERE id = ?", (alerta_id,))
    alerta = cur.fetchone()
    
    if alerta:
        print(f"✅ Verificado: alerta existe en BD")
        print(f"   Ticker: {alerta[1]}")
        print(f"   Tipo: {alerta[3]}")
        print(f"   Nivel: {alerta[4]}")
    else:
        print("❌ ERROR: alerta no se encuentra en BD")
    
    con.close()
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()