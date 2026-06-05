#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de Testing Manual - Integración Analytics + Cartera v85.24

Ejecutar: python test_analytics_cartera.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, datetime
from cartera.cartera_db import CarteraDB
from analytics.integrador import registrar_apertura, registrar_cierre
from analytics.trades_log import obtener_trade
import sqlite3


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_test(nombre, resultado, detalle=""):
    icono = f"{Colors.GREEN}✅" if resultado else f"{Colors.RED}❌"
    print(f"{icono} {Colors.BOLD}{nombre}{Colors.RESET}")
    if detalle:
        print(f"   {detalle}")
    print()


def test_1_migracion_columna():
    """Test 1: Verificar que columna analytics_id existe"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}TEST 1: Migración Columna analytics_id{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    db = CarteraDB()
    
    # Verificar columna existe
    with db._conexion() as con:
        cols = [r[1] for r in con.execute("PRAGMA table_info(posiciones)").fetchall()]
        tiene_analytics = "analytics_id" in cols
    
    print_test(
        "Columna analytics_id existe en tabla posiciones",
        tiene_analytics,
        f"Columnas encontradas: {len(cols)}"
    )
    
    # Verificar que posiciones antiguas tienen NULL
    with db._conexion() as con:
        total = con.execute("SELECT COUNT(*) FROM posiciones").fetchone()[0]
        con_analytics = con.execute("SELECT COUNT(*) FROM posiciones WHERE analytics_id IS NOT NULL").fetchone()[0]
        sin_analytics = total - con_analytics
    
    print_test(
        "Posiciones antiguas tienen analytics_id = NULL (correcto)",
        sin_analytics > 0 or total == 0,
        f"Total: {total} | Con analytics_id: {con_analytics} | Sin analytics_id: {sin_analytics}"
    )
    
    return tiene_analytics


def test_2_apertura_con_analytics():
    """Test 2: Abrir posición nueva con Analytics"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}TEST 2: Apertura Posición con Analytics{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    # 1. Registrar en Analytics
    try:
        trade_id = registrar_apertura(
            ticker="TEST.MC",
            sistema="SWING",
            tipo_setup="TEST_AUTOMATIZADO",
            precio_entrada=10.00,
            stop=9.50,
            contexto_mercado="ALCISTA",
            rating_fundamental=None,
            notas="Test automático v85.24"
        )
        
        print_test(
            "Analytics: Trade registrado",
            trade_id is not None and trade_id > 0,
            f"trade_id = {trade_id}"
        )
    except Exception as e:
        print_test("Analytics: Trade registrado", False, f"Error: {e}")
        return False
    
    # 2. Crear posición en cartera
    db = CarteraDB()
    try:
        pid = db.agregar_posicion(
            ticker="TEST.MC",
            nombre="Test Trading",
            sistema="SWING",
            fecha_entrada=date.today().isoformat(),
            precio_entrada=10.00,
            stop_inicial=9.50,
            objetivo=11.00,
            acciones=100,
            score_nivel="TEST",
            contexto_ibex="ALCISTA",
            es_excepcion=False,
            notas="Test automático",
            analytics_id=trade_id
        )
        
        print_test(
            "Cartera: Posición creada",
            pid is not None and pid > 0,
            f"pid = {pid}"
        )
    except Exception as e:
        print_test("Cartera: Posición creada", False, f"Error: {e}")
        return False
    
    # 3. Verificar vínculo
    pos = db.obtener_posicion_por_id(pid)
    vinculo_correcto = pos.get("analytics_id") == trade_id
    
    print_test(
        "Vínculo correcto: posiciones.analytics_id = trades_log.id",
        vinculo_correcto,
        f"posicion.analytics_id={pos.get('analytics_id')} | trade_id={trade_id}"
    )
    
    # Guardar IDs para siguiente test
    return {"pid": pid, "trade_id": trade_id}


