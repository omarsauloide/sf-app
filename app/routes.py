import secrets
import time
from functools import wraps

from flask import (Blueprint, abort, current_app, jsonify, redirect, render_template,
                   request, session, url_for)

from . import db, queries as q

bp = Blueprint("main", __name__)

ESTADOS_TAREA = {
    "pendiente": "Por recibir", "recibida": "Recibida", "en_proceso": "En progreso",
    "concluida": "En revisión", "rechazada": "Rechazada", "validada": "Validada",
    "cancelada": "Cancelada",
}
ESTADOS_FOLIO = {
    "borrador": "Borrador", "publicado": "Publicado", "en_proceso": "En progreso",
    "en_revision": "En revisión", "devuelto": "Devuelto", "cerrado": "Cerrado",
    "cancelado": "Cancelado",
}
ROLES = {"admin": "Administrador", "gerente": "Gerente", "supervisor": "Supervisor"}
# Siguiente paso permitido para el supervisor: estado actual -> (nuevo estado, texto del botón)
SIGUIENTE = {
    "pendiente": ("recibida", "Recibir tarea"),
    "recibida": ("en_proceso", "Iniciar"),
    "rechazada": ("en_proceso", "Retomar"),
    "en_proceso": ("concluida", "Concluir y enviar a revisión"),
}


@bp.app_context_processor
def inject():
    return dict(
        user=session.get("user"),
        csrf=csrf_token(),
        ESTADOS_TAREA=ESTADOS_TAREA, ESTADOS_FOLIO=ESTADOS_FOLIO, ROLES=ROLES,
        SIGUIENTE=SIGUIENTE, app_name=current_app.config["APP_NAME"],
        fmt_fecha=fmt_fecha, iniciales=iniciales,
        soporte_nombre=current_app.config['SOPORTE_NOMBRE'], soporte_tel=current_app.config['SOPORTE_TEL'],
    )


def fmt_fecha(s):
    if not s:
        return "—"
    y, m, d = s.split("-")
    return f"{d}/{m}/{y}"


def iniciales(nombre):
    partes = [p for p in (nombre or "").split() if p]
    return ("".join(p[0] for p in partes[:2]) or "?").upper()


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(24)
    return session["csrf"]


def check_csrf():
    sent = request.headers.get("X-CSRF") or request.form.get("csrf")
    if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
        abort(403)


def login_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            u = session.get("user")
            if not u:
                if request.path.startswith("/api/"):
                    return jsonify(ok=False, error="Sesión expirada"), 401
                return redirect(url_for("main.login"))
            if roles and u["rol"] not in roles:
                return redirect(url_for("main.inicio"))
            return fn(*a, **kw)
        return wrapper
    return deco


# --- límite de intentos de login (por IP + usuario) ---
_FALLOS = {}
MAX_FALLOS, VENTANA = 5, 600


def _clave():
    return (request.remote_addr or "?", (request.form.get("codigo") or "").strip().lower())


def _bloqueado(k):
    ahora = time.time()
    _FALLOS[k] = [t for t in _FALLOS.get(k, []) if ahora - t < VENTANA]
    return len(_FALLOS[k]) >= MAX_FALLOS


@bp.route("/")
def inicio():
    u = session.get("user")
    if not u:
        return redirect(url_for("main.login"))
    if u["rol"] == "supervisor":
        return redirect(url_for("main.supervisor"))
    return redirect(url_for("main.admin"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        check_csrf()
        k = _clave()
        codigo = (request.form.get("codigo") or "").strip()
        password = request.form.get("password") or ""
        if _bloqueado(k):
            error = "Demasiados intentos. Espera unos minutos e inténtalo de nuevo."
        elif not codigo or not password:
            error = "Escribe tu código y tu contraseña."
        else:
            res = db.query(q.LOGIN, {"codigo": codigo, "password": password})
            if res:
                session.clear()
                session.permanent = True
                session["user"] = res[0]
                csrf_token()
                _FALLOS.pop(k, None)
                return redirect(url_for("main.inicio"))
            _FALLOS.setdefault(k, []).append(time.time())
            error = "Código o contraseña incorrectos."
    return render_template("login.html", error=error)


@bp.route("/logout", methods=["POST"])
def logout():
    check_csrf()
    session.clear()
    return redirect(url_for("main.login"))


@bp.route("/supervisor")
@login_required("supervisor")
def supervisor():
    uid = session["user"]["id"]
    tareas = db.query(q.MIS_TAREAS, {"uid": uid})
    folios = db.query(q.MIS_FOLIOS, {"uid": uid})
    grupos = {
        "recibir": [t for t in tareas if t["estado"] == "pendiente"],
        "curso": [t for t in tareas if t["estado"] in ("recibida", "en_proceso", "rechazada")],
        "concluidas": [t for t in tareas if t["estado"] in ("concluida", "validada")],
    }
    return render_template("supervisor.html", grupos=grupos, folios=folios)


@bp.route("/folio/<int:fid>")
@login_required("supervisor", "admin", "gerente")
def folio(fid):
    uid = session["user"]["id"]
    res = db.query(q.FOLIO, {"fid": fid, "uid": uid})
    if not res:
        abort(404)
    tareas = db.query(q.FOLIO_TAREAS, {"fid": fid, "uid": uid})
    activas = [t for t in tareas if t["estado"] != "cancelada"]
    hechas = len([t for t in activas if t["estado"] in ("concluida", "validada")])
    es_sup = session["user"]["rol"] == "supervisor"
    return render_template("folio.html", f=res[0], tareas=tareas, total=len(activas),
                           hechas=hechas, es_sup=es_sup)


@bp.route("/admin")
@login_required("admin", "gerente")
def admin():
    return render_template("admin.html", appsmith_url=current_app.config["APPSMITH_URL"])


@bp.route("/api/tareas/<int:tid>/estado", methods=["POST"])
@login_required("supervisor")
def api_estado(tid):
    check_csrf()
    data = request.get_json(silent=True) or {}
    nuevo = data.get("nuevo")
    if nuevo not in ("recibida", "en_proceso", "concluida"):
        return jsonify(ok=False, error="Estado no válido"), 400
    res = db.query(q.CAMBIAR_ESTADO, {"nuevo": nuevo, "tid": tid, "uid": session["user"]["id"]})
    if not res:
        return jsonify(ok=False, error="No se pudo cambiar el estado de la tarea."), 409
    return jsonify(ok=True, tarea=res[0])


@bp.after_request
def seguridad(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Cache-Control"] = "no-store"
    return resp
