"""
Configuración Dinámica
Gestión de parámetros configurables del sistema
"""

class ConfigDinamica:
    """Gestor de configuración dinámica del sistema"""

    def __init__(self):
        self.parametros = {}

    def get(self, clave, default=None):
        """Obtiene un parámetro de configuración"""
        return self.parametros.get(clave, default)

    def set(self, clave, valor):
        """Establece un parámetro de configuración"""
        self.parametros[clave] = valor

# Instancia global
config = ConfigDinamica()
