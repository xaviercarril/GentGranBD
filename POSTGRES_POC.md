# POC PostgreSQL local

Este POC valida que la app puede arrancar con PostgreSQL sin dejar de soportar SQLite.

## 1. Levantar PostgreSQL

```bash
docker compose up -d postgres
```

La base local queda disponible en:

```text
postgresql+psycopg://gentgran:gentgran_dev@localhost:5432/gentgran_poc
```

## 2. Configurar la app para el POC

```bash
export DATABASE_URL="postgresql+psycopg://gentgran:gentgran_dev@localhost:5432/gentgran_poc"
```

`.env.example` queda como referencia, pero la app no carga `.env` automáticamente todavía. Para el POC usa `export DATABASE_URL=...` en la terminal donde ejecutes comandos.

Si no defines `DATABASE_URL`, la app seguirá usando SQLite como hasta ahora.

## 3. Crear las tablas en PostgreSQL

```bash
python scripts/create_schema.py
```

## 4. Arrancar la app contra PostgreSQL

```bash
DATABASE_URL="postgresql+psycopg://gentgran:gentgran_dev@localhost:5432/gentgran_poc" \
python src/ui/app.py
```

## Limitaciones del POC

- El backup/restore integrado de la UI solo sirve para SQLite. En PostgreSQL se debe usar `pg_dump`, `pg_restore` o backups gestionados.
- La migración inicial desde SQLite se puede ejecutar con `scripts/migrate_sqlite_to_postgres.py`.
- La importación masiva desde `LARGO Borrador para bbdd.csv` es un paso separado.

## 5. Migrar datos desde SQLite al PostgreSQL local

Primero revisa conteos sin modificar PostgreSQL. Puedes pasar cualquier `.db`
compatible de Gent Gran:

```bash
python scripts/migrate_sqlite_to_postgres.py src/gentgran.db --dry-run
```

Para copiar datos al POC limpiando antes las tablas de PostgreSQL:

```bash
python scripts/migrate_sqlite_to_postgres.py src/gentgran.db --truncate
```

También puedes usar flags explícitos:

```bash
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path /ruta/a/otra/gentgran.db \
  --postgres-url "postgresql+psycopg://usuario:password@host:5432/base" \
  --truncate
```
