-- Usuario de base de datos con permisos MÍNIMOS para la web app (sf-app).
-- Ejecutar UNA vez desde Appsmith (consulta temporal, "Use prepared statement" apagado).
-- 1) Cambia CAMBIAR_ESTA_CONTRASENA por una contraseña larga que solo tú conozcas.
-- 2) Corre la consulta y BORRA la consulta de inmediato.

CREATE ROLE folios_app LOGIN PASSWORD 'CAMBIAR_ESTA_CONTRASENA';

GRANT CONNECT ON DATABASE folios TO folios_app;
GRANT USAGE ON SCHEMA public TO folios_app;

GRANT SELECT ON usuarios, clientes, sitios, folios, folio_supervisores, tareas TO folios_app;
GRANT UPDATE (estado, concluida_en) ON tareas TO folios_app;
GRANT UPDATE (estado) ON folios TO folios_app;
GRANT INSERT ON bitacora TO folios_app;
GRANT USAGE, SELECT ON SEQUENCE bitacora_id_seq TO folios_app;
