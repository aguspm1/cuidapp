// ============================================================
// CUIDA APP — main.js (Versión Final Unificada)
// ============================================================

window.mostrarPestana = function(nombre) {
    document.querySelectorAll('.pestana-content').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.shortcut-btn').forEach(b => b.classList.remove('active'));
    const seccion = document.getElementById('seccion-' + nombre);
    const boton   = document.getElementById('btn-tab-' + nombre);
    if (seccion) seccion.classList.add('active');
    if (boton)   boton.classList.add('active');
    sessionStorage.setItem('dashboard_tab', nombre);
};

// Funciones globales (Acordeón)
window.toggleAcordeon = function(boton) {
    const itemActual = boton.parentElement;
    const contenidoActual = itemActual.querySelector('.acordeon-content');
    const flechaActual = itemActual.querySelector('.acordeon-flecha');
    const estaActivo = itemActual.classList.contains('active');

    document.querySelectorAll('.acordeon-item').forEach(item => {
        item.classList.remove('active');
        item.querySelector('.acordeon-content').style.display = 'none';
        item.querySelector('.acordeon-flecha').style.transform = 'rotate(-90deg)';
    });

    if (!estaActivo) {
        itemActual.classList.add('active');
        contenidoActual.style.display = 'block';
        flechaActual.style.transform = 'rotate(0deg)';
    }
};

