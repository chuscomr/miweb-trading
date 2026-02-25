# ==========================================================
# GESTIÓN DE SALIDAS - SISTEMA MEDIO PLAZO
# Sistema de estados: INICIAL → PROTEGIDO → TRAILING
# ==========================================================

from .config_medio import *


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 CLASE POSICIÓN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PosicionMedioPlazo:
    """
    Representa una posición abierta en medio plazo.
    Gestiona estados y actualizaciones de stop.
    """
    
    def __init__(self, entrada, stop_inicial, fecha_entrada=None):
        """
        Inicializa posición.
        
        Args:
            entrada: precio de entrada
            stop_inicial: stop inicial
            fecha_entrada: fecha de entrada (opcional)
        """
        self.entrada = entrada
        self.stop_inicial = stop_inicial
        self.stop_actual = stop_inicial
        self.estado = ESTADO_INICIAL
        
        self.riesgo_inicial = entrada - stop_inicial
        self.fecha_entrada = fecha_entrada
        self.semanas_en_posicion = 0
        
        # Historial de precios (para trailing)
        self.historial_precios = []
    
    def actualizar(self, precio_actual, high=None, low=None):
        """
        Actualiza la posición con nueva semana de datos.
        
        Args:
            precio_actual: precio de cierre semanal
            high: máximo semanal (opcional)
            low: mínimo semanal (opcional)
        
        Returns:
            dict con:
            - salir: bool (si debe cerrar posición)
            - motivo: str (razón de salida)
            - stop_nuevo: float (nuevo nivel de stop)
            - estado_nuevo: str (nuevo estado)
        """
        self.semanas_en_posicion += 1
        self.historial_precios.append(precio_actual)
        
        # Calcular R actual
        if self.riesgo_inicial <= 0:
            return {
                "salir": True,
                "motivo": "RIESGO_INVALIDO",
                "stop_nuevo": self.stop_actual,
                "estado_nuevo": self.estado
            }
        
        R_actual = (precio_actual - self.entrada) / self.riesgo_inicial
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # FASE 1: ESTADO INICIAL
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        if self.estado == ESTADO_INICIAL:
            # Transición a PROTEGIDO si llegamos a +2R
            if R_actual >= R_PARA_PROTEGER:
                nuevo_stop = self.entrada + (self.riesgo_inicial * PROTECCION_R_NEGATIVO)
                
                return {
                    "salir": False,
                    "motivo": "PROTECCION_ACTIVADA",
                    "stop_nuevo": nuevo_stop,
                    "estado_nuevo": ESTADO_PROTEGIDO
                }
            
            # Salir si toca stop inicial
            if precio_actual <= self.stop_actual or (low and low <= self.stop_actual):
                return {
                    "salir": True,
                    "motivo": "STOP_INICIAL",
                    "stop_nuevo": self.stop_actual,
                    "estado_nuevo": self.estado
                }
            
            # Mantener estado
            return {
                "salir": False,
                "motivo": None,
                "stop_nuevo": self.stop_actual,
                "estado_nuevo": ESTADO_INICIAL
            }
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # FASE 2: ESTADO PROTEGIDO
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        if self.estado == ESTADO_PROTEGIDO:
            # Transición a TRAILING si llegamos a +4R
            if R_actual >= R_PARA_TRAILING and len(self.historial_precios) >= TRAILING_LOOKBACK:
                trailing_stop = min(self.historial_precios[-TRAILING_LOOKBACK:])
                nuevo_stop = max(self.stop_actual, trailing_stop)
                
                return {
                    "salir": False,
                    "motivo": "TRAILING_ACTIVADO",
                    "stop_nuevo": nuevo_stop,
                    "estado_nuevo": ESTADO_TRAILING
                }
            
            # Salir si toca stop protegido
            if precio_actual <= self.stop_actual or (low and low <= self.stop_actual):
                return {
                    "salir": True,
                    "motivo": "STOP_PROTEGIDO",
                    "stop_nuevo": self.stop_actual,
                    "estado_nuevo": self.estado
                }
            
            # Mantener estado
            return {
                "salir": False,
                "motivo": None,
                "stop_nuevo": self.stop_actual,
                "estado_nuevo": ESTADO_PROTEGIDO
            }
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # FASE 3: ESTADO TRAILING
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        if self.estado == ESTADO_TRAILING:
            # Actualizar trailing stop (últimas N semanas)
            lookback = min(TRAILING_LOOKBACK_FINAL, len(self.historial_precios))
            trailing_stop = min(self.historial_precios[-lookback:])
            
            # El stop solo puede subir, nunca bajar
            nuevo_stop = max(self.stop_actual, trailing_stop)
            
            # Salir si toca trailing stop
            if precio_actual <= nuevo_stop or (low and low <= nuevo_stop):
                return {
                    "salir": True,
                    "motivo": "TRAILING_STOP",
                    "stop_nuevo": nuevo_stop,
                    "estado_nuevo": self.estado
                }
            
            # Mantener trailing
            return {
                "salir": False,
                "motivo": None,
                "stop_nuevo": nuevo_stop,
                "estado_nuevo": ESTADO_TRAILING
            }
        
        # Estado desconocido (no debería llegar aquí)
        return {
            "salir": False,
            "motivo": None,
            "stop_nuevo": self.stop_actual,
            "estado_nuevo": self.estado
        }
    
    def aplicar_actualizacion(self, resultado):
        """
        Aplica el resultado de actualizar().
        
        Args:
            resultado: dict devuelto por actualizar()
        """
        self.stop_actual = resultado["stop_nuevo"]
        self.estado = resultado["estado_nuevo"]
    
    def calcular_R_actual(self, precio_actual):
        """
        Calcula R actual.
        
        Returns:
            float: R actual
        """
        if self.riesgo_inicial <= 0:
            return 0
        
        return (precio_actual - self.entrada) / self.riesgo_inicial
    
    def obtener_info(self, precio_actual):
        """
        Obtiene información completa de la posición.
        
        Returns:
            dict con toda la info
        """
        R_actual = self.calcular_R_actual(precio_actual)
        
        return {
            "entrada": self.entrada,
            "stop_inicial": self.stop_inicial,
            "stop_actual": self.stop_actual,
            "estado": self.estado,
            "semanas": self.semanas_en_posicion,
            "R_actual": round(R_actual, 2),
            "riesgo_inicial": self.riesgo_inicial,
            "precio_actual": precio_actual
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎯 FUNCIÓN SIMPLIFICADA (para backtest)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def gestionar_salida_simple(precio_actual, entrada, stop_inicial, stop_actual, estado, historial_precios):
    """
    Versión funcional (sin clase) para compatibilidad con código existente.
    
    Returns:
        tuple: (stop_nuevo, estado_nuevo, salir)
    """
    riesgo_inicial = entrada - stop_inicial
    
    if riesgo_inicial <= 0:
        return stop_actual, estado, True
    
    R_actual = (precio_actual - entrada) / riesgo_inicial
    
    # ESTADO INICIAL
    if estado == ESTADO_INICIAL:
        if R_actual >= R_PARA_PROTEGER:
            nuevo_stop = entrada + (riesgo_inicial * PROTECCION_R_NEGATIVO)
            return nuevo_stop, ESTADO_PROTEGIDO, False
        
        if precio_actual <= stop_actual:
            return stop_actual, estado, True
        
        return stop_actual, estado, False
    
    # ESTADO PROTEGIDO
    if estado == ESTADO_PROTEGIDO:
        if R_actual >= R_PARA_TRAILING and len(historial_precios) >= TRAILING_LOOKBACK:
            trailing = min(historial_precios[-TRAILING_LOOKBACK:])
            nuevo_stop = max(stop_actual, trailing)
            return nuevo_stop, ESTADO_TRAILING, False
        
        if precio_actual <= stop_actual:
            return stop_actual, estado, True
        
        return stop_actual, estado, False
    
    # ESTADO TRAILING
    if estado == ESTADO_TRAILING:
        lookback = min(TRAILING_LOOKBACK_FINAL, len(historial_precios))
        trailing = min(historial_precios[-lookback:])
        nuevo_stop = max(stop_actual, trailing)
        
        if precio_actual <= nuevo_stop:
            return nuevo_stop, estado, True
        
        return nuevo_stop, estado, False
    
    return stop_actual, estado, False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧪 TEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("🧪 Test gestion_medio.py")
    print("=" * 50)
    
    # Simular posición
    entrada = 10.0
    stop = 9.0
    
    print(f"\n📌 Posición:")
    print(f"   Entrada: {entrada}")
    print(f"   Stop inicial: {stop}")
    print(f"   Riesgo inicial: {entrada - stop} ({(entrada-stop)/entrada*100:.1f}%)")
    
    pos = PosicionMedioPlayzo(entrada, stop)
    
    # Simular evolución
    precios_sim = [10.2, 10.5, 10.8, 11.0, 11.2, 11.5, 11.8, 12.0, 11.8, 11.5]
    
    print(f"\n📊 Evolución:")
    for i, precio in enumerate(precios_sim, 1):
        resultado = pos.actualizar(precio)
        pos.aplicar_actualizacion(resultado)
        
        R = pos.calcular_R_actual(precio)
        
        print(f"   Semana {i}: ${precio:.2f} | R: {R:+.2f} | Estado: {pos.estado} | Stop: ${pos.stop_actual:.2f}")
        
        if resultado["motivo"]:
            print(f"      └─ {resultado['motivo']}")
        
        if resultado["salir"]:
            print(f"      └─ ❌ SALIDA: {resultado['motivo']}")
            break
