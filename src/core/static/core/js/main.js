// ============================================================
// CUIDA APP — main.js
// Lógica centralizada para toda la aplicación
// ============================================================


// --- 1. LÓGICA DE PESTAÑAS (Dashboard) ---
window.mostrarPestana = function(nombre) {
    document.querySelectorAll('.pestana-content').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.shortcut-btn').forEach(b => b.classList.remove('active'));

    const seccion = document.getElementById('seccion-' + nombre);
    const boton   = document.getElementById('btn-tab-' + nombre);

    if (seccion) seccion.classList.add('active');
    if (boton)   boton.classList.add('active');

    sessionStorage.setItem('dashboard_tab', nombre);
};


// --- 2. LÓGICA DE MEDICAMENTOS (Creación/Edición) ---
window.agregarHorario = function() {
    const container = document.getElementById('horarios-container');
    if (!container) return;

    // Renumera los inputs existentes para que siempre sean 0, 1, 2...
    // así el backend recibe índices correlat ivos sin importar cuántos se eliminaron
    const existentes = container.querySelectorAll('.horario-input-wrapper input[type="time"]');
    existentes.forEach((input, i) => { input.name = `horario_${i}`; });

    const nuevoIndex = existentes.length;
    const wrapper = document.createElement('div');
    wrapper.className = 'horario-input-wrapper';
    wrapper.innerHTML = `
        <input type="time" name="horario_${nuevoIndex}" class="form-control" style="width:140px;">
        <button type="button" onclick="eliminarHorario(this)" class="btn-remove-horario" title="Eliminar">✕</button>
    `;
    container.appendChild(wrapper);
};

// Elimina el horario y renumera los restantes
window.eliminarHorario = function(btn) {
    btn.parentElement.remove();
    const container = document.getElementById('horarios-container');
    if (!container) return;
    container.querySelectorAll('.horario-input-wrapper input[type="time"]')
        .forEach((input, i) => { input.name = `horario_${i}`; });
};


// --- 3. LÓGICA DEL MODAL DE DOCUMENTOS ---

// Llamada desde las cards de fotos_mediciones (lee data-* del elemento)
window.lanzarModal = function(card) {
    const id             = card.dataset.id;
    const tipoDisplay    = card.dataset.display  || '';
    const tipo           = card.dataset.tipo      || '';
    const url            = card.dataset.url      || '';
    const fecha          = card.dataset.fecha    || '';
    const nota           = card.dataset.nota     || '';
    const pacienteNombre = card.dataset.paciente || '';
    const esTutor        = card.dataset.esTutor === 'true';
    const esPdf          = card.dataset.esPdf === 'true' || url.toLowerCase().endsWith('.pdf');

    const modal = document.getElementById('modal-doc');
    if (!modal) return;

    // Badge, fecha y nombre
    const badge = document.getElementById('modal-badge');
    if (badge) badge.textContent = tipoDisplay;
    const fechaEl = document.getElementById('modal-fecha');
    if (fechaEl) fechaEl.textContent = fecha;
    const pacEl = document.getElementById('modal-paciente-nombre');
    if (pacEl) pacEl.textContent = pacienteNombre ? '👤 ' + pacienteNombre : '';

    // Imagen o PDF
    const archEl = document.getElementById('modal-archivo');
    if (archEl) {
        if (esPdf) {
            // iframe para ver el PDF directamente en el modal
            archEl.innerHTML = `<iframe src="${url}" style="width:100%;height:500px;border:none;border-radius:10px;"></iframe>`;
        } else {
            archEl.innerHTML = `<img src="${url}" style="width:100%;border-radius:10px;margin-bottom:10px;">`;
        }
    }

    // Nota del paciente
    const notaWrapper = document.getElementById('modal-nota-wrapper');
    const notaEl      = document.getElementById('modal-nota');
    if (notaWrapper) notaWrapper.style.display = nota ? 'block' : 'none';
    if (notaEl) notaEl.textContent = nota;

    // Botones de acción: solo si es tutor
    const btnCargar   = document.getElementById('modal-btn-cargar');
    const formAceptar = document.getElementById('form-aceptar');
    const formRechazar = document.getElementById('form-rechazar');

    if (esTutor) {
        if (btnCargar) {
            btnCargar.href          = `/fotos-mediciones/${id}/cargar/`;
            btnCargar.style.display = tipo === 'medicion' ? 'inline-flex' : 'none';
        }
        if (formAceptar) {
            formAceptar.action        = `/fotos-mediciones/${id}/procesar/`;
            formAceptar.style.display = 'inline';
        }
        if (formRechazar) {
            formRechazar.action        = `/fotos-mediciones/${id}/rechazar/`;
            formRechazar.style.display = 'inline';
        }
    } else {
        // Paciente: oculta todos los botones de acción
        if (btnCargar)    btnCargar.style.display    = 'none';
        if (formAceptar)  formAceptar.style.display  = 'none';
        if (formRechazar) formRechazar.style.display = 'none';
    }

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
};

