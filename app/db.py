"""Acceso a PostgreSQL.

Convención: TODAS las consultas devuelven una sola columna `j` con un arreglo JSON
(json_agg). Así el mismo código sirve con psycopg (producción) y con el modo de
pruebas por psql (DB_DRIVER=psql).
"""
import json
import os
import re
import subprocess

DRIVER = os.environ.get("DB_DRIVER", "psycopg")

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        from psycopg_pool import ConnectionPool
        _pool = ConnectionPool(os.environ["DATABASE_URL"], min_size=1, max_size=6, open=True)
    return _pool


def _quote(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def _query_psql(sql, params):
    sql = re.sub(r"%\((\w+)\)s", lambda m: _quote(params[m.group(1)]), sql)
    cmd = ["psql", "-X", "-At", "-v", "ON_ERROR_STOP=1", "-c", sql]
    env = dict(os.environ)
    env["PGHOST"] = os.environ.get("PGHOST", "/tmp/pgtest")
    env["PGPORT"] = os.environ.get("PGPORT", "55432")
    env["PGDATABASE"] = os.environ.get("PGDATABASE", "folios")
    env["PGUSER"] = os.environ.get("PGUSER", "postgres")
    out = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip())
    txt = out.stdout
    a, b = txt.find("["), txt.rfind("]")
    if a != -1 and b > a:
        return json.loads(txt[a:b + 1])
    return []


def query(sql, params=None):
    """Ejecuta una consulta que devuelve la columna `j` (arreglo JSON). Regresa lista de dicts."""
    params = params or {}
    if DRIVER == "psql":
        return _query_psql(sql, params)
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return (row[0] if row and row[0] else []) or []
