Esta carpeta contiene el módulo de gestión de alertas.

Base de datos:
- alertas.db (se crea automáticamente al arrancar)

Archivos del módulo:
- alertas_db.py    → Operaciones CRUD sobre alertas.db
- alertas_ia.py    → Análisis IA de alertas disparadas  
- detector.py      → Motor de detección en tiempo real

La base de datos alertas.db se crea automáticamente la primera vez
que se arranca el sistema o se accede a /alertas