// Versión con parámetros explícitos (compatibilidad)
window.abrirModal = function(id, tipoDisplay, tipo, url, fecha, nota, pacienteNombre) {
    lanzarModal({ dataset: { id, display: tipoDisplay, tipo, url, fecha, nota, paciente: pacienteNombre, esTutor: 'false' } });
};

window.cerrarModal = function() {
    const modal = document.getElementById('modal-doc');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
};


// --- 4. INICIALIZACIÓN GLOBAL ---
document.addEventListener('DOMContentLoaded', function() {

    // Restaurar pestaña activa solo si venimos del mismo dashboard
    // (no al entrar desde otra sección)
    const tabGuardada = sessionStorage.getItem('dashboard_tab');
    const vieneDeInternamente = document.referrer.includes(window.location.pathname);
    if (tabGuardada && vieneDeInternamente && document.getElementById('seccion-' + tabGuardada)) {
        mostrarPestana(tabGuardada);
    }

    // Cerrar dropdown de pacientes al hacer click afuera
    document.addEventListener('click', function(e) {
        const selector = document.querySelector('.dashboard-selector');
        if (selector && !selector.contains(e.target)) {
            document.getElementById('dropdown-pacientes')?.classList.remove('show');
        }
    });

    // Lógica de Gráficos (Dashboard)
    const dataElement     = document.getElementById('mediciones-data');
    const controlesElement = document.getElementById('controles-data');

    if (dataElement && controlesElement && typeof Chart !== 'undefined') {
        let raw, controles;

        try {
            raw      = JSON.parse(dataElement.textContent);
            controles = JSON.parse(controlesElement.textContent);
        } catch(e) {
            console.error('Cuida APP: error al parsear datos de mediciones', e);
            raw = []; controles = [];
        }

        let graficoActual = null;

        window.mostrarGrafico = function(tipo) {
            document.querySelectorAll('.btn-graf-tipo').forEach(b => b.classList.remove('active-graf'));
            document.getElementById('btn-graf-' + tipo)?.classList.add('active-graf');

            const datos = raw.filter(d => d.tipo === tipo).reverse();
            const canvasWrapper = document.querySelector('.chart-wrapper');
            const sinDatosEl   = document.getElementById('grafico-sin-datos');

            if (datos.length === 0) {
                if (canvasWrapper) canvasWrapper.style.display = 'none';
                if (sinDatosEl)   sinDatosEl.style.display = 'block';
                return;
            }
            if (canvasWrapper) canvasWrapper.style.display = 'block';
            if (sinDatosEl)   sinDatosEl.style.display = 'none';

            if (graficoActual) graficoActual.destroy();

            const ctx    = document.getElementById('grafico-mediciones').getContext('2d');
            const labels = datos.map(d => new Date(d.fecha).toLocaleDateString('es-AR'));

            // Presión arterial tiene dos valores: sistólica y diastólica
            const datasets = tipo === 'presion'
                ? [
                    { label: 'Sistólica',  data: datos.map(d => d.valor_1), borderColor: '#004b80', backgroundColor: 'rgba(0,75,128,0.08)', tension: 0.3, fill: false },
                    { label: 'Diastólica', data: datos.map(d => d.valor_2), borderColor: '#e53e3e', backgroundColor: 'rgba(229,62,62,0.08)',  tension: 0.3, fill: false }
                  ]
                : [
                    { label: tipo, data: datos.map(d => d.valor_1), borderColor: '#004b80', backgroundColor: 'rgba(0,75,128,0.08)', tension: 0.3, fill: true }
                  ];

            graficoActual = new Chart(ctx, {
                type: 'line',
                data: { labels, datasets },
                options: {
                    responsive: true,
                    plugins: { legend: { display: tipo === 'presion' } }
                }
            });
        };

        // Mostrar el primer control disponible al cargar
        if (controles.length > 0) mostrarGrafico(controles[0]);

    } else {
        // Si no hay datos, definir mostrarGrafico como no-op para evitar errores en los botones
        window.mostrarGrafico = function() {};
    }

    // Inicializar listeners de frecuencia (Medicamentos)
    const radiosFrecuencia = document.querySelectorAll('input[name="frecuencia_tipo"]');
    radiosFrecuencia.forEach(r => r.addEventListener('change', () => {
        const val = document.querySelector('input[name="frecuencia_tipo"]:checked')?.value;
        document.getElementById('campos-fijo')?.style     && (document.getElementById('campos-fijo').style.display     = val === 'fijo'      ? 'block' : 'none');
        document.getElementById('campos-intervalo')?.style && (document.getElementById('campos-intervalo').style.display = val === 'intervalo' ? 'block' : 'none');
        document.getElementById('campos-evento')?.style   && (document.getElementById('campos-evento').style.display   = val === 'evento'    ? 'block' : 'none');
    }));

});