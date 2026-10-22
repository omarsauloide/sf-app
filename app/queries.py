"""Consultas SQL. Cada una devuelve la columna `j` (arreglo JSON)."""

LOGIN = """
SELECT coalesce(json_agg(u), '[]'::json) AS j FROM (
  SELECT id, codigo_empleado AS codigo, nombre, rol
  FROM usuarios
  WHERE codigo_empleado = %(codigo)s AND activo = TRUE
    AND password_hash = crypt(%(password)s, password_hash)
) u
"""

MIS_TAREAS = """
SELECT coalesce(json_agg(x ORDER BY x.fecha_limite NULLS LAST, x.id), '[]'::json) AS j FROM (
  SELECT t.id, t.folio_id, f.folio, f.nombre_proyecto, c.nombre AS cliente,
         f.ubicacion AS sitio, t.orden, t.titulo, t.tipo, t.descripcion,
         to_char(t.fecha_inicio,'YYYY-MM-DD') AS fecha_inicio,
         to_char(t.fecha_limite,'YYYY-MM-DD') AS fecha_limite,
         t.estado
  FROM tareas t
  JOIN folios f ON f.id = t.folio_id
  JOIN clientes c ON c.id = f.cliente_id
  JOIN folio_supervisores fs ON fs.folio_id = f.id
  WHERE fs.supervisor_id = %(uid)s
    AND f.estado IN ('publicado','en_proceso','devuelto')
    AND t.estado <> 'cancelada'
) x
"""

MIS_FOLIOS = """
SELECT coalesce(json_agg(x ORDER BY x.fecha_inicio, x.id), '[]'::json) AS j FROM (
  SELECT f.id, f.folio, f.nombre_proyecto, f.estado, c.nombre AS cliente,
         f.ubicacion AS sitio,
         to_char(f.fecha_inicio,'YYYY-MM-DD') AS fecha_inicio,
         to_char(f.fecha_fin_estimada,'YYYY-MM-DD') AS fecha_fin,
         (SELECT count(*) FROM tareas t WHERE t.folio_id = f.id AND t.estado <> 'cancelada') AS total,
         (SELECT count(*) FROM tareas t WHERE t.folio_id = f.id AND t.estado IN ('concluida','validada')) AS hechas
  FROM folios f
  JOIN clientes c ON c.id = f.cliente_id
  JOIN folio_supervisores fs ON fs.folio_id = f.id
  WHERE fs.supervisor_id = %(uid)s
    AND f.estado IN ('publicado','en_proceso','devuelto')
) x
"""

# Acceso: admin/gerente ven todo; supervisor solo sus folios.
FOLIO = """
SELECT coalesce(json_agg(x), '[]'::json) AS j FROM (
  SELECT f.id, f.folio, f.nombre_proyecto, f.descripcion, f.estado,
         to_char(f.fecha_inicio,'YYYY-MM-DD') AS fecha_inicio,
         to_char(f.fecha_fin_estimada,'YYYY-MM-DD') AS fecha_fin,
         c.nombre AS cliente, c.contacto,
         s.nombre AS sitio, s.calle_numero, s.colonia, s.municipio, s.estado_mx,
         s.codigo_postal, s.referencias,
         (SELECT u.nombre FROM folio_supervisores fs JOIN usuarios u ON u.id = fs.supervisor_id
           WHERE fs.folio_id = f.id AND fs.rol_folio = 'responsable' LIMIT 1) AS supervisor
  FROM folios f
  JOIN clientes c ON c.id = f.cliente_id
  LEFT JOIN sitios s ON s.id = f.sitio_id
  WHERE f.id = %(fid)s
    AND (
      EXISTS (SELECT 1 FROM usuarios WHERE id = %(uid)s AND rol IN ('admin','gerente') AND activo)
      OR EXISTS (SELECT 1 FROM folio_supervisores WHERE folio_id = f.id AND supervisor_id = %(uid)s)
    )
) x
"""

FOLIO_TAREAS = """
SELECT coalesce(json_agg(x ORDER BY x.orden, x.id), '[]'::json) AS j FROM (
  SELECT t.id, t.orden, t.titulo, t.tipo, t.descripcion, t.estado,
         to_char(t.fecha_inicio,'YYYY-MM-DD') AS fecha_inicio,
         to_char(t.fecha_limite,'YYYY-MM-DD') AS fecha_limite,
         to_char(t.concluida_en AT TIME ZONE 'America/Mexico_City','DD/MM HH24:MI') AS concluida_en
  FROM tareas t
  WHERE t.folio_id = %(fid)s
    AND (t.estado <> 'cancelada' OR EXISTS (SELECT 1 FROM usuarios WHERE id = %(uid)s AND rol IN ('admin','gerente')))
) x
"""

# Cambio de estado del supervisor (mismas reglas que en Appsmith).
CAMBIAR_ESTADO = """
WITH cambio AS (
  UPDATE tareas t
  SET estado = %(nuevo)s::text,
      concluida_en = CASE WHEN %(nuevo)s::text = 'concluida' THEN now() ELSE t.concluida_en END
  WHERE t.id = %(tid)s
    AND (
         (t.estado = 'pendiente'  AND %(nuevo)s::text = 'recibida')
      OR (t.estado = 'recibida'   AND %(nuevo)s::text = 'en_proceso')
      OR (t.estado = 'rechazada'  AND %(nuevo)s::text = 'en_proceso')
      OR (t.estado = 'en_proceso' AND %(nuevo)s::text = 'concluida')
    )
    AND EXISTS (
      SELECT 1 FROM folio_supervisores fs
      JOIN usuarios u ON u.id = fs.supervisor_id
      WHERE fs.folio_id = t.folio_id AND fs.supervisor_id = %(uid)s
        AND u.rol = 'supervisor' AND u.activo = TRUE
    )
    AND EXISTS (SELECT 1 FROM folios WHERE id = t.folio_id AND estado IN ('publicado','en_proceso','devuelto'))
  RETURNING t.id, t.folio_id, t.titulo, t.estado
),
fol AS (
  UPDATE folios SET estado = 'en_proceso'
  WHERE id IN (SELECT folio_id FROM cambio) AND estado = 'publicado'
),
bit AS (
  INSERT INTO bitacora (folio_id, tarea_id, usuario_id, accion, detalle)
  SELECT folio_id, id, %(uid)s, 'tarea_' || estado, jsonb_build_object('titulo', titulo)
  FROM cambio
)
SELECT coalesce(json_agg(c), '[]'::json) AS j FROM cambio c
"""
