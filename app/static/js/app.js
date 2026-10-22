(function () {
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // fecha y reloj
  var f = $('#fecha-hoy');
  if (f) {
    var d = new Date();
    f.textContent = d.toLocaleDateString('es-MX', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' }).replace(/ de /g, '-').replace(',', '');
  }
  var r = $('#reloj');
  if (r) {
    var tick = function () { r.textContent = new Date().toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' }); };
    tick(); setInterval(tick, 20000);
  }

  // menú lateral
  var drawer = $('#drawer'), bg = $('#drawer-bg');
  function menu(abrir) {
    if (!drawer) return;
    drawer.classList.toggle('is-open', abrir);
    drawer.setAttribute('aria-hidden', abrir ? 'false' : 'true');
    bg.hidden = !abrir;
  }
  var ab = $('#abrir-menu'), ce = $('#cerrar-menu');
  if (ab) ab.addEventListener('click', function () { menu(true); });
  if (ce) ce.addEventListener('click', function () { menu(false); });
  if (bg) bg.addEventListener('click', function () { menu(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') menu(false); });

  // pestañas
  function irTab(nombre) {
    $$('.tab').forEach(function (t) { t.classList.toggle('is-active', t.dataset.tab === nombre); });
    $$('.panel').forEach(function (p) { p.classList.toggle('is-active', p.dataset.panel === nombre); });
    try { sessionStorage.setItem('tab:' + location.pathname, nombre); } catch (e) {}
  }
  $$('.tab').forEach(function (t) { t.addEventListener('click', function () { irTab(t.dataset.tab); }); });
  $$('[data-ir-tab]').forEach(function (b) {
    b.addEventListener('click', function () {
      irTab(b.dataset.irTab);
      var t = $('.tabs'); if (t) t.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
  try {
    var guardada = sessionStorage.getItem('tab:' + location.pathname);
    if (guardada && $('.tab[data-tab="' + guardada + '"]')) irTab(guardada);
  } catch (e) {}

  // avisos
  var toast = $('#toast'), tt;
  function aviso(msg, error) {
    toast.textContent = msg; toast.className = 'toast' + (error ? ' err' : ''); toast.hidden = false;
    clearTimeout(tt); tt = setTimeout(function () { toast.hidden = true; }, 3500);
  }

  // cambiar estado de una tarea
  var csrf = ($('meta[name="csrf"]') || {}).content;
  $$('[data-accion="estado"]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      btn.disabled = true;
      fetch('/api/tareas/' + btn.dataset.tarea + '/estado', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF': csrf },
        body: JSON.stringify({ nuevo: btn.dataset.nuevo }),
        credentials: 'same-origin'
      }).then(function (res) { return res.json().then(function (j) { return { ok: res.ok, j: j }; }); })
        .then(function (r) {
          if (r.ok && r.j.ok) { aviso('Tarea actualizada'); setTimeout(function () { location.reload(); }, 500); }
          else { aviso((r.j && r.j.error) || 'No se pudo actualizar la tarea.', true); btn.disabled = false; }
        })
        .catch(function () { aviso('Sin conexión. Inténtalo de nuevo.', true); btn.disabled = false; });
    });
  });
})();
