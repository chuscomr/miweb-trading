#!/usr/bin/env python3
"""
Script de migración: Añadir columna 'sistema' a tabla posiciones
Ejecutar: python migrar_cartera_sistema.py
"""

import os
import sqlite3


DB_PATH = "cartera/cartera.db"

def migrar():
    if not os.path.exists(DB_PATH):
        print(f"❌ No se encuentra {DB_PATH}")
        return

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Verificar si ya existe la columna
    cur.execute("PRAGMA table_info(posiciones)")
    columnas = [row[1] for row in cur.fetchall()]

    if "sistema" in columnas:
        print("✅ La columna 'sistema' ya existe")
    else:
        print("📝 Añadiendo columna 'sistema' a tabla posiciones...")
        try:
            cur.execute("""
                ALTER TABLE posiciones 
                ADD COLUMN sistema TEXT NOT NULL DEFAULT 'SWING'
            """)
            con.commit()
            print("✅ Columna 'sistema' añadida correctamente")

            # Mostrar estadísticas
            cur.execute("SELECT COUNT(*) FROM posiciones WHERE estado='ABIERTA'")
            abiertas = cur.fetchone()[0]
            print(f"   📊 {abiertas} posiciones abiertas ahora tienen sistema='SWING' por defecto")

        except sqlite3.OperationalError as e:
            print(f"❌ Error: {e}")

    con.close()
    print("\n🎯 Ahora puedes editar el sistema de cada posición desde la interfaz")

if __name__ == "__main__":
    print("="*60)
    print("MIGRACIÓN: Añadir columna 'sistema' a cartera")
    print("="*60)
    migrar()
    print("="*60)
