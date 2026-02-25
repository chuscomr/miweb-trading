"""
migrar_stop_original.py
Script para agregar la columna stop_original a posiciones existentes
"""

import sqlite3

DB_PATH = "cartera.db"

print("🔧 Iniciando migración de base de datos...")

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verificar si la columna ya existe
    cursor.execute("PRAGMA table_info(posiciones)")
    columnas = [col[1] for col in cursor.fetchall()]
    
    if 'stop_original' in columnas:
        print("✅ La columna 'stop_original' ya existe. No es necesario migrar.")
    else:
        print("📝 Agregando columna 'stop_original'...")
        
        # Agregar columna stop_original
        cursor.execute("""
            ALTER TABLE posiciones 
            ADD COLUMN stop_original REAL
        """)
        
        # Para posiciones existentes, copiar stop_loss actual como stop_original
        cursor.execute("""
            UPDATE posiciones 
            SET stop_original = stop_loss 
            WHERE stop_original IS NULL
        """)
        
        conn.commit()
        
        # Verificar cuántas filas se actualizaron
        cursor.execute("SELECT COUNT(*) FROM posiciones WHERE stop_original IS NOT NULL")
        count = cursor.fetchone()[0]
        
        print(f"✅ Migración completada: {count} posiciones actualizadas")
        print("   - Columna 'stop_original' agregada")
        print("   - Stop original copiado desde stop_loss actual")
        print()
        print("ℹ️  NOTA: Para posiciones existentes, el stop_original será igual")
        print("   al stop_loss actual. A partir de ahora, el stop_original se")
        print("   guardará al crear nuevas posiciones y no cambiará al editar.")
    
    conn.close()
    print("\n✅ Migración finalizada correctamente")
    
except Exception as e:
    print(f"❌ Error durante la migración: {e}")
    print("   Por favor, revisa tu archivo cartera.db")

print("\nPuedes cerrar esta ventana y reiniciar tu servidor Flask.")
input("\nPresiona ENTER para continuar...")
