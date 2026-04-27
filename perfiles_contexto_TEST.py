# VERSIÓN DE TEST - SCORES MÁS BAJOS
# Solo para validación - NO usar en producción

PERFILES = {
    "ALCISTA": {
        "peso_breakout": 1.0,
        "peso_pullback": 1.0,
        "score_base_minimo": 5.0,  # ← BAJADO PARA TEST
        "bonus_breakout": 0.3,
        "bonus_pullback": 0.0,
        "penalizacion_general": 0.0,
        "riesgo_por_trade_pct": 2.0,
        "max_posiciones_abiertas": 5,
        "max_exposicion_total_pct": 10.0,
        "trailing_desde_r": 2.0,
        "objetivo_parcial_r": 3.0,
        "venta_parcial_pct": 50,
        "descripcion": "TEST: Alcista con score bajo"
    },
    
    "LATERAL": {
        "peso_breakout": 0.6,
        "peso_pullback": 1.0,
        "score_base_minimo": 5.0,  # ← BAJADO PARA TEST
        "bonus_breakout": 0.0,
        "bonus_pullback": 0.3,
        "penalizacion_general": 0.0,
        "riesgo_por_trade_pct": 1.5,
        "max_posiciones_abiertas": 3,
        "max_exposicion_total_pct": 6.0,
        "trailing_desde_r": 1.5,
        "objetivo_parcial_r": 2.0,
        "venta_parcial_pct": 50,
        "descripcion": "TEST: Lateral con score bajo"
    },
    
    "BAJISTA": {
        "peso_breakout": 0.3,
        "peso_pullback": 0.5,
        "score_base_minimo": 5.0,  # ← BAJADO PARA TEST
        "bonus_breakout": 0.0,
        "bonus_pullback": 0.0,
        "penalizacion_general": 0.5,
        "riesgo_por_trade_pct": 1.0,
        "max_posiciones_abiertas": 2,
        "max_exposicion_total_pct": 3.0,
        "trailing_desde_r": 1.0,
        "objetivo_parcial_r": 1.5,
        "venta_parcial_pct": 75,
        "descripcion": "TEST: Bajista con score bajo"
    }
}

def obtener_perfil_trading(contexto_mercado):
    contexto = contexto_mercado.upper()
    if contexto not in PERFILES:
        print(f"⚠️ Contexto '{contexto}' desconocido, usando perfil LATERAL por defecto")
        contexto = "LATERAL"
    perfil = PERFILES[contexto].copy()
    perfil["contexto"] = contexto
    return perfil

# ... resto del código igual