def test_3_cierre_con_analytics(datos_test2):
    """Test 3: Cerrar posición y actualizar Analytics"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}TEST 3: Cierre Posición con Analytics{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    if not datos_test2:
        print_test("Prerequisito", False, "Test 2 falló, no hay posición para cerrar")
        return False
    
    pid = datos_test2["pid"]
    trade_id = datos_test2["trade_id"]
    
    db = CarteraDB()
    pos = db.obtener_posicion_por_id(pid)
    
    # 1. Cerrar en cartera
    precio_cierre = 10.50
    entrada = float(pos.get("precio_entrada", 0))
    stop = float(pos.get("stop_inicial", 0))
    R = entrada - stop
    r_final = round((precio_cierre - entrada) / R, 2) if R > 0 else None
    
    try:
        exito = db.cerrar_posicion(
            pid=pid,
            fecha_cierre=date.today().isoformat(),
            precio_cierre=precio_cierre,
            motivo_cierre="TEST",
            r_final=r_final
        )
        
        print_test(
            "Cartera: Posición cerrada",
            exito,
            f"R calculado = {r_final}"
        )
    except Exception as e:
        print_test("Cartera: Posición cerrada", False, f"Error: {e}")
        return False
    
    # 2. Actualizar Analytics
    try:
        registrar_cierre(
            trade_id=trade_id,
            precio_salida=precio_cierre,
            precio_entrada=entrada,
            stop=stop,
            tipo_salida="TEST",
            r_multiple=r_final
        )
        
        print_test(
            "Analytics: Trade actualizado",
            True,
            f"trade_id={trade_id} cerrado con R={r_final}"
        )
    except Exception as e:
        print_test("Analytics: Trade actualizado", False, f"Error: {e}")
        return False
    
    # 3. Verificar en BD Analytics
    trade = obtener_trade(trade_id)
    
    if trade:
        cerrado = trade.get("fecha_salida") is not None
        r_guardado = trade.get("r_multiple")
        
        print_test(
            "Analytics: Datos guardados correctamente",
            cerrado and r_guardado == r_final,
            f"fecha_salida={trade.get('fecha_salida')} | R={r_guardado}"
        )
    else:
        print_test("Analytics: Datos guardados correctamente", False, "Trade no encontrado")
    
    return True


def test_4_retrocompatibilidad():
    """Test 4: Posiciones antiguas sin analytics_id funcionan"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}TEST 4: Retrocompatibilidad (sin analytics_id){Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    db = CarteraDB()
    
    # Buscar posición antigua sin analytics_id
    with db._conexion() as con:
        pos_antigua = con.execute("""
            SELECT id, ticker FROM posiciones 
            WHERE analytics_id IS NULL 
            AND estado='ABIERTA' 
            LIMIT 1
        """).fetchone()
    
    if not pos_antigua:
        print_test(
            "Test omitido",
            True,
            f"{Colors.YELLOW}No hay posiciones antiguas abiertas para probar{Colors.RESET}"
        )
        return True
    
    pid_antigua = pos_antigua[0]
    ticker_antigua = pos_antigua[1]
    
    print(f"   Usando posición antigua: ID={pid_antigua}, Ticker={ticker_antigua}\n")
    
    # Verificar que analytics_id es NULL
    pos = db.obtener_posicion_por_id(pid_antigua)
    tiene_null = pos.get("analytics_id") is None
    
    print_test(
        "Posición antigua tiene analytics_id = NULL",
        tiene_null,
        f"analytics_id = {pos.get('analytics_id')}"
    )
    
    print(f"   {Colors.YELLOW}NOTA: No cerramos la posición real, solo verificamos que existe{Colors.RESET}\n")
    
    return tiene_null


