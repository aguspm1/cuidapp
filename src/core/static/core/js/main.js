// ============================================================
// CUIDA APP — main.js
// ============================================================

function mostrarPestana(nombre) {
    document.querySelectorAll('.pestana-content').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.shortcut-btn').forEach(b => b.classList.remove('active'));

    const seccion = document.getElementById('seccion-' + nombre);
    const boton   = document.getElementById('btn-tab-' + nombre);

    if (seccion) seccion.classList.add('active');
    if (boton)   boton.classList.add('active');

    sessionStorage.setItem('dashboard_tab', nombre);
}

document.addEventListener('DOMContentLoaded', function() {
    const tabGuardada = sessionStorage.getItem('dashboard_tab');
    if (tabGuardada && document.getElementById('seccion-' + tabGuardada)) {
        mostrarPestana(tabGuardada);
    }
});