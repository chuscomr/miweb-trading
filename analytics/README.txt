Esta carpeta contiene el módulo de analytics y métricas.

Base de datos:
- trades.db (se crea automáticamente al cerrar una posición)

Archivos del módulo:
- integrador.py  → Integración automática con trades.db
- metrics.py     → Cálculo de KPIs (winrate, expectancy, etc)
- trades_log.py  → Registro de operaciones

La base de datos trades.db se crea automáticamente cuando se cierra
la primera posición en cartera.