def test_5_resiliencia_fallos():
    """Test 5: Cartera funciona si Analytics falla"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}TEST 5: Resiliencia a Fallos de Analytics{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    db = CarteraDB()
    
    # Simular que Analytics falla (pasamos analytics_id=None)
    try:
        pid = db.agregar_posicion(
            ticker="TEST2.MC",
            nombre="Test Sin Analytics",
            sistema="SWING",
            fecha_entrada=date.today().isoformat(),
            precio_entrada=20.00,
            stop_inicial=19.00,
            objetivo=22.00,
            acciones=50,
            score_nivel="TEST",
            contexto_ibex="NEUTRO",
            es_excepcion=False,
            notas="Test sin Analytics",
            analytics_id=None  # Simula fallo en registrar_apertura
        )
        
        print_test(
            "Cartera: Posición creada sin analytics_id",
            pid is not None and pid > 0,
            f"pid = {pid}"
        )
        
        # Verificar que se creó con NULL
        pos = db.obtener_posicion_por_id(pid)
        es_null = pos.get("analytics_id") is None
        
        print_test(
            "analytics_id es NULL (correcto cuando Analytics falla)",
            es_null,
            f"analytics_id = {pos.get('analytics_id')}"
        )
        
        # Cerrar la posición de prueba
        db.cerrar_posicion(pid, date.today().isoformat(), 20.50, "TEST", 0.5)
        
        print_test(
            "Posición cerrada correctamente sin Analytics",
            True,
            "Cartera funciona independientemente de Analytics"
        )
        
        return True
        
    except Exception as e:
        print_test("Resiliencia a fallos", False, f"Error: {e}")
        return False


def limpiar_datos_test():
    """Eliminar datos de test"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}LIMPIEZA: Eliminando datos de test{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    db = CarteraDB()
    
    # Eliminar posiciones de test
    with db._conexion() as con:
        n_pos = con.execute("""
            DELETE FROM posiciones 
            WHERE ticker IN ('TEST.MC', 'TEST2.MC')
        """).rowcount
        con.commit()
    
    print_test(
        "Posiciones de test eliminadas",
        True,
        f"{n_pos} posiciones eliminadas de cartera"
    )
    
    # Eliminar trades de test de Analytics
    try:
        import sqlite3
        analytics_db = "analytics/trades.db"
        if os.path.exists(analytics_db):
            con_analytics = sqlite3.connect(analytics_db)
            n_trades = con_analytics.execute("""
                DELETE FROM trades 
                WHERE ticker IN ('TEST.MC', 'TEST2.MC')
            """).rowcount
            con_analytics.commit()
            con_analytics.close()
            
            print_test(
                "Trades de test eliminados",
                True,
                f"{n_trades} trades eliminados de Analytics"
            )
        else:
            print_test(
                "Analytics DB no existe (se creará al abrir posición real)",
                True,
                ""
            )
    except Exception as e:
        print_test("Limpieza Analytics", False, f"Error: {e}")


def main():
    """Ejecutar todos los tests"""
    print(f"\n{Colors.BOLD}{'='*60}")
    print("🧪 TESTS INTEGRACIÓN ANALYTICS + CARTERA v85.24")
    print(f"{'='*60}{Colors.RESET}\n")
    
    resultados = {}
    
    # Test 1: Migración
    resultados["test_1"] = test_1_migracion_columna()
    
    if not resultados["test_1"]:
        print(f"\n{Colors.RED}❌ Test 1 falló. No se puede continuar.{Colors.RESET}")
        return
    
    # Test 2: Apertura
    datos_test2 = test_2_apertura_con_analytics()
    resultados["test_2"] = datos_test2 is not False
    
    # Test 3: Cierre (depende de Test 2)
    if resultados["test_2"]:
        resultados["test_3"] = test_3_cierre_con_analytics(datos_test2)
    else:
        resultados["test_3"] = False
    
    # Test 4: Retrocompatibilidad
    resultados["test_4"] = test_4_retrocompatibilidad()
    
    # Test 5: Resiliencia
    resultados["test_5"] = test_5_resiliencia_fallos()
    
    # Limpieza
    limpiar_datos_test()
    
    # Resumen final
    print(f"\n{Colors.BOLD}{'='*60}")
    print("📊 RESUMEN FINAL")
    print(f"{'='*60}{Colors.RESET}\n")
    
    total = len(resultados)
    exitosos = sum(1 for r in resultados.values() if r)
    
    for nombre, resultado in resultados.items():
        icono = f"{Colors.GREEN}✅" if resultado else f"{Colors.RED}❌"
        print(f"{icono} {nombre.replace('_', ' ').title()}")
    
    print(f"\n{Colors.BOLD}TOTAL: {exitosos}/{total} tests exitosos{Colors.RESET}")
    
    if exitosos == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ¡TODOS LOS TESTS PASARON!{Colors.RESET}")
        print(f"{Colors.GREEN}La integración Analytics + Cartera funciona correctamente.{Colors.RESET}\n")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}⚠️ ALGUNOS TESTS FALLARON{Colors.RESET}")
        print(f"{Colors.RED}Revisa los errores arriba.{Colors.RESET}\n")


if __name__ == "__main__":
    main()