document.addEventListener('DOMContentLoaded', function() {
    
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

    const inputHoras = document.querySelector('input[name="cada_cuantas_horas"]');
    if (inputHoras) {
        inputHoras.addEventListener('input', function() {
            if (this.value > 24) {
                this.value = 24; 
                alert("⚠️ El intervalo máximo permitido es de 24 horas.");
            }
            if (this.value < 1) {
                this.value = 1; 
            }
        });
    }

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
        const esProcesada    = card.dataset.procesada  === 'true';

        const modal = document.getElementById('modal-doc');
        if (!modal) return;

        document.getElementById('modal-badge').textContent = tipoDisplay;
        document.getElementById('modal-fecha').textContent = fecha;
        document.getElementById('modal-paciente-nombre').textContent = pacienteNombre ? '👤 ' + pacienteNombre : '';
        document.getElementById('modal-nota').textContent = nota || "Sin observaciones.";

        const archEl = document.getElementById('modal-archivo');
        archEl.innerHTML = url.toLowerCase().endsWith('.pdf') ? 
            `<div style="padding:40px; background:#f0f4f8; border-radius:10px;">📄 PDF detectado. <a href="${url}" target="_blank">Abrir documento ↗</a></div>` :
            `<img src="${url}" style="width:100%; max-height: 60vh; object-fit:contain; border-radius:10px;">`;

        const btnCargar = document.getElementById('modal-btn-cargar');
        const formAceptar = document.getElementById('form-aceptar');
        const formRechazar = document.getElementById('form-rechazar');
        
        if (formRechazar) formRechazar.action = `/fotos-mediciones/${id}/eliminar/`;

        // Lógica de visualización según rol
        if (esTutor) {
            if (!esProcesada) {
                if(btnCargar) {
                    btnCargar.href = `/fotos-mediciones/${id}/cargar/`;
                    btnCargar.style.display = (tipo === 'medicion') ? 'inline-flex' : 'none';
                }
                if(formAceptar) {
                    formAceptar.action = `/fotos-mediciones/${id}/procesar/`;
                    formAceptar.style.display = 'inline';
                }
                if(formRechazar) {
                    formRechazar.action = `/fotos-mediciones/${id}/rechazar/`;
                    formRechazar.style.display = 'inline';
                }
            } else {
                if(btnCargar) btnCargar.style.display = 'none';
                if(formAceptar) formAceptar.style.display = 'none';
                if(formRechazar) formRechazar.style.display = 'none';
            }
        } else {
            if(btnCargar) btnCargar.style.display = 'none';
            if(formAceptar) formAceptar.style.display = 'none';
            if(formRechazar) formRechazar.style.display = 'none';
        }
        
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    };

    window.cerrarModal = function() {
        const modal = document.getElementById('modal-doc');
        if (modal) modal.style.display = 'none';
        document.body.style.overflow = '';
    };

    // --- 4. DINÁMICA DE FORMULARIOS DE MEDICAMENTOS ---
    
    // A. Mostrar/Ocultar Frecuencia (Fijo, Intervalo, Evento)
    const radiosFrecuencia = document.querySelectorAll('input[name="frecuencia_tipo"]');
    if (radiosFrecuencia.length > 0) {
        function actualizarFrecuencia() {
            const val = document.querySelector('input[name="frecuencia_tipo"]:checked')?.value;
            const cFijo = document.getElementById('campos-fijo');
            const cInt = document.getElementById('campos-intervalo');
            const cEv = document.getElementById('campos-evento');
            if (cFijo) cFijo.style.display = (val === 'fijo') ? 'block' : 'none';
            if (cInt) cInt.style.display = (val === 'intervalo') ? 'block' : 'none';
            if (cEv) cEv.style.display = (val === 'evento') ? 'block' : 'none';
        }
        radiosFrecuencia.forEach(r => r.addEventListener('change', actualizarFrecuencia));
        actualizarFrecuencia(); 
    }

    // B. Mostrar/Ocultar Fecha de Fin (Tratamiento Temporal)
    const radiosDuracion = document.querySelectorAll('input[name="duracion_tipo"]');
    if (radiosDuracion.length > 0) {
        function actualizarDuracion() {
            const val = document.querySelector('input[name="duracion_tipo"]:checked')?.value;
            const cFin = document.getElementById('campos-fecha-fin');
            if (cFin) cFin.style.display = (val === 'temporal') ? 'block' : 'none';
        }
        
        const inputFechaFin = document.getElementById('id_fecha_fin') || document.querySelector('#campos-fecha-fin input[type="date"]');
        if (inputFechaFin) {
            const hoy = new Date();
            const yyyy = hoy.getFullYear();
            const mm = String(hoy.getMonth() + 1).padStart(2, '0');
            const dd = String(hoy.getDate()).padStart(2, '0');
            inputFechaFin.min = `${yyyy}-${mm}-${dd}`;
        }

        radiosDuracion.forEach(r => r.addEventListener('change', actualizarDuracion));
        actualizarDuracion();
    }

    // C. Automatizar y Filtrar Relación Presentación -> Unidad de Medida
    const selectPres = document.getElementById('id_tipo_presentacion');
    const selectUnid = document.getElementById('id_unidad_medida');
    if (selectPres && selectUnid) {
        function filtrarUnidades() {
            const presente = selectPres.value;
            
            Array.from(selectUnid.options).forEach(opt => {
                opt.style.display = 'block';
                opt.disabled = false;
            });

            if (presente === 'comprimido') {
                selectUnid.value = 'unidades';
                Array.from(selectUnid.options).forEach(opt => {
                    if (opt.value !== 'unidades') {
                        opt.style.display = 'none';
                        opt.disabled = true;
                    }
                });
            } else if (presente === 'liquido' || presente === 'inyectable') {
                selectUnid.value = 'ml';
                Array.from(selectUnid.options).forEach(opt => {
                    if (opt.value !== 'ml' && opt.value !== 'mg') {
                        opt.style.display = 'none';
                        opt.disabled = true;
                    }
                });
            } else if (presente === 'gota') {
                selectUnid.value = 'gotas';
                Array.from(selectUnid.options).forEach(opt => {
                    if (opt.value !== 'gotas' && opt.value !== 'ml') {
                        opt.style.display = 'none';
                        opt.disabled = true;
                    }
                });
            }
        }

        selectPres.addEventListener('change', filtrarUnidades);
        filtrarUnidades();
    }

    // --- VALIDACIONES FINALES ---
    const stockTotalInput  = document.querySelector('input[name=stock_total]');
    const stockActualInput = document.querySelector('input[name=stock_actual]');
    const dosisInput       = document.querySelector('input[name=dosis_por_toma]');
    const cadaHorasInput   = document.querySelector('input[name=cada_cuantas_horas]');

    if (stockTotalInput && stockActualInput) {
        stockTotalInput.addEventListener('input', function() {
            if (!stockActualInput.value || stockActualInput.value === '0') {
                stockActualInput.value = stockTotalInput.value;
            }
        });
    }

    const formMed = document.querySelector('form[action*=medicamento]');
    if (formMed && dosisInput) {
        formMed.addEventListener('submit', function(e) {
            const dosis       = parseFloat(dosisInput?.value) || 0;
            const stockActual = parseFloat(stockActualInput?.value) || 0;
            const stockTotal  = parseFloat(stockTotalInput?.value) || 0;

            if (dosis <= 0) {
                e.preventDefault(); alert('❌ La dosis debe ser mayor a cero.'); return;
            }
            if (dosis > stockActual) {
                e.preventDefault(); alert(`❌ La dosis (${dosis}) no puede superar el stock actual (${stockActual}).`); return;
            }
            if (dosis > stockTotal) {
                e.preventDefault(); alert(`❌ La dosis (${dosis}) no puede superar la capacidad del envase (${stockTotal}).`); return;
            }
            if (cadaHorasInput && cadaHorasInput.value) {
                const horas = parseFloat(cadaHorasInput.value) || 0;
                if (horas < 1 || horas > 24) {
                    e.preventDefault(); alert('❌ El intervalo debe estar entre 1 y 24 horas.'); cadaHorasInput.focus(); return;
                }
            }
        });
    }

    // --- RESTO (Campanita, Pestañas, Gráficos) ---
    const tabGuardada = sessionStorage.getItem('dashboard_tab');
    if (tabGuardada && document.getElementById('seccion-' + tabGuardada)) {
        mostrarPestana(tabGuardada);
    }

    const btnCampanita = document.getElementById('btn-campanita');
    const dropdownNotif = document.getElementById('dropdown-notif');
    const badgeNotif = document.getElementById('badge-notif');

    if (btnCampanita && dropdownNotif) {
        btnCampanita.addEventListener('click', function(e) {
            e.stopPropagation();
            const estaOculto = dropdownNotif.style.display === 'none';
            dropdownNotif.style.display = estaOculto ? 'block' : 'none';

            if (estaOculto && badgeNotif) {
                fetch('/notificaciones/marcar-leidas/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json'
                    }
                }).then(response => {
                    if(response.ok) {
                        badgeNotif.style.display = 'none';
                    }
                }).catch(error => console.error("Error al marcar notificaciones:", error));
            }
        });

        document.addEventListener('click', function(e) {
            if (!btnCampanita.contains(e.target) && !dropdownNotif.contains(e.target)) {
                dropdownNotif.style.display = 'none';
            }
        });
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // --- Gráficos ---
    let miGrafico = null;
    window.mostrarGrafico = function(tipo) {
        const dataEl = document.getElementById('mediciones-data');
        if (!dataEl) return;
        
        const datos = JSON.parse(dataEl.textContent);
        const ctx = document.getElementById('grafico-mediciones');
        if (!ctx) return;

        document.querySelectorAll('[id^="btn-graf-"]').forEach(btn => {
            btn.classList.remove('active');
        });
        const btnActivo = document.getElementById(`btn-graf-${tipo}`);
        if (btnActivo) btnActivo.classList.add('active');

        const datosTipo = datos[tipo];
        const sinDatosEl = document.getElementById('grafico-sin-datos');
        const canvasEl = document.getElementById('grafico-mediciones');

        if (!datosTipo || !datosTipo.labels || datosTipo.labels.length === 0) {
            if (sinDatosEl) sinDatosEl.style.display = 'block';
            if (canvasEl) canvasEl.style.display = 'none';
            if (miGrafico) miGrafico.destroy();
            return;
        }

        if (sinDatosEl) sinDatosEl.style.display = 'none';
        if (canvasEl) canvasEl.style.display = 'block';

        if (miGrafico) miGrafico.destroy();

        let datasets = [];
        if (tipo === 'presion') {
            datasets = [
                { label: 'Sistólica', data: datosTipo.valores_sistolica || datosTipo.valores_1 || [], borderColor: '#e74c3c', backgroundColor: 'rgba(231, 76, 60, 0.1)', tension: 0.2, fill: true },
                { label: 'Diastólica', data: datosTipo.valores_diastolica || datosTipo.valores_2 || [], borderColor: '#34495e', backgroundColor: 'rgba(52, 73, 94, 0.1)', tension: 0.2, fill: true }
            ];
        } else if (tipo === 'glucosa') {
            datasets = [{ label: 'Glucosa (mg/dL)', data: datosTipo.valores || datosTipo.valores_1 || [], borderColor: '#2ecc71', backgroundColor: 'rgba(46, 204, 113, 0.1)', tension: 0.2, fill: true }];
        } else if (tipo === 'peso') {
            datasets = [{ label: 'Peso (kg)', data: datosTipo.valores || datosTipo.valores_1 || [], borderColor: '#3498db', backgroundColor: 'rgba(52, 152, 219, 0.1)', tension: 0.2, fill: true }];
        }

        miGrafico = new Chart(ctx, {
            type: 'line',
            data: { labels: datosTipo.labels, datasets: datasets },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: false } } }
        });
    };
});