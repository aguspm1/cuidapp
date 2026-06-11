// ============================================================
// CUIDA APP — main.js (Versión Final Unificada)
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
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
        const existentes = container.querySelectorAll('input[type="time"]');
        existentes.forEach((input, i) => { input.name = `horario_${i}`; });
        const nuevoIndex = existentes.length;
        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'display:flex; align-items:center; gap:6px; margin-top:5px;';
        wrapper.innerHTML = `
            <input type="time" name="horario_${nuevoIndex}" class="form-control" style="width:140px;">
            <button type="button" onclick="eliminarHorario(this)" style="background:none;border:none;color:#e74c3c;font-size:1.2rem;cursor:pointer;" title="Eliminar">✕</button>
        `;
        container.appendChild(wrapper);
    };

    window.eliminarHorario = function(btn) {
        btn.parentElement.remove();
        const container = document.getElementById('horarios-container');
        if (!container) return;
        container.querySelectorAll('input[type="time"]').forEach((input, i) => { input.name = `horario_${i}`; });
    };

    // --- 3. LÓGICA DEL MODAL DE DOCUMENTOS ---
    window.lanzarModal = function(card) {
        const id             = card.dataset.id;
        const tipoDisplay    = card.dataset.display    || '';
        const tipo           = card.dataset.tipo       || '';
        const url            = card.dataset.url        || '';
        const fecha          = card.dataset.fecha      || '';
        const nota           = card.dataset.nota       || '';
        const pacienteNombre = card.dataset.paciente   || '';
        const esTutor        = card.dataset.esTutor    === 'true';

        const modal = document.getElementById('modal-doc');
        if (!modal) return;

        document.getElementById('modal-badge').textContent = tipoDisplay;
        document.getElementById('modal-fecha').textContent = fecha;
        document.getElementById('modal-paciente-nombre').textContent = pacienteNombre ? '👤 ' + pacienteNombre : '';
        document.getElementById('modal-nota').textContent = nota || "Sin observaciones.";

        const archEl = document.getElementById('modal-archivo');
        archEl.innerHTML = url.toLowerCase().endsWith('.pdf') ? 
            `<div style="padding:40px; background:#f0f4f8; border-radius:10px;">📄 PDF detectado. <a href="${url}" target="_blank">Abrir documento ↗</a></div>` :
            `<img src="${url}" style="width:100%; border-radius:10px;">`;

        const btnCargar = document.getElementById('modal-btn-cargar');
        const formAceptar = document.getElementById('form-aceptar');
        const formRechazar = document.getElementById('form-rechazar');

        if (esTutor) {
            btnCargar.href = `/fotos-mediciones/${id}/cargar/`;
            btnCargar.style.display = (tipo === 'medicion') ? 'inline-flex' : 'none';
            formAceptar.action = `/fotos-mediciones/${id}/procesar/`;
            formRechazar.action = `/fotos-mediciones/${id}/rechazar/`;
            formAceptar.style.display = 'inline';
            formRechazar.style.display = 'inline';
        } else {
            btnCargar.style.display = 'none';
            formAceptar.style.display = 'none';
            formRechazar.style.display = 'none';
        }
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    };

    window.cerrarModal = function() {
        document.getElementById('modal-doc').style.display = 'none';
        document.body.style.overflow = '';
    };

    // --- 4. CONFIGURACIÓN DINÁMICA (Radio Buttons de frecuencia) ---
    // Guard: solo ejecutar si estamos en la página de medicamentos
    const camposFijo = document.getElementById('campos-fijo');
    if (camposFijo) {
        const radiosFrecuencia = document.querySelectorAll('input[name="frecuencia_tipo"]');
        function actualizarFrecuencia() {
            const val = document.querySelector('input[name="frecuencia_tipo"]:checked')?.value;
            document.getElementById('campos-fijo').style.display      = val === 'fijo'      ? 'block' : 'none';
            document.getElementById('campos-intervalo').style.display = val === 'intervalo' ? 'block' : 'none';
            document.getElementById('campos-evento').style.display    = val === 'evento'    ? 'block' : 'none';
        }
        radiosFrecuencia.forEach(r => r.addEventListener('change', actualizarFrecuencia));
        actualizarFrecuencia();
    }

    // --- 5. RESTAURAR PESTAÑA ACTIVA (Dashboard) ---
    const tabGuardada = sessionStorage.getItem('dashboard_tab');
    if (tabGuardada && document.getElementById('seccion-' + tabGuardada)) {
        mostrarPestana(tabGuardada);
    }

    // --- 6. AJUSTAR COLUMNAS DEL GRID SEGÚN PESTAÑAS VISIBLES ---
    const grid = document.getElementById('grid-pestanas');
    if (grid) {
        const cantidad = grid.querySelectorAll('.shortcut-btn').length;
        grid.style.gridTemplateColumns = 'repeat(' + cantidad + ', 1fr)';
    }
});