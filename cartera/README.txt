Esta carpeta contiene el módulo de gestión de cartera.

Base de datos:
- cartera.db (se crea automáticamente al arrancar)

Archivos del módulo:
- cartera_db.py     → Operaciones CRUD sobre cartera.db
- cartera_logica.py → Lógica de negocio (sizing, validaciones)

La base de datos cartera.db se crea automáticamente la primera vez
que se abre una posición o se accede a /cartera
