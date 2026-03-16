# Compatibilidad: logica_posicional antiguo usa funciones, no clase Posicional
try:
    from .logica_posicional import Posicional
except ImportError:
    Posicional = None

try:
    from .scanner_posicional import ScannerPosicional
except ImportError:
    ScannerPosicional = None
