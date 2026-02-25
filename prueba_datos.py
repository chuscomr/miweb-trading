from logica import obtener_precios

class DummyCache:
    def cached(self, *args, **kwargs):
        def decorator(f):
            return f
        return decorator

cache = DummyCache()

print("Antes de obtener_precios")
precios, volumenes, fechas, precio_actual = obtener_precios("SAN.MC", cache)
print("Después de obtener_precios")

print("len precios:", len(precios))
