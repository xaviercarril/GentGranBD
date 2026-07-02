# Staging en DigitalOcean

Objetivo: validar la app de escritorio contra una base PostgreSQL gestionada en DigitalOcean antes de producción.

## Arquitectura recomendada para staging

Como esta app es de escritorio, el primer staging realista es:

```text
App local PySide6 -> DigitalOcean Managed PostgreSQL
```

La VPC privada solo aplica si la app se ejecuta dentro de DigitalOcean, por ejemplo en un Droplet o App Platform. Para una app de escritorio conectando desde tu Mac, usa el hostname público de la base y restringe acceso con Trusted Sources.

Según la documentación actual de DigitalOcean, Managed PostgreSQL ofrece conexión pública o privada/VPC, SSL, backups y Trusted Sources. La conexión privada solo funciona desde recursos en la misma VPC.

Referencias:
- https://docs.digitalocean.com/products/databases/postgresql/how-to/connect/
- https://docs.digitalocean.com/products/databases/postgresql/how-to/secure/
- https://docs.digitalocean.com/products/databases/

## Pasos

1. Crear proyecto en DigitalOcean: `gentgran-staging`.
2. Crear Managed PostgreSQL en una región cercana.
3. Crear base de datos, por ejemplo `gentgran_staging`.
4. Añadir tu IP pública como Trusted Source para pruebas desde tu Mac.
5. Copiar la connection string de DigitalOcean.
6. Configurar `DATABASE_URL` localmente.
7. Crear esquema.
8. Migrar datos.
9. Probar la app.

## Configurar conexión

Copia el ejemplo:

```bash
cp .env.staging.example .env.staging
```

Edita `.env.staging` y pega la URL real de DigitalOcean. Para una primera prueba:

```text
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:25060/DBNAME?sslmode=require
```

Para TLS más estricto, descarga el CA certificate en DigitalOcean y usa:

```text
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:25060/DBNAME?sslmode=verify-full&sslrootcert=/absolute/path/to/ca-certificate.crt
```

## Crear esquema

```bash
set -a
source .env.staging
set +a

python3 scripts/create_schema.py
python3 scripts/check_database.py
```

## Migrar desde SQLite local

Si `src/gentgran.db` ya tiene los datos validados:

```bash
set -a
source .env.staging
set +a

python3 scripts/migrate_sqlite_to_postgres.py src/gentgran.db --truncate
python3 scripts/check_database.py
```

Para escoger el backup desde terminal:

```bash
set -a
source .env.staging
set +a

python3 scripts/migrate_backup_to_digitalocean.py --dry-run
python3 scripts/migrate_backup_to_digitalocean.py
python3 scripts/check_database.py
```

El script lista los `.db` encontrados y permite elegir uno por numero o pegar una ruta manual. En la migracion real vacia las tablas del PostgreSQL destino antes de copiar el backup seleccionado.

## Arrancar la app contra staging

```bash
set -a
source .env.staging
set +a

python3 src/ui/app.py
```

En la pantalla inicial solo se introducen los datos de la app:

- `Database URL`: se muestra sin usuario ni password si viene de la configuracion.
- `Usuari app` / `Contrasenya app`: usuario interno de Gent Gran

El usuario/password tecnico de PostgreSQL debe configurarse fuera de la pantalla de login, por ejemplo con `DATABASE_URL` o `GENTGRAN_DATABASE_URL`.

En `logs/app-startup.log` debe aparecer:

```text
Database backend=postgresql
```

## Auditoria

La app registra automaticamente cambios ORM en la tabla `auditoria` cuando se ejecuta desde la UI:

- `usuario_app`: usuario interno autenticado en Gent Gran.
- `accion`: `CREATE`, `UPDATE` o `DELETE`.
- `tabla`: tabla modificada.
- `registro_id`: clave primaria del registro.
- `fecha_hora`: momento del cambio.
- `detalle`: valores o campos modificados en JSON.

La URL del log aparece con password oculto.

## Checklist de validación

- Listado de socios carga con 42.900 registros.
- Buscar socio funciona.
- Editar socio conserva posición y datos.
- Generar carnet funciona.
- Crear socio de prueba.
- Borrar socio de prueba.
- Crear actividad de prueba.
- Inscribir socio en actividad.
- Registrar pago.
- Generar PDF de asistencia/inscripciones si aplica.

## Notas

- No subas `.env.staging` al repositorio.
- Si aparece `Connection refused`, revisa puerto, Trusted Sources y que uses el hostname correcto.
- Si conectas por private hostname/VPC, la app debe ejecutarse desde un recurso DigitalOcean en la misma VPC.
