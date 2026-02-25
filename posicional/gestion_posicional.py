# ==========================================================
# GESTIÓN POSICIONAL
# Clase para gestionar posiciones de largo plazo (6M-2Y)
# ==========================================================

try:
    from .config_posicional import *
except ImportError:
    from config_posicional import *


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 CLASE POSICIÓN POSICIONAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PosicionPosicional:
    """
    Gestión de una posición de largo plazo (6 meses - 2 años).
    
    FILOSOFÍA:
    - Stops amplios (8-15%)
    - Trailing ultra-conservador
    - Objetivo: capturar tendencias completas
    - Mínimo 26 semanas en posición
    
    ESTADOS:
    - INICIAL: Desde entrada hasta +5R
    - PROTEGIDO: De +5R a +10R (stop en breakeven)
    - TRAILING: >+10R (trailing de máximos)
    """
    
    def __init__(self, entrada, stop, fecha_apertura):
        """
        Inicializa posición posicional.
        
        Args:
            entrada: Precio de entrada
            stop: Stop inicial (8-15% bajo entrada)
            fecha_apertura: Fecha de entrada
        """
        self.entrada = entrada
        self.stop_inicial = stop
        self.stop = stop
        self.fecha_apertura = fecha_apertura
        
        # Estado de gestión
        self.estado = ESTADO_INICIAL
        self.semanas_en_posicion = 0
        
        # Tracking
        self.maximo_alcanzado = entrada
        self.fecha_maximo = fecha_apertura
        self.r_maximo = 0.0
        
        # Histórico de stops
        self.historial_stops = [(fecha_apertura, stop, "Stop inicial")]
    
    
    def actualizar(self, fecha, precio, high=None, low=None):
        """
        Actualiza la posición con nueva semana de datos.
        
        Args:
            fecha: Fecha actual
            precio: Precio de cierre semanal
            high: Máximo semanal (opcional)
            low: Mínimo semanal (opcional)
        
        Returns:
            tuple (debe_salir, motivo_salida)
        """
        self.semanas_en_posicion += 1
        
        # Usar high si disponible, sino precio
        precio_maximo = high if high is not None else precio
        precio_minimo = low if low is not None else precio
        
        # Actualizar máximo alcanzado
        if precio_maximo > self.maximo_alcanzado:
            self.maximo_alcanzado = precio_maximo
            self.fecha_maximo = fecha
        
        # Calcular R actual
        r_actual = self.calcular_R_actual(precio)
        if r_actual > self.r_maximo:
            self.r_maximo = r_actual
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # VERIFICAR STOP
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        if precio_minimo <= self.stop:
            motivo = f"Stop en {self.estado} (-{abs(r_actual):.2f}R)"
            return (True, motivo)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # NO SALIR ANTES DE DURACIÓN MÍNIMA
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        if self.semanas_en_posicion < DURACION_MINIMA_SEMANAS:
            # Aún no han pasado 6 meses - no hacer nada más
            return (False, None)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # TRANSICIONES DE ESTADO
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        # Estado INICIAL → PROTEGIDO (a +5R)
        if self.estado == ESTADO_INICIAL and r_actual >= R_PARA_PROTEGER:
            self._transicion_a_protegido(fecha, precio)
        
        # Estado PROTEGIDO → TRAILING (a +10R)
        elif self.estado == ESTADO_PROTEGIDO and r_actual >= R_PARA_TRAILING:
            self._transicion_a_trailing(fecha, precio)
        
        # Estado TRAILING → Actualizar trailing
        elif self.estado == ESTADO_TRAILING:
            self._actualizar_trailing(fecha, precio, high)
        
        return (False, None)
    
    
    def _transicion_a_protegido(self, fecha, precio):
        """Transición de INICIAL a PROTEGIDO."""
        # Mover stop a breakeven (pequeña pérdida aceptable)
        nuevo_stop = self.entrada * (1 + PROTECCION_R_NEGATIVO * (self.entrada - self.stop_inicial) / self.entrada)
        
        if nuevo_stop > self.stop:
            self.stop = nuevo_stop
            self.estado = ESTADO_PROTEGIDO
            self.historial_stops.append((fecha, nuevo_stop, "Breakeven a +5R"))
    
    
    def _transicion_a_trailing(self, fecha, precio):
        """Transición de PROTEGIDO a TRAILING."""
        # Activar trailing stop
        self.estado = ESTADO_TRAILING
        self.historial_stops.append((fecha, self.stop, "Activar trailing a +10R"))
    
    
    def _actualizar_trailing(self, fecha, precio, high=None):
        """Actualiza trailing stop en estado TRAILING."""
        precio_ref = high if high is not None else precio
        
        # Trailing basado en máximos de últimas N semanas
        if self.r_maximo >= TRAILING_R_MINIMO:
            # Trailing ultra-conservador (semestre)
            lookback = TRAILING_LOOKBACK_FINAL
        else:
            # Trailing estándar (trimestre)
            lookback = TRAILING_LOOKBACK
        
        # Calcular nuevo stop (este método se llama semanalmente,
        # por lo que necesitaríamos el histórico de precios)
        # Por simplicidad, usamos el máximo alcanzado con un porcentaje
        
        # Stop = máximo alcanzado - X% del riesgo inicial
        factor_trailing = 0.5  # 50% del riesgo inicial desde máximo
        riesgo_inicial_pct = (self.entrada - self.stop_inicial) / self.entrada
        nuevo_stop = self.maximo_alcanzado * (1 - riesgo_inicial_pct * factor_trailing)
        
        if nuevo_stop > self.stop:
            self.stop = nuevo_stop
            self.historial_stops.append((fecha, nuevo_stop, "Trailing actualizado"))
    
    
    def calcular_R_actual(self, precio):
        """
        Calcula R actual de la posición.
        
        R = (Precio - Entrada) / (Entrada - Stop_Inicial)
        """
        riesgo_inicial = self.entrada - self.stop_inicial
        if riesgo_inicial == 0:
            return 0
        
        r = (precio - self.entrada) / riesgo_inicial
        return r
    
    
    def obtener_info(self, precio_actual):
        """
        Obtiene información completa de la posición.
        
        Returns:
            dict con estado actual
        """
        r_actual = self.calcular_R_actual(precio_actual)
        
        return {
            "entrada": round(self.entrada, 2),
            "stop_actual": round(self.stop, 2),
            "stop_inicial": round(self.stop_inicial, 2),
            "precio_actual": round(precio_actual, 2),
            "r_actual": round(r_actual, 2),
            "r_maximo": round(self.r_maximo, 2),
            "maximo_alcanzado": round(self.maximo_alcanzado, 2),
            "estado": self.estado,
            "semanas_posicion": self.semanas_en_posicion,
            "movimientos_stop": len(self.historial_stops)
        }
    
    
    def __repr__(self):
        """Representación de la posición."""
        return (f"PosicionPosicional(entrada={self.entrada:.2f}, "
                f"stop={self.stop:.2f}, estado={self.estado}, "
                f"semanas={self.semanas_en_posicion})")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧪 TEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("🧪 Test gestion_posicional.py")
    print("=" * 60)
    
    from datetime import datetime, timedelta
    
    # Simular posición ganadora
    entrada = 100.0
    stop = 90.0  # 10% riesgo
    fecha_inicio = datetime(2024, 1, 1)
    
    print(f"\n📊 Posición de prueba:")
    print(f"   Entrada: {entrada}€")
    print(f"   Stop inicial: {stop}€")
    print(f"   Riesgo inicial: {((entrada - stop) / entrada) * 100:.1f}%")
    
    posicion = PosicionPosicional(entrada, stop, fecha_inicio)
    
    # Simular evolución de 52 semanas (1 año)
    precios_semana = [
        # Fase 1: Inicial (semanas 1-20) - +0 a +50%
        *[entrada + i * 2.5 for i in range(20)],
        # Fase 2: Consolidación (semanas 21-30)
        *[entrada + 50 + (i % 3 - 1) * 3 for i in range(10)],
        # Fase 3: Breakout (semanas 31-52) - Hasta +150%
        *[entrada + 50 + (i - 30) * 4 for i in range(30, 52)]
    ]
    
    print(f"\n📈 Simulando {len(precios_semana)} semanas:")
    
    eventos = []
    for semana, precio in enumerate(precios_semana, 1):
        fecha = fecha_inicio + timedelta(weeks=semana)
        
        debe_salir, motivo = posicion.actualizar(fecha, precio, high=precio*1.02, low=precio*0.98)
        
        r_actual = posicion.calcular_R_actual(precio)
        
        # Registrar eventos importantes
        if posicion.estado == ESTADO_PROTEGIDO and len(eventos) == 0:
            eventos.append((semana, "PROTEGIDO", r_actual))
        
        if posicion.estado == ESTADO_TRAILING and len(eventos) <= 1:
            eventos.append((semana, "TRAILING", r_actual))
        
        if debe_salir:
            print(f"\n🛑 Salida en semana {semana}:")
            print(f"   Motivo: {motivo}")
            print(f"   Precio salida: {precio:.2f}€")
            print(f"   R final: {r_actual:.2f}R")
            break
    
    if not debe_salir:
        print(f"\n✅ Posición sigue abierta:")
        info = posicion.obtener_info(precios_semana[-1])
        print(f"   Semanas: {info['semanas_posicion']}")
        print(f"   Estado: {info['estado']}")
        print(f"   Precio actual: {info['precio_actual']}€")
        print(f"   R actual: {info['r_actual']}R")
        print(f"   R máximo: {info['r_maximo']}R")
        print(f"   Máximo alcanzado: {info['maximo_alcanzado']}€")
        print(f"   Stop actual: {info['stop_actual']}€")
        print(f"   Movimientos de stop: {info['movimientos_stop']}")
    
    print(f"\n📋 Eventos importantes:")
    for semana, evento, r_val in eventos:
        print(f"   Semana {semana:2d}: {evento:15s} (R={r_val:+.1f})")
    
    print("\n" + "=" * 60)
