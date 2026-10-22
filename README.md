# SF-EMPRESARIAL · capa de diseño (sf-app)

Web app (Flask) que usa la MISMA base de datos PostgreSQL de Appsmith.
Pantallas: login, bandeja del supervisor (Por recibir / En curso / Concluidas), detalle de folio.
El panel de administración sigue en Appsmith.

## Instalación (resumen)
1. Ejecutar `db/app_role.sql` en Appsmith (usuario de base de datos con permisos mínimos).
2. DNS: registro A `app` → IP del VPS.
3. Administrador de Docker → proyecto nuevo desde este repositorio → variables:
   `APP_HOST`, `APP_DB_PASSWORD`, `SECRET_KEY` (+ opcionales `SOPORTE_NOMBRE`, `SOPORTE_TEL`).
4. Revisar que las etiquetas de traefik en `docker-compose.yml` coincidan con las de `appsmith-ogqn`.

## Pruebas locales
`DB_DRIVER=psql` permite probar con un PostgreSQL local usando el cliente `psql` (sin instalar paquetes).
